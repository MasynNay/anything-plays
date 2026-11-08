"""Bundle Dolphin's Libretro system assets during the 2.1 test build.

This is BUILD-TIME only. No end user is asked to download a Dolphin Sys ZIP.
Downloaded files are size-limited, ZIP paths are validated, and the extracted
file hashes are recorded to support exact bundle verification. These nightly
inputs are *not* approved immutable release inputs; public releases require
a preserved, reviewed archive and a source/license compliance audit.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
from tempfile import TemporaryDirectory
from urllib import request
import zipfile

SYSTEM_ASSET_URL = "https://buildbot.libretro.com/assets/system/Dolphin.zip"
MAX_DOWNLOAD_BYTES = 16 * 1024 * 1024
MAX_EXTRACTED_BYTES = 80 * 1024 * 1024
MAX_FILES = 4000
MAX_SINGLE_FILE = 16 * 1024 * 1024
ARCHIVE_NAME = "Dolphin.zip"
MANIFEST_NAME = "DOLPHIN_SYS_PROVENANCE.json"


def read_system_archive():
    """Allow test builds to use a preserved local archive instead of the net."""
    is_release = os.environ.get("AP_RELEASE_BUILD") == "1"
    v30_release = os.environ.get("AP_V30_APPROVED_RELEASE") == "1"
    if is_release:
        if not v30_release:
            raise ValueError(
                "Dolphin Sys requires approved/pinned inputs; the historical v2.0 release excludes it"
            )
        if not os.environ.get("AP_CORE_ARCHIVE_DIR", "").strip():
            raise ValueError(
                "3.0 official release needs preserved, reviewed Dolphin.zip"
            )
        # Do not access the mutable upstream URL in release mode.
        from tools.v30_release_lock import load_approved_lock
        load_approved_lock()
    cached = os.environ.get("AP_CORE_ARCHIVE_DIR", "").strip()
    if cached:
        local = Path(cached).expanduser() / ARCHIVE_NAME
        if local.is_symlink():
            raise ValueError("Refusing symlinked Dolphin system archive")
        with local.open("rb") as stream:
            data = stream.read(MAX_DOWNLOAD_BYTES + 1)
    else:
        url = request.Request(
            SYSTEM_ASSET_URL,
            headers={"User-Agent": "AnythingPlays-2.1-test-builder"},
        )
        with request.urlopen(url, timeout=45) as response:
            data = response.read(MAX_DOWNLOAD_BYTES + 1)
    if not data or len(data) > MAX_DOWNLOAD_BYTES:
        raise ValueError("Dolphin system ZIP is empty or too large")
    if is_release:
        # Do not extract unapproved native Sys data.
        import platform
        import sys
        from tools.v30_release_lock import verify_dolphin_archive
        verify_dolphin_archive(
            load_approved_lock(), sys.platform, platform.machine(), data,
        )
    # Preserve exactly the upstream bytes that were verified and installed.
    # Future release candidates must reuse reviewed archives, not a newer
    # nightly served from the same mutable buildbot URL.
    capture = os.environ.get("AP_CORE_ARCHIVE_CAPTURE_DIR", "").strip()
    if capture:
        folder = Path(capture).expanduser()
        if folder.is_symlink():
            raise ValueError("Refusing symlinked Dolphin capture directory")
        folder.mkdir(parents=True, exist_ok=True)
        archived = folder / ARCHIVE_NAME
        if archived.is_symlink():
            raise ValueError("Refusing symlinked Dolphin archive destination")
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(
            prefix=".dolphin-capture-", suffix=".zip",
            dir=folder, delete=False,
        ) as stream:
            staged = Path(stream.name)
            try:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            except BaseException:
                staged.unlink(missing_ok=True)
                raise
        os.replace(staged, archived)
        print(f"Preserved Dolphin Sys source ZIP: {archived} "
              f"sha256={hashlib.sha256(data).hexdigest()}", flush=True)
    return data


def _safe_member(filename):
    """Extract only children of Sys, rejecting traversal and unusual members."""
    raw = filename.replace("\\", "/")
    path = PurePosixPath(raw)
    if (path.is_absolute() or "\x00" in raw or
            any(part in (".", "..") for part in raw.split("/")) or
            any(":" in part for part in path.parts)):
        raise ValueError(f"Unsafe Dolphin system ZIP member: {filename}")
    parts = path.parts
    for i in range(len(parts) - 1):
        if parts[i] == "dolphin-emu" and parts[i + 1] == "Sys":
            tail = parts[i + 2:]
            return PurePosixPath(*tail) if tail else None
    # Some preserved upstream archives start directly at Data/Sys.
    for i in range(len(parts)):
        if parts[i] == "Sys" and i + 1 < len(parts):
            return PurePosixPath(*parts[i + 1:])
    return None


def extract_dolphin_sys(archive_bytes, destination):
    """Stage a bounded, hash-inventoried Sys directory without ZIP traversal."""
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    if (root / "dolphin-emu").is_symlink():
        raise ValueError("Refusing symlinked Dolphin system directory")

    archive_digest = hashlib.sha256(archive_bytes).hexdigest()
    inventory = {}
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        entries = []
        total = 0
        for item in archive.infolist():
            if item.is_dir():
                continue
            name = _safe_member(item.filename)
            if name is None:
                continue
            if item.external_attr >> 16 and stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("Symlink entries are not allowed in Dolphin Sys")
            # Dolphin ships intentional zero-byte GraphicMods text markers.
            # Empty files are valid; only negative/oversized lengths are bad.
            if (item.file_size < 0 or item.file_size > MAX_SINGLE_FILE):
                raise ValueError(f"Invalid Dolphin Sys member size: {item.filename}")
            if str(name) in inventory:
                raise ValueError("Duplicate Dolphin Sys path")
            total += item.file_size
            if total > MAX_EXTRACTED_BYTES or len(entries) >= MAX_FILES:
                raise ValueError("Dolphin Sys archive exceeds safe extraction limit")
            entries.append((item, name))
            inventory[str(name)] = None

        if "codehandler.bin" not in inventory or len(entries) < 5:
            raise ValueError("Dolphin Sys archive is missing required system data")

        with TemporaryDirectory(prefix="dolphin-sys-", dir=root) as stage_name:
            stage = Path(stage_name)
            sys_folder = stage / "Sys"
            for item, relative in entries:
                target = sys_folder.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as source, target.open("wb") as output:
                    data = source.read(item.file_size + 1)
                    if len(data) != item.file_size:
                        raise ValueError("Incorrect Dolphin Sys member length")
                    output.write(data)
                inventory[str(relative)] = {
                    "size_bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }

            destination_root = root / "dolphin-emu"
            if destination_root.exists():
                if not destination_root.is_dir():
                    raise ValueError("Dolphin system destination is not a directory")
                shutil.rmtree(destination_root)
            shutil.move(str(stage), str(destination_root))
            # shutil.move(stage, dolphin-emu) moves Sys/ under dolphin-emu;
            # TemporaryDirectory's cleanup tolerates its staged path moving.

    manifest = {
        "source_url": SYSTEM_ASSET_URL,
        "archive_sha256": archive_digest,
        "archive_size_bytes": len(archive_bytes),
        "file_count": len(entries),
        "files": inventory,
    }
    (root / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def fetch_dolphin_sys(destination):
    """Download at build-time and produce cores/dolphin-emu/Sys."""
    return extract_dolphin_sys(read_system_archive(), destination)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", nargs="?", default="cores")
    args = parser.parse_args()
    print(json.dumps(fetch_dolphin_sys(args.destination), indent=2))
