"""Build an UNAPPROVED 3.0 native-core lock from preserved, checksum-verified ZIPs.

This tool takes the original four-platform CI input artifacts as arguments.
It verifies each original Libretro ZIP and its embedded library (11 per OS),
and Dolphin Sys (one per OS), before generating a complete immutable candidate.
It never marks source correspondence or redistribution permissions as approved.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import tempfile
import stat
from pathlib import Path
import re
import sys
import zipfile

from fetch_mgba_core import CORE_NAMES, OPTIONAL_V21_CORES

CORES = frozenset((*CORE_NAMES, *OPTIONAL_V21_CORES))
PLATFORMS = {
    "windows-x64": ("windows-x86_64", ".dll"),
    "macos-arm64": ("macos-arm64", ".dylib"),
    "macos-x64": ("macos-x86_64", ".dylib"),
    "linux-x64": ("linux-x86_64", ".so"),
}
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_PROVENANCE_BYTES = 1024 * 1024  # metadata only; native binaries are verified separately
MAX_NATIVE_PAYLOAD_BYTES = 512 * 1024 * 1024  # reject decompression bombs before extraction
MAX_ORIGINAL_ARCHIVE_BYTES = MAX_NATIVE_PAYLOAD_BYTES + 1024 * 1024  # ZIP overhead allowance


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_native_payload(raw: bytes, expected_file: str, platform: str, name: str) -> bytes:
    """Read the single matching native file, rejecting ZIP symlink impersonation."""
    with zipfile.ZipFile(io.BytesIO(raw)) as inner:
        # A native core archive must contain exactly one regular payload.
        # Reject unexpected files, directories and duplicate entries rather
        # than silently blessing an archive with unverified extra content.
        members = inner.infolist()
        if len(members) != 1 or members[0].filename != expected_file or members[0].is_dir():
            raise ValueError(f"{platform}: invalid core ZIP payload: {name}")
        member = members[0]
        if member.create_system == 3:
            # A ZIP entry can impersonate a native file while declaring a FIFO,
            # socket, block or character device in its Unix mode. Some ordinary
            # ZIP writers omit the file-type bits, so accept those as well.
            kind = stat.S_IFMT(member.external_attr >> 16)
            if kind == stat.S_IFLNK:
                raise ValueError(f"{platform}: symlinked core ZIP payload: {name}")
            if kind not in (0, stat.S_IFREG):
                raise ValueError(f"{platform}: non-regular core ZIP payload: {name}")
        if member.file_size > MAX_NATIVE_PAYLOAD_BYTES:
            raise ValueError(f"{platform}: oversized native core ZIP payload: {name}")
        with inner.open(member) as handle:
            payload = handle.read(MAX_NATIVE_PAYLOAD_BYTES + 1)
        if len(payload) > MAX_NATIVE_PAYLOAD_BYTES:
            raise ValueError(f"{platform}: native core ZIP payload exceeds limit: {name}")
        return payload


def read_original_archive(outer: zipfile.ZipFile, archive_name: str, platform: str) -> bytes:
    """Bound untrusted outer ZIP member expansion before hashing its contents."""
    entry = outer.getinfo(archive_name)
    if entry.is_dir() or entry.file_size > MAX_ORIGINAL_ARCHIVE_BYTES:
        raise ValueError(f"{platform}: oversized or invalid original archive: {archive_name}")
    with outer.open(entry) as handle:
        raw = handle.read(MAX_ORIGINAL_ARCHIVE_BYTES + 1)
    if len(raw) > MAX_ORIGINAL_ARCHIVE_BYTES:
        raise ValueError(f"{platform}: original archive exceeds limit: {archive_name}")
    return raw



def read_preserved_provenance(outer: zipfile.ZipFile, entry: zipfile.ZipInfo, platform: str) -> dict:
    """Reject oversized metadata before and during ZIP decompression."""
    if entry.is_dir() or entry.file_size > MAX_PROVENANCE_BYTES:
        raise ValueError(f"{platform}: oversized or invalid preserved provenance")
    with outer.open(entry) as handle:
        payload = handle.read(MAX_PROVENANCE_BYTES + 1)
    if len(payload) > MAX_PROVENANCE_BYTES:
        raise ValueError(f"{platform}: preserved provenance exceeds limit")
    record = json.loads(payload)
    if not isinstance(record, dict):
        raise ValueError(f"{platform}: preserved provenance must be a JSON object")
    return record


def build_candidate(artifact_paths):
    if set(artifact_paths) != set(PLATFORMS):
        raise ValueError("Require preserved artifacts for exactly four platforms")
    targets = {}
    revision = None
    for platform in PLATFORMS:
        source = Path(artifact_paths[platform])
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Missing regular original-input artifact for {platform}")
        target_id, suffix = PLATFORMS[platform]
        with zipfile.ZipFile(source) as outer:
            files = outer.namelist()
            # ZIP metadata is untrusted until exact input hashes are checked.
            # Refuse Unix symlink entries and oversized provenance before extraction.
            if any((entry.create_system == 3 and
                    stat.S_ISLNK(entry.external_attr >> 16)) for entry in outer.infolist()):
                raise ValueError(f"{platform}: symlinked preserved ZIP member")
            provenance_entry = outer.getinfo("PRESERVED_NATIVE_INPUTS.json") if "PRESERVED_NATIVE_INPUTS.json" in files else None
            if provenance_entry is not None and provenance_entry.file_size > MAX_PROVENANCE_BYTES:
                raise ValueError(f"{platform}: oversized preserved provenance")
            if len(files) != len(set(files)):
                raise ValueError(f"{platform}: duplicate ZIP member")
            if "PRESERVED_NATIVE_INPUTS.json" not in files:
                raise ValueError(f"{platform}: preserved provenance is missing")
            record = read_preserved_provenance(outer, provenance_entry, platform)
            if not isinstance(record, dict):
                raise ValueError(f"{platform}: preserved provenance must be a JSON object")
            source_sha = record.get("source_revision")
            if not isinstance(source_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", source_sha):
                raise ValueError(f"{platform}: missing source revision")
            if revision is None:
                revision = source_sha
            if revision != source_sha:
                raise ValueError("Candidate platforms do not share a source commit")
            if (record.get("target") != platform
                    or record.get("status") != "UNAPPROVED-TEST-INPUTS"
                    or record.get("public_distribution_approved") is not False
                    or record.get("original_archive_count") != 12):
                raise ValueError(f"{platform}: invalid or accidentally approved input status")
            manifest = record.get("source_core_provenance")
            if not isinstance(manifest, dict):
                raise ValueError(f"{platform}: core provenance missing")
            names = manifest.get("cores")
            if not isinstance(names, list) or len(names) != 11:
                raise ValueError(f"{platform}: expected 11 native core records")
            if any(not isinstance(row, dict) for row in names):
                raise ValueError(f"{platform}: malformed native core provenance row")
            if any(not isinstance(row.get("name"), str) for row in names):
                raise ValueError(f"{platform}: native core name must be a string")
            by_name = {x["name"]: x for x in names}
            if set(by_name) != CORES or len(by_name) != len(names):
                raise ValueError(f"{platform}: missing or unexpected emulator core")
            file_table = record.get("files")
            if not isinstance(file_table, list) or len(file_table) != 12:
                raise ValueError(f"{platform}: expected 12 original archives")
            if any(not isinstance(row, dict) for row in file_table):
                raise ValueError(f"{platform}: malformed original archive record")
            if any(not isinstance(row.get("name"), str) for row in file_table):
                raise ValueError(f"{platform}: archive name must be a string")
            archive_index = {x["name"]: x for x in file_table}
            if len(archive_index) != 12 or set(outer.namelist()) != set(archive_index) | {"PRESERVED_NATIVE_INPUTS.json"}:
                raise ValueError(f"{platform}: unrecognized original input file")
            locked = {}
            for name in sorted(CORES):
                core = by_name[name]
                expected_file = name + "_libretro" + suffix
                if core.get("file") != expected_file:
                    raise ValueError(f"{platform}: wrong core architecture for {name}")
                archive_name = expected_file + ".zip"
                zip_record = archive_index.get(archive_name)
                if not isinstance(zip_record, dict):
                    raise ValueError(f"{platform}: missing archive for {name}")
                raw = read_original_archive(outer, archive_name, platform)
                if (hash_bytes(raw) != core.get("archive_sha256")
                        or hash_bytes(raw) != zip_record.get("sha256")
                        or len(raw) != core.get("archive_size_bytes")
                        or len(raw) != zip_record.get("size_bytes")):
                    raise ValueError(f"{platform}: changed original archive: {name}")
                payload = read_native_payload(raw, expected_file, platform, name)
                if len(payload) != core.get("size_bytes") or hash_bytes(payload) != core.get("sha256"):
                    raise ValueError(f"{platform}: changed native library: {name}")
                locked[name] = {
                    "file": expected_file,
                    "native_sha256": core["sha256"],
                    "native_size_bytes": core["size_bytes"],
                    "original_archive_sha256": core["archive_sha256"],
                    "original_archive_size_bytes": core["archive_size_bytes"],
                    "upstream_reported_revision": core.get("reported_source_revision"),
                    "upstream_source_repository": core.get("source_repository_url"),
                    "reported_library_version": core.get("libretro_library_version"),
                    "corresponding_source_verified": False,
                    "redistribution_approved": False,
                }
            sysinfo = manifest.get("dolphin_system_assets")
            index = archive_index.get("Dolphin.zip")
            if not isinstance(sysinfo, dict) or not isinstance(index, dict):
                raise ValueError(f"{platform}: original Dolphin source archive missing")
            sysbytes = read_original_archive(outer, "Dolphin.zip", platform)
            if (hash_bytes(sysbytes) != sysinfo.get("archive_sha256")
                    or hash_bytes(sysbytes) != index.get("sha256")
                    or len(sysbytes) != sysinfo.get("archive_size_bytes")
                    or len(sysbytes) != index.get("size_bytes")):
                raise ValueError(f"{platform}: original Dolphin Sys mismatch")
            targets[target_id] = {
                "cores": locked,
                "dolphin_sys": {
                    "original_archive_sha256": hash_bytes(sysbytes),
                    "original_archive_size_bytes": len(sysbytes),
                    "source_correspondence_verified": False,
                },
                "approved_for_distribution": False,
            }
    return {
        "schema_version": 1,
        "source_commit": revision,
        "status": "UNAPPROVED-FOUR-PLATFORM-3.0-CANDIDATE",
        "approved_for_binary_distribution": False,
        "native_core_count": 11,
        "system_profile_count": 18,
        "targets": targets,
        "notice": "These are exact developer-preview binary identities, not corresponding-source or third-party redistribution approval.",
    }



def write_candidate_atomic(output: Path, candidate: dict) -> None:
    """Commit a fully serialized lock without exposing partial JSON on failure."""
    if output.is_symlink():
        raise ValueError("Refusing symlinked lock output")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         prefix="." + output.name + ".", suffix=".tmp",
                                         delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(candidate, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if output.is_symlink():
            raise ValueError("Refusing symlinked lock output")
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for platform in PLATFORMS:
        p.add_argument("--" + platform, type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    artifacts = {name: getattr(args, name.replace("-", "_")) for name in PLATFORMS}
    try:
        candidate = build_candidate(artifacts)
        write_candidate_atomic(args.output, candidate)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        p.exit(1, f"Candidate lock generation failed: {error}\n")
    print(f"Locked {len(candidate['targets'])} targets with 11 original native archives and Dolphin Sys each (UNAPPROVED)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
