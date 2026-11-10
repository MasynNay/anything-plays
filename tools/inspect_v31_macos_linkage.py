"""Read-only macOS SDL/pygame native dependency evidence from final RC1 DMG.

Must run on a macOS host with otool, lipo and codesign. This records linked
library paths, Mach-O architecture and signature state for *actual* frozen
RC1 files. It neither modifies the application nor proves LGPL compliance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

RC_SHA = "fe0da0b8b5f478cf1172734ef38546c4f1e86229"
ARCHES = {"macos-arm64": "arm64", "macos-x64": "x86_64"}
MAX_OUTPUT_CHARS = 12_000
OTOOLED = re.compile(r"^\s*(.*?)\s*\(compatibility version ([^,]+), current version ([^)]+)\)\s*$")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dependencies_from_otool(output):
    """Structured dylib names; preserve the raw command output for review."""
    result = []
    for line in output.splitlines()[1:]:
        match = OTOOLED.match(line)
        if match:
            result.append({
                "name": match[1],
                "compatibility_version": match[2],
                "current_version": match[3],
            })
    return result


def _run(command, runner=subprocess.run):
    completed = runner(command, text=True, capture_output=True, check=False)
    return {
        "return_code": completed.returncode,
        "stdout": completed.stdout[:MAX_OUTPUT_CHARS],
        "stderr": completed.stderr[:MAX_OUTPUT_CHARS],
    }


def inspect(bundle, audit, receipt, installer, target, runner=subprocess.run):
    bundle, installer = Path(bundle), Path(installer)
    if target not in ARCHES or not bundle.is_dir() or bundle.is_symlink():
        raise ValueError("Expected genuine mounted 3.1 macOS RC bundle")
    if not installer.is_file() or installer.is_symlink():
        raise ValueError("Expected complete original QA DMG")
    if (receipt.get("target") != target
            or receipt.get("source_preview_revision") != RC_SHA
            or receipt.get("public_release_approved") is not False
            or receipt.get("final_release_approved") is not False
            or receipt.get("native_core_count") != 11
            or receipt.get("console_profiles") != 18
            or receipt.get("installer") != installer.name
            or receipt.get("sha256") != sha256(installer)):
        raise ValueError("Tampered or mismatched full 3.1 RC1 DMG receipt")
    if (audit.get("target") != target
            or audit.get("status") != "UNRELEASED_3_1_SDL_RUNTIME_INVENTORY"
            or audit.get("redistribution_approved") is not False
            or audit.get("pygame_version") != "2.5.8"):
        raise ValueError("Unexpected or approved frozen SDL audit")
    natives = audit.get("native_candidates")
    if not isinstance(natives, list) or not natives:
        raise ValueError("Missing packaged pygame/SDL native file evidence")
    root = bundle.resolve()
    files = []
    for native in natives:
        relative = native.get("path") if isinstance(native, dict) else None
        if (not isinstance(relative, str) or not relative
                or relative.startswith("/") or "\\" in relative
                or ".." in relative.split("/")):
            raise ValueError("Unsafe native path")
        candidate = bundle / relative
        try:
            file = candidate.resolve(strict=True)
        except OSError as exc:
            raise ValueError("Missing actual native dylib: " + relative) from exc
        if not file.is_file() or not file.is_relative_to(root):
            raise ValueError("Native dylib outside mounted RC bundle")
        if sha256(file) != native.get("sha256"):
            raise ValueError("Final signed macOS dylib differs from QA hash: " + relative)
        otool = _run(["otool", "-L", str(file)], runner)
        lipo = _run(["lipo", "-archs", str(file)], runner)
        codesign = _run(["codesign", "-dv", "--verbose=4", str(file)], runner)
        files.append({
            "path": relative, "sha256": native["sha256"],
            "size_bytes": file.stat().st_size,
            "otool_dependencies": dependencies_from_otool(otool["stdout"])
                if otool["return_code"] == 0 else [],
            "otool_result": otool,
            "lipo_result": lipo,
            "codesign_metadata": codesign,
            "signed_metadata_available": codesign["return_code"] == 0,
            "binary_correspondence_approved": False,
        })
    return {
        "schema_version": 1,
        "status": "UNRELEASED_3_1_MACOS_NATIVE_LINKAGE_REVIEW",
        "target": target, "source_app_commit": RC_SHA,
        "qa_installer": installer.name,
        "qa_installer_sha256": sha256(installer),
        "expected_architecture": ARCHES[target],
        "native_file_count": len(files),
        "native_files": files,
        "codesign_impact_on_wheel_bytes_resolved": False,
        "upstream_sdl_sources_correspondence_verified": False,
        "lgpl_relinking_reviewed": False,
        "redistribution_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--installer", type=Path, required=True)
    p.add_argument("--target", choices=sorted(ARCHES), required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    audit = json.loads(args.audit.read_text("utf-8"))
    receipt = json.loads(args.receipt.read_text("utf-8"))
    result = inspect(args.bundle, audit, receipt, args.installer, args.target)
    out = args.output.resolve()
    if out.is_relative_to(args.bundle.resolve()):
        p.error("Inspection output must not modify frozen application")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    print(f"Audited {result['native_file_count']} final macOS pygame/SDL native "
          "candidates; code-signing and upstream linkage compliance UNAPPROVED")


if __name__ == "__main__":
    main()
