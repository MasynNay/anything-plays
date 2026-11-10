"""Prepare strictly labelled pygame-ce / SDL source review evidence for 3.1.

This produces an upstream pygame-ce source copy and hashes the exact published
platform wheels against the four *previously audited* installed RC1 bundles.
It does NOT prove those wheels were used at build time, nor that vendored SDL
matches any particular source tree, or that LGPL replacement is adequate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
import zipfile

TARGETS = ("linux-x64", "windows-x64", "macos-arm64", "macos-x64")
RC_APP_COMMIT = "86baa6972ed923540f6ab49b636652a0f499d45c"
RC_RUN = 42865608433
PYGAME_COMMIT = "c8200a9eaa530f884a0a4c3384cefc48006e58be"
PYGAME_VERSION = "2.5.8"
UPSTREAM_LGPL_HASH = "a190dc9c8043755d90f8b0a75fa66b9e42d4af4c980bf5ddc633f0124db3cee7"
SOURCE_ARCHIVE = "pygame-ce-2.5.8-tagged-upstream-source.tar.gz"
NATIVE_SHA = re.compile(r"^[0-9a-f]{64}$")
# Digests are taken from the upstream 2.5.8 GitHub release asset metadata,
# not from filenames guessed from the operating system.
WHEELS = {
    "linux-x64": (
        "pygame_ce-2.5.8-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.whl",
        "5bb966b610e161a8f6d908b4c62ef3a1f3e922bc7bed73bd70a3e15dc780b90e",
    ),
    "windows-x64": (
        "pygame_ce-2.5.8-cp313-cp313-win_amd64.whl",
        "f495b0eb7a5c54c59da58e964bc7f68073c3f43cf307729fd48309104a04c190",
    ),
    "macos-arm64": (
        "pygame_ce-2.5.8-cp313-cp313-macosx_10_13_universal2.whl",
        "56441a9bb75c2461750dc0e6e4a46e3833b3cf6339bfbaf16f93ecac037510f3",
    ),
    "macos-x64": (
        "pygame_ce-2.5.8-cp313-cp313-macosx_10_13_universal2.whl",
        "56441a9bb75c2461750dc0e6e4a46e3833b3cf6339bfbaf16f93ecac037510f3",
    ),
}
EXPECTED_RECEIPT_STATUS = {
    "linux-x64": "UNRELEASED_3_1_FULL_LINUX_RC1_QA",
    "windows-x64": "UNRELEASED_3_1_FULL_WINDOWS_RC1_QA",
    "macos-arm64": "UNRELEASED_3_1_FULL_MACOS_RC1_QA",
    "macos-x64": "UNRELEASED_3_1_FULL_MACOS_RC1_QA",
}
MAX_SOURCE_BYTES = 100 * 1024 * 1024
MAX_WHEEL_BYTES = 40 * 1024 * 1024


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("Missing or unsafe native review JSON: " + str(path))
    value = json.loads(path.read_text("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected JSON object: " + str(path))
    return value


def validate_source_archive(archive):
    """Examine tagged source as archive data; never extract untrusted members."""
    archive = Path(archive)
    if (not archive.is_file() or archive.is_symlink()
            or not 1_000_000 <= archive.stat().st_size <= MAX_SOURCE_BYTES):
        raise ValueError("Missing, linked or implausible upstream source archive")
    with tarfile.open(archive, "r:gz") as tar:
        entries = tar.getmembers()
        if not entries or len(entries) > 50_000:
            raise ValueError("Missing or excessive upstream source entries")
        for member in entries:
            parts = member.name.split("/")
            if (member.name.startswith("/") or ".." in parts
                    or not member.name.startswith("pygame-ce-2.5.8/")
                    or member.isdev()):
                raise ValueError("Unsafe upstream source member")
        names = {m.name for m in entries}
        license_name = "pygame-ce-2.5.8/docs/LGPL.txt"
        if license_name not in names:
            raise ValueError("Upstream pygame-ce license missing from archive")
        item = tar.extractfile(license_name)
        if item is None or hashlib.sha256(item.read()).hexdigest() != UPSTREAM_LGPL_HASH:
            raise ValueError("Upstream pygame-ce LGPL bytes do not match tag")
        if not any(p.startswith("pygame-ce-2.5.8/src_c/") for p in names):
            raise ValueError("Source archive lacks compiled pygame source")
    return {"filename": SOURCE_ARCHIVE, "sha256": sha256(archive),
            "source_commit": PYGAME_COMMIT, "source_kind": "git-archive",
            "note": "Tagged project source. Build submodules/dependency recipes not independently matched to wheel."}


def wheel_hashes(path, target):
    name, expected = WHEELS[target]
    path = Path(path)
    if (path.name != name or not path.is_file() or path.is_symlink()
            or not 1_000_000 <= path.stat().st_size <= MAX_WHEEL_BYTES):
        raise ValueError("Missing or suspicious official pygame-ce wheel for " + target)
    if sha256(path) != expected:
        raise ValueError("Official pygame-ce upstream wheel digest mismatch: " + target)
    hashes = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            filename = info.filename
            if (filename.startswith("/") or ".." in filename.split("/")
                    or "\\" in filename or info.file_size > MAX_WHEEL_BYTES):
                raise ValueError("Unsafe upstream wheel ZIP member")
            if not filename.lower().endswith((".so", ".dylib", ".dll", ".pyd")) and ".so." not in filename.lower():
                continue
            if info.file_size == 0:
                continue
            hashes.setdefault(hashlib.sha256(archive.read(info)).hexdigest(), []).append(filename)
    if not hashes:
        raise ValueError("Official pygame-ce wheel contains no native binary")
    return hashes


def match_installed_runtime(target, receipt, audit, wheel_hashes_map):
    if (receipt.get("status") != EXPECTED_RECEIPT_STATUS[target]
            or receipt.get("source_preview_revision") != RC_APP_COMMIT
            or receipt.get("native_core_count") != 11
            or receipt.get("console_profiles") != 18
            or receipt.get("public_release_approved") is not False
            or receipt.get("final_release_approved") is not False
            or receipt.get("sdl_runtime_audit") != "SDL_RUNTIME_AUDIT.json"):
        raise ValueError("Full-console RC1 receipt not pinned or still approved: " + target)
    if (audit.get("status") != "UNRELEASED_3_1_SDL_RUNTIME_INVENTORY"
            or audit.get("target") != target
            or audit.get("pygame_version") != PYGAME_VERSION
            or audit.get("pygame_distribution") != "pygame-ce"
            or audit.get("redistribution_approved") is not False
            or audit.get("original_sources_verified") is not False
            or audit.get("lgpl_relinking_reviewed") is not False):
        raise ValueError("Missing/approved or wrong frozen SDL runtime audit: " + target)
    native = audit.get("native_candidates")
    if not isinstance(native, list) or not native:
        raise ValueError("No native library evidence: " + target)
    hits = []
    unresolved = []
    for item in native:
        if not isinstance(item, dict):
            raise ValueError("Invalid native file entry: " + target)
        file_path = item.get("path")
        hash_value = item.get("sha256")
        if (not isinstance(file_path, str) or not file_path
                or file_path.startswith("/") or ".." in file_path.split("/")
                or not isinstance(hash_value, str) or not NATIVE_SHA.fullmatch(hash_value)):
            raise ValueError("Unsafe or incorrect native file digest: " + target)
        found = wheel_hashes_map.get(hash_value)
        entry = {"installed_path": file_path, "sha256": hash_value}
        if found:
            entry["official_wheel_paths"] = sorted(found)
            hits.append(entry)
        else:
            unresolved.append(entry)
    return {
        "target": target, "installer": receipt.get("installer"),
        "installed_runtime_entries": len(native),
        "exact_wheel_byte_matches": hits,
        "unmatched_native_candidates": unresolved,
        "wheel_match_count": len(hits),
        "native_coverage": "Partially mapped; sign/repack may alter binary bytes",
        "wheel_provenance_in_installed_bundle_proven": False,
        "sdl_native_source_correspondence_proven": False,
        "runtime_relinking_verified": False,
    }


def make_review(input_dir, wheels_dir, source_archive, output):
    input_dir, wheels_dir, source_archive = map(Path, (input_dir, wheels_dir, source_archive))
    output = Path(output)
    if output.resolve().is_relative_to(input_dir.resolve()):
        raise ValueError("Output must not overwrite evidence input")
    source_record = validate_source_archive(source_archive)
    reports = []
    hashes = {}
    for target in TARGETS:
        folder = input_dir / target
        receipt_name = ("FULL_LIBRARY_QA_RECEIPT.json" if target == "linux-x64"
                        else "FULL_WINDOWS_QA_RECEIPT.json" if target == "windows-x64"
                        else "FULL_MACOS_QA_RECEIPT.json")
        receipt = _read_json(folder / receipt_name)
        audit = _read_json(folder / "SDL_RUNTIME_AUDIT.json")
        filename, digest = WHEELS[target]
        if digest not in hashes:
            hashes[digest] = wheel_hashes(wheels_dir / filename, target)
        report = match_installed_runtime(target, receipt, audit, hashes[digest])
        report["upstream_wheel"] = {"filename": filename, "published_sha256": digest,
                                    "release": "https://github.com/pygame-community/pygame-ce/releases/tag/2.5.8"}
        report["full_qa_run"] = RC_RUN
        reports.append(report)
    output.mkdir(parents=True, exist_ok=True)
    source_out = output / SOURCE_ARCHIVE
    if source_archive.resolve() != source_out.resolve():
        shutil.copyfile(source_archive, source_out)
    result = {
        "schema_version": 1,
        "status": "UNRELEASED_3_1_SDL_CORRESPONDENCE_REVIEW_INCOMPLETE",
        "pygame_version": PYGAME_VERSION,
        "pygame_git_tag": "2.5.8",
        "pygame_git_commit": PYGAME_COMMIT,
        "upstream_source": source_record,
        "readme": "Pinned tagged source and exact upstream wheel bytes. Native SDL build provenance and LGPL relinking still need review.",
        "full_rc_qa_run": RC_RUN,
        "source_app_commit": RC_APP_COMMIT,
        "targets": reports,
        "build_wheel_provenance_verified": False,
        "bundled_sdl_sources_matched": False,
        "lgpl_relinking_reviewed": False,
        "corresponding_source_complete": False,
        "redistribution_approved": False,
    }
    (output / "SDL_SOURCE_REVIEW.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files = [output / SOURCE_ARCHIVE, output / "SDL_SOURCE_REVIEW.json"]
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256(file)}  {file.name}\n" for file in files), encoding="utf-8")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--wheels", type=Path, required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = make_review(args.input, args.wheels, args.source, args.output)
    print("Prepared pygame-ce source evidence and official wheels for",
          len(result["targets"]), "unreleased targets; LGPL approval remains FALSE")


if __name__ == "__main__":
    main()
