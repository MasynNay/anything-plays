"""Inspect signed macOS RC1 Mach-O runpaths for the conflicting SDL2 basename.

This reads original signed libraries and the independently pinned linkage
receipt. It resolves *direct image LC_RPATH candidates*, not dyld's full
loader chain: dependency inheritance, process environment, and the actual
loaded image must be verified separately. Never mark source or release
approval based on this diagnostic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from tools.probe_v31_macos_sdl_load import select_libs

SOURCE_SHA = "26de1e1ad1b701d0735e085158347f8c213ce437"
TARGET_COUNTS = {"macos-arm64": 121, "macos-x64": 120}
SDL_REFERENCE = "@rpath/libSDL2-2.0.0.dylib"
REPORT_STATUS = "UNRELEASED_3_1_MACOS_NATIVE_LINKAGE_REVIEW"
HASH_RE = re.compile(r"^[a-f0-9]{64}$")
RPATH_RE = re.compile(r"^\s*path\s+(.+?)\s+\(offset\s+\d+\)\s*$")
MAX_OTOOL_OUTPUT = 2 * 1024 * 1024


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def parse_local_rpaths(output):
    """Read LC_RPATH only, rejecting malformed or incomplete commands."""
    if not isinstance(output, str) or len(output) > MAX_OTOOL_OUTPUT:
        raise ValueError("Invalid or unbounded Mach-O load commands")
    lines = output.splitlines()
    result = []
    for index, line in enumerate(lines):
        if line.strip() != "cmd LC_RPATH":
            continue
        # A normal load command has a cmdsize and then a path field.
        following = lines[index + 1:index + 5]
        fields = [RPATH_RE.match(value) for value in following]
        paths = [match.group(1) for match in fields if match]
        if len(paths) != 1 or not paths[0] or "\x00" in paths[0]:
            raise ValueError("Malformed LC_RPATH load command")
        if paths[0] not in result:
            result.append(paths[0])
    return result


def checked_bundle_file(app, relative, digest):
    """Require an exact audited file, rejecting path escape and replacement."""
    if (not isinstance(relative, str) or not relative
            or relative.startswith("/") or "\\" in relative
            or any(part in ("", ".", "..") for part in relative.split("/"))
            or not isinstance(digest, str) or not HASH_RE.fullmatch(digest)):
        raise ValueError("Unsafe or unpinned installed library record")
    location = app / relative
    if location.is_symlink():
        # PyInstaller ships legitimate relative dylib / extension symlinks.
        # Preserve them only if the final target remains inside the
        # read-only signed app and its bytes match the original QA hash.
        # Absolute or escaping symlinks are not trusted even when readable.
        if location.readlink().is_absolute():
            raise ValueError("Absolute original native link requires review")
    try:
        resolved = location.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("Missing original audited library") from exc
    if (not resolved.is_file() or
            not resolved.is_relative_to(app.resolve()) or
            sha256(resolved) != digest):
        raise ValueError("Original signed library differs from trusted receipt")
    return resolved


def expand_direct_rpath(raw, loader, app):
    """Expand only the tested image's own local runpath; never guess parents."""
    if raw == "@loader_path" or raw.startswith("@loader_path/"):
        return (loader.parent / raw[len("@loader_path"):].lstrip("/")), None
    if raw == "@executable_path" or raw.startswith("@executable_path/"):
        return (app / "Contents" / "MacOS" /
                raw[len("@executable_path"):].lstrip("/")), None
    if raw.startswith("/"):
        return None, "absolute_runpath_not_assumed_bundled"
    return None, "unexpanded_or_inherited_runpath"


def classify_candidate(candidate, app, signed):
    """Name matching is insufficient; authenticate actual on-disk bytes."""
    root = app.resolve()
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        return {"status": "not_present_at_direct_runpath"}
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError("LC_RPATH unexpectedly resolves outside signed app")
    actual = sha256(resolved)
    matched = sorted(
        slot for slot, details in signed.items()
        if details["audited_sha256"] == actual
    )
    return {
        "status": ("signed_sdl_binary_hash_match" if matched
                   else "other_bundled_binary_requires_review"),
        "bundle_path": resolved.relative_to(root).as_posix(),
        "sha256": actual,
        "matching_pinned_sdl_slots": matched,
        "actual_loader_choice_verified": False,
    }


