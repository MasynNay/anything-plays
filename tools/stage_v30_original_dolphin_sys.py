"""Import an exact source-backed Dolphin Sys ZIP into an offline 3.0 trial.

The original upstream Data/Sys Git *tree* is reconstructed from ZIP bytes and
file modes, rather than trusting the research artifact's unapproved JSON. This
proves byte identity with an immutable public Git tree, not third-party rights
or correspondence with an old emulator binary. Never enables release flags.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re
import stat
import zipfile

from tools.prepare_v30_dolphin_source_sys import (
    DOLPHIN_REV, PINNED_SYS_TREE_SHA1, ZIP_PREFIX,
    MAX_FILES, MAX_TOTAL, MAX_SINGLE, MAX_ZIP_BYTES, _git_tree_sha,
)

ARCHIVE = "Dolphin.zip"
REPORT = "DOLPHIN_ORIGINAL_SOURCE_SYS_UNAPPROVED.json"
CHECKSUMS = "SHA256SUMS.txt"
FILES = frozenset((ARCHIVE, REPORT, CHECKSUMS))
MAX_REPORT_BYTES = 600_000
HEX64 = re.compile(r"[a-f0-9]{64}\Z")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def exact_original_sys_artifact(folder):
    root = Path(folder)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Source-backed Dolphin Sys input directory is missing or unsafe")
    members = list(root.iterdir())
    if (len(members) != 3 or {p.name for p in members} != FILES
            or any(p.is_symlink() or not p.is_file() for p in members)):
        raise ValueError("Source-backed Dolphin Sys research artifact has missing/extra files")
    if (not 0 < (root / REPORT).stat().st_size <= MAX_REPORT_BYTES
            or not 0 < (root / ARCHIVE).stat().st_size <= MAX_ZIP_BYTES
            or not 0 < (root / CHECKSUMS).stat().st_size < 1000):
        raise ValueError("Pinned original Dolphin Sys input exceeds safe limits")
    data = (root / ARCHIVE).read_bytes()
    manifest_bytes = (root / REPORT).read_bytes()
    report = json.loads(manifest_bytes)
    if (not isinstance(report, dict) or report.get("schema_version") != 1
            or report.get("status") != "UNAPPROVED-SOURCE-EXACT-DOLPHIN-SYS-CANDIDATE"
            or report.get("upstream_source_repository") != "https://github.com/libretro/dolphin"
            or report.get("original_parent_source_commit") != DOLPHIN_REV
            or report.get("pinned_git_data_sys_tree_sha1") != PINNED_SYS_TREE_SHA1
            or report.get("independently_reconstructed_git_data_sys_tree_sha1")
                != PINNED_SYS_TREE_SHA1
            or report.get("matches_original_source_bytes") is not True
            or report.get("binary_to_source_compilation_verified") is not False
            or report.get("all_third_party_fonts_and_asset_rights_independently_reviewed") is not False
            or report.get("public_binary_distribution_approved") is not False):
        raise ValueError("Unapproved Dolphin original Sys source identity/rights forged")
    for field in ("original_parent_source_tar_sha256", "dolphin_sys_zip_sha256"):
        if not isinstance(report.get(field), str) or not HEX64.fullmatch(report[field]):
            raise ValueError("Missing immutable original Dolphin Sys source/archive hash")
    if report["dolphin_sys_zip_sha256"] != digest(data):
        raise ValueError("Original pinned Dolphin Sys ZIP SHA256 changed")
    if report.get("dolphin_sys_zip_size") != len(data):
        raise ValueError("Original pinned Dolphin Sys ZIP size changed")
    expected_checksum_lines = {
        f"{digest(data)}  {ARCHIVE}",
        f"{digest(manifest_bytes)}  {REPORT}",
    }
    if set((root / CHECKSUMS).read_text("ascii").splitlines()) != expected_checksum_lines:
        raise ValueError("Original pinned Sys SHA256SUMS mismatch")
    file_table = report.get("files")
    if not isinstance(file_table, dict) or len(file_table) != report.get("dolphin_sys_file_count"):
        raise ValueError("Original source Sys file inventory absent")
    if not 5 <= len(file_table) <= MAX_FILES:
        raise ValueError("Original source Sys file count outside source limits")
    entries = {}
    seen_lower = set()
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as src:
        infos = src.infolist()
        if len(infos) != len(file_table):
            raise ValueError("Original source Sys ZIP file count mismatched")
        for info in infos:
            name = info.filename
            if not name.startswith(ZIP_PREFIX):
                raise ValueError("Unexpected original Dolphin Sys ZIP destination")
            relative = name[len(ZIP_PREFIX):]
            pieces = relative.split("/")
            if (info.is_dir() or not relative or "\\" in relative
                    or "\x00" in relative or len(relative) > 512
                    or any(not piece or piece in (".", "..") or ":" in piece for piece in pieces)
                    or relative.casefold() in seen_lower):
                raise ValueError("Original Dolphin Sys ZIP path is unsafe/duplicated")
            mode = info.external_attr >> 16
            if not stat.S_ISREG(mode) or (mode & 0o6000):
                raise ValueError("Source-backed Sys ZIP includes nonregular/privileged file")
            if info.file_size < 0 or info.file_size > MAX_SINGLE:
                raise ValueError("Original Sys ZIP member size outside safe limit")
            total += info.file_size
            if total > MAX_TOTAL:
                raise ValueError("Original Sys ZIP expands beyond safe limit")
            row = file_table.get(relative)
            if (not isinstance(row, dict) or row.get("size_bytes") != info.file_size
                    or not isinstance(row.get("sha256"), str) or
                    not HEX64.fullmatch(row["sha256"])):
                raise ValueError("Original Sys file not present in pinned source report")
            with src.open(info) as handle:
                raw = handle.read(info.file_size + 1)
            if len(raw) != info.file_size or digest(raw) != row["sha256"]:
                raise ValueError("Dolphin Sys original source file bytes do not match report")
            entries[relative] = (raw, bool(mode & stat.S_IXUSR))
            seen_lower.add(relative.casefold())
    if set(entries) != set(file_table) or not entries.get("codehandler.bin"):
        raise ValueError("Dolphin original Sys missing mandatory source file")
    if report.get("dolphin_sys_extracted_bytes") != total:
        raise ValueError("Dolphin source Sys original uncompressed size changed")
    original_git_tree = _git_tree_sha(entries)
    if original_git_tree != PINNED_SYS_TREE_SHA1:
        raise ValueError("Actual ZIP bytes do not match immutable Dolphin original Git tree")
    return data, {
        "source_revision": DOLPHIN_REV,
        "source_repository": "https://github.com/libretro/dolphin",
        "original_git_data_sys_tree_sha1": original_git_tree,
        "original_source_tar_sha256": report["original_parent_source_tar_sha256"],
        "pinned_sys_zip_sha256": digest(data),
        "pinned_sys_zip_bytes": len(data),
        "pinned_sys_files": len(entries),
        "source_correspondence_to_archived_buildbot_dolphin_verified": False,
        "source_asset_rights_independently_approved": False,
        "public_distribution_approved": False,
    }
