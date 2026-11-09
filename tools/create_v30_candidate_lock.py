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


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
            if len(files) != len(set(files)):
                raise ValueError(f"{platform}: duplicate ZIP member")
            if "PRESERVED_NATIVE_INPUTS.json" not in files:
                raise ValueError(f"{platform}: preserved provenance is missing")
            record = json.loads(outer.read("PRESERVED_NATIVE_INPUTS.json"))
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
                raw = outer.read(archive_name)
                if (hash_bytes(raw) != core.get("archive_sha256")
                        or hash_bytes(raw) != zip_record.get("sha256")
                        or len(raw) != core.get("archive_size_bytes")
                        or len(raw) != zip_record.get("size_bytes")):
                    raise ValueError(f"{platform}: changed original archive: {name}")
                with zipfile.ZipFile(io.BytesIO(raw)) as inner:
                    members = [
                        member for member in inner.infolist()
                        if member.filename == expected_file and not member.is_dir()
                    ]
                    if len(members) != 1:
                        raise ValueError(f"{platform}: invalid core ZIP payload: {name}")
                    payload = inner.read(members[0])
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
            sysbytes = outer.read("Dolphin.zip")
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
            handle.write("\\n")
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
        output = args.output
        if output.is_symlink():
            raise ValueError("Refusing symlinked lock output")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        p.exit(1, f"Candidate lock generation failed: {error}\n")
    print(f"Locked {len(candidate['targets'])} targets with 11 original native archives and Dolphin Sys each (UNAPPROVED)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
