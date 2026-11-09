"""Compare frozen original Dolphin buildbot Sys ZIP with exact upstream source.

This is source-byte evidence only, never permission to redistribute any
commercial game, firmware, or emulator binary. The original pinned libretro
Dolphin Git revision may differ from the buildbot asset's mutable provenance;
all differences must remain visible, not silently waved away.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
import zipfile

from tools.fetch_dolphin_sys import (
    _safe_member, MAX_DOWNLOAD_BYTES, MAX_EXTRACTED_BYTES,
    MAX_SINGLE_FILE, MAX_FILES,
)

PIN = "32c61f9d0e933331bb7087ba57e96883241b4960"
MAX_REPORT = 4000


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def require_checkout(checkout):
    checkout = Path(checkout)
    if checkout.is_symlink() or not checkout.is_dir():
        raise ValueError("Missing safe original pinned Dolphin checkout")
    def git(*parts):
        return subprocess.check_output(
            ["git", "-C", str(checkout), *parts],
            stderr=subprocess.PIPE, text=True, timeout=60).strip()
    if git("rev-parse", "HEAD") != PIN:
        raise ValueError("Dolphin Sys source checkout changed from pinned parent")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Original source checkout has modified tracked files")
    return checkout / "Data" / "Sys"


def source_files(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Missing safe pinned original Data/Sys source directory")
    content = {}
    total = 0
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise ValueError("Dolphin Sys source tree contains symlink")
        if p.is_dir():
            continue
        if not p.is_file() or not stat.S_ISREG(p.stat().st_mode):
            raise ValueError("Dolphin Sys source contains non-file data")
        name = p.relative_to(root).as_posix()
        if len(content) >= MAX_FILES or name in content or len(name) > 512:
            raise ValueError("Source Sys too many/duplicate/long names")
        length = p.stat().st_size
        total += length
        if length > MAX_SINGLE_FILE or total > MAX_EXTRACTED_BYTES:
            raise ValueError("Source Sys oversized")
        content[name] = (sha(p.read_bytes()), length)
    if not content.get("codehandler.bin") or content["codehandler.bin"][1] == 0:
        raise ValueError("Original Sys source missing required codehandler.bin")
    return content


def archive_files(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_DOWNLOAD_BYTES:
        raise ValueError("Missing or oversized preserved original Dolphin Sys archive")
    data = path.read_bytes()
    if not data or len(data) > MAX_DOWNLOAD_BYTES:
        raise ValueError("Missing preserved original Sys archive")
    records = {}
    total = 0
    with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = _safe_member(info.filename)
            if name is None:
                continue
            if (info.external_attr >> 16 and
                    stat.S_ISLNK(info.external_attr >> 16)):
                raise ValueError("Original archived Dolphin Sys contains unsafe symlink")
            relative = name.as_posix()
            if relative in records or len(relative) > 512 or len(records) >= MAX_FILES:
                raise ValueError("Original Sys duplicate/too many/long files")
            if info.file_size > MAX_SINGLE_FILE:
                raise ValueError("Original Sys archive file oversized")
            total += info.file_size
            if total > MAX_EXTRACTED_BYTES:
                raise ValueError("Original Sys archive content oversized")
            payload = archive.read(info)
            if len(payload) != info.file_size:
                raise ValueError("Original Sys archive file size mismatch")
            records[relative] = (sha(payload), len(payload))
    if not records.get("codehandler.bin") or records["codehandler.bin"][1] == 0:
        raise ValueError("Original archived Sys is missing codehandler.bin")
    return sha(data), records


def compare(checkout, archive, output, *, verify_git=require_checkout):
    root = verify_git(checkout)
    source = source_files(root)
    old_sha, archived = archive_files(archive)
    original = set(source)
    unpacked = set(archived)
    matched = sorted(name for name in original & unpacked
                     if source[name] == archived[name])
    changed = sorted(name for name in original & unpacked
                     if source[name] != archived[name])
    missing = sorted(original - unpacked)
    additional = sorted(unpacked - original)
    exact = len(matched) == len(source) == len(archived)
    record = {
        "schema_version": 1,
        "status": "UNAPPROVED-ORIGINAL-DOLPHIN-SYS-SOURCE-COMPARISON",
        "pinned_upstream_parent_commit": PIN,
        "upstream_source_repository": "https://github.com/libretro/dolphin",
        "preserved_buildbot_dolphin_zip_sha256": old_sha,
        "pinned_source_file_count": len(source),
        "archived_sys_file_count": len(archived),
        "byte_identical_file_count": len(matched),
        "changed_source_files": changed,
        "missing_archive_files": missing,
        "extra_archive_files": additional,
        "archive_matches_pinned_upstream_source_byte_for_byte": exact,
        "mutable_historical_asset_build_revision_proven": False,
        "third_party_source_and_license_rights_reviewed": False,
        "original_source_native_binary_equivalence_proven": False,
        "public_binary_distribution_approved": False,
    }
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Refuse overwrite of original Dolphin Sys source audit")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", "utf-8")
    return record


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkout", type=Path, required=True)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--require-exact-match", action="store_true")
    args = p.parse_args(argv)
    try:
        result = compare(args.checkout, args.archive, args.output)
    except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile,
            subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        p.exit(1, f"Original Dolphin Sys source comparison FAILED: {exc}\n")
    print("Preserved Dolphin Sys vs original pinned source:",
          result["byte_identical_file_count"], "/", result["pinned_source_file_count"],
          "identical;",
          len(result["changed_source_files"]), "changed;",
          len(result["missing_archive_files"]), "missing;",
          len(result["extra_archive_files"]), "extra;",
          "redistribution approval FALSE")
    if args.require_exact_match and not result["archive_matches_pinned_upstream_source_byte_for_byte"]:
        p.exit(1, "Preserved buildbot Dolphin Sys does NOT equal original pinned source\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