def inspect(app, linkage, target, runner=subprocess.run):
    """Bound and authenticate original evidence before inspecting runpaths."""
    if target not in TARGET_COUNTS or not isinstance(linkage, dict):
        raise ValueError("Unsupported macOS linker review target")
    app = Path(app)
    if not app.is_dir() or app.is_symlink():
        raise ValueError("Expected genuine mounted original Mac RC application")
    if (linkage.get("schema_version") != 1
            or linkage.get("target") != target
            or linkage.get("status") != REPORT_STATUS
            or linkage.get("source_app_commit") != SOURCE_SHA
            or linkage.get("native_file_count") != TARGET_COUNTS[target]
            or linkage.get("redistribution_approved") is not False
            or linkage.get("lgpl_relinking_reviewed") is not False):
        raise ValueError("Unexpected or approved signed native linkage receipt")
    files = linkage.get("native_files")
    if not isinstance(files, list) or len(files) != TARGET_COUNTS[target]:
        raise ValueError("Incomplete original Mac native file inventory")
    signed = select_libs(app, linkage, target)
    observed_paths = set()
    findings = []
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Malformed original native library record")
        relative = item.get("path")
        if relative in observed_paths:
            raise ValueError("Duplicate native record")
        observed_paths.add(relative)
        deps = item.get("otool_dependencies")
        if not isinstance(deps, list) or not deps:
            raise ValueError("Missing original native dependency evidence")
        if not any(isinstance(dep, dict) and
                   dep.get("name") == SDL_REFERENCE for dep in deps):
            continue
        library = checked_bundle_file(app, relative, item.get("sha256"))
        try:
            process = runner(["otool", "-l", str(library)],
                             text=True, capture_output=True, check=False,
                             timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("Cannot inspect original native load commands") from exc
        if process.returncode != 0:
            raise ValueError("Original signed Mach-O load command inspection failed")
        rpaths = parse_local_rpaths(process.stdout)
        options = []
        for value in rpaths:
            directory, reason = expand_direct_rpath(value, library, app)
            if directory is None:
                options.append({"runpath": value, "status": reason})
            else:
                path = directory / SDL_REFERENCE.split("/", 1)[1]
                detail = classify_candidate(path, app, signed)
                options.append({"runpath": value, **detail})
        findings.append({
            "signed_library": relative,
            "signed_sha256": item["sha256"],
            "linked_install_name": SDL_REFERENCE,
            "image_local_rpaths": rpaths,
            "direct_candidates": options,
            "dyld_actual_selection_verified": False,
        })
    if not findings:
        raise ValueError("No original SDL2 @rpath references found to inspect")
    return {
        "schema_version": 1,
        "status": "REVIEW_ONLY_3_1_MACOS_SIGNED_SDL2_DIRECT_RPATHS",
        "target": target,
        "source_app_commit": SOURCE_SHA,
        "original_signed_native_count": len(files),
        "sdl2_referencing_images": len(findings),
        "signed_sdl2_variants": signed,
        "linking": findings,
        "scope": "Only direct LC_RPATH entries in audited SDL/pygame Mach-O images",
        "full_dyld_loader_chain_resolved": False,
        "live_loaded_sdl_image_proven": False,
        "physical_controller_camera_tested": False,
        "complete_corresponding_source_verified": False,
        "lgpl_redistribution_approved": False,
        "stable_3_1_release_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--linkage", type=Path, required=True)
    parser.add_argument("--target", choices=sorted(TARGET_COUNTS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    bundle = options.bundle.resolve(strict=True)
    output = options.output.resolve()
    if output.is_relative_to(bundle) or options.output.is_symlink():
        parser.error("Read-only review output must not overwrite signed app")
    report = inspect(bundle, json.loads(options.linkage.read_text("utf-8")),
                     options.target)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = {}
    for item in report["linking"]:
        for candidate in item["direct_candidates"]:
            status = candidate["status"]
            summary[status] = summary.get(status, 0) + 1
    print(options.target, "signed SDL2 reference images:",
          report["sdl2_referencing_images"], "direct rpath findings:",
          json.dumps(summary, sort_keys=True))
    print("Dynamic-loader selection, complete source, LGPL and stable release NOT verified")


if __name__ == "__main__":
    main()
