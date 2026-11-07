"""Create an UNAPPROVED Dolphin binary + matching Sys catalog candidate.

A full source/license and real-game QA review must explicitly grant both
approval flags before an archive could pass the in-app installer. This tool
does not upload, publish, sign, or pretend to certify the native binary.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import zipfile

from anything_plays.core_packs import (
    MAX_BINARY_BYTES, PACK_PREFIX, RELEASE_TAG_RE, target_identity, UPSTREAM_REPOS,
)
from anything_plays.dolphin_pack import (
    MAX_FILES, MAX_SYS_TOTAL, MAX_SYS_SINGLE, SYS_PREFIX, SYS_MANIFEST,
    make_sys_index, sha256, _safe_name,
)


def make_candidate_dolphin_pack(
    cores_dir, output_dir, tag, *, target=None,
    license_reviewed=False, runtime_tested=False,
):
    if not isinstance(tag, str) or not RELEASE_TAG_RE.fullmatch(tag):
        raise ValueError("Dolphin package must use an approved catalog-tag shape")
    target = target or target_identity()[0]
    ext = {"windows-x64": ".dll", "macos-arm64": ".dylib",
           "macos-x64": ".dylib", "linux-x64": ".so"}.get(target)
    if ext is None:
        raise ValueError("Unknown Dolphin native platform")
    cores = Path(cores_dir)
    filename = "dolphin_libretro" + ext
    binary_path = cores / filename
    if binary_path.is_symlink() or not binary_path.is_file():
        raise ValueError("Missing or symlinked Dolphin binary")
    binary = binary_path.read_bytes()
    if not 10000 < len(binary) <= MAX_BINARY_BYTES:
        raise ValueError("Dolphin binary does not meet native size budget")
    core_info = json.loads((cores / "CORE_PROVENANCE.json").read_text("utf-8"))
    core_entries = core_info.get("cores")
    if not isinstance(core_entries, list):
        raise ValueError("Missing Dolphin source provenance")
    matches = [row for row in core_entries if isinstance(row, dict)
               and row.get("name") == "dolphin"]
    if (len(matches) != 1 or matches[0].get("file") != filename
            or matches[0].get("sha256") != sha256(binary)):
        raise ValueError("Dolphin binary source provenance mismatch")
    sys_root = cores / "dolphin-emu" / "Sys"
    if sys_root.is_symlink() or not sys_root.is_dir():
        raise ValueError("Dolphin Sys is missing or symlinked")
    sys_info = json.loads(
        (cores / "DOLPHIN_SYS_PROVENANCE.json").read_text("utf-8")
    )
    original_files = sys_info.get("files")
    if not isinstance(original_files, dict):
        raise ValueError("Missing Dolphin Sys source inventory")
    files = {}
    for entry in sorted(sys_root.rglob("*")):
        if entry.is_symlink():
            raise ValueError("Dolphin Sys cannot contain symlinks")
        if not entry.is_file():
            continue
        relative = entry.relative_to(sys_root).as_posix()
        if not _safe_name(relative) or relative not in original_files:
            raise ValueError("Unrecognized Dolphin system asset")
        if entry.stat().st_size > MAX_SYS_SINGLE:
            raise ValueError("Dolphin Sys individual member exceeds budget")
        contents = entry.read_bytes()
        provenance = original_files[relative]
        if (not isinstance(provenance, dict)
                or provenance.get("sha256") != sha256(contents)
                or provenance.get("size_bytes") != len(contents)):
            raise ValueError("Dolphin Sys asset checksum differs from source")
        files[relative] = contents
    if set(files) != set(original_files):
        raise ValueError("Dolphin Sys archive is missing required files")
    if (not 5 <= len(files) <= MAX_FILES
            or sum(len(x) for x in files.values()) > MAX_SYS_TOTAL):
        raise ValueError("Dolphin Sys archive exceeds safe limits")
    archive_sha = sys_info.get("archive_sha256")
    if (not isinstance(archive_sha, str) or len(archive_sha) != 64
            or any(c not in "0123456789abcdef" for c in archive_sha)):
        raise ValueError("Unpinned Dolphin Sys source archive checksum")
    sys_index = make_sys_index(files)
    index = json.loads(sys_index)
    meta = {
        "schema": 2, "name": "dolphin", "target": target,
        "release": tag, "file": filename, "sha256": sha256(binary),
        "source_repository": "https://github.com/" + UPSTREAM_REPOS["dolphin"],
        "source_revision": matches[0].get("reported_source_revision"),
        "sys_manifest_file": SYS_MANIFEST,
        "sys_manifest_sha256": sha256(sys_index),
        "sys_file_count": index["file_count"],
        "sys_total_size_bytes": index["total_size_bytes"],
        "sys_source_archive_sha256": archive_sha,
        "third_party_license_reviewed": license_reviewed is True,
        "packaged_runtime_tested": runtime_tested is True,
    }
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    final = output / f"{PACK_PREFIX}dolphin-{target}.zip"
    if final.is_symlink():
        raise ValueError("Refusing symlinked Dolphin candidate output")
    with zipfile.ZipFile(final, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("core-pack.json", json.dumps(meta, sort_keys=True) + "\n")
        archive.writestr(filename, binary)
        archive.writestr(SYS_MANIFEST, sys_index)
        for relative, value in sorted(files.items()):
            archive.writestr(SYS_PREFIX + relative, value)
    return {
        "name": "dolphin", "target": target, "file": str(final),
        "sha256": sha256(final.read_bytes()),
        "binary_sha256": sha256(binary), "release": tag,
        "sys_file_count": len(files),
        "status": "candidate-only; needs real GameCube QA and redistribution review",
    }
