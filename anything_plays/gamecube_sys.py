"""Provide writable Dolphin Sys files without modifying the installed core.

Linux DEB files live in root-owned /opt. Dolphin's native GameCube core can
open Sys/codehandler.bin for write access, so handing it /opt via Libretro's
GET_SYSTEM_DIRECTORY fails with EACCES. The original bundled Sys and managed
core packs MUST remain immutable. On Linux only, stage a validated, private,
writable copy in XDG user data; the native core still comes from the bundle.

Cache content is keyed by every source Sys filename, length and SHA-256.
A stale/tampered copy is rebuilt under a process lock. No sudo, chmod of /opt,
external Dolphin executable, downloads, or writes to ROM directories.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import uuid

from anything_plays.gamecube_software import packaged_dolphin_system_directory
from anything_plays.libretro_save import _user_save_directory

MAX_FILES = 4000
MAX_TOTAL_BYTES = 80 * 1024 * 1024
MAX_FILE_BYTES = 16 * 1024 * 1024


def _inventory(folder):
    """Return (identity, relative filenames), rejecting links and oversized data."""
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Unsafe or missing Dolphin system directory")
    entries = {}
    total = 0
    digest = hashlib.sha256()
    for item in sorted(folder.rglob("*")):
        if item.is_symlink():
            raise ValueError("Dolphin Sys cannot contain symbolic links")
        if item.is_dir():
            continue
        if not item.is_file() or not stat.S_ISREG(item.stat().st_mode):
            raise ValueError("Dolphin Sys contains a nonregular file")
        relative = item.relative_to(folder).as_posix()
        if len(relative) > 512 or len(entries) >= MAX_FILES:
            raise ValueError("Dolphin Sys has too many or overly long filenames")
        length = item.stat().st_size
        total += length
        if length > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise ValueError("Dolphin Sys exceeds its safe data limit")
        h = hashlib.sha256()
        with item.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                h.update(block)
        checksum = h.hexdigest()
        entries[relative] = (length, checksum)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(length).encode("ascii"))
        digest.update(b"\0")
        digest.update(checksum.encode("ascii"))
        digest.update(b"\n")
    if not entries.get("codehandler.bin") or entries["codehandler.bin"][0] == 0:
        raise ValueError("Dolphin Sys is missing codehandler.bin")
    return digest.hexdigest(), entries


def _valid_copy(root, expected):
    folder = Path(root) / "dolphin-emu" / "Sys"
    if Path(root).is_symlink() or not folder.is_dir():
        return False
    try:
        _, actual = _inventory(folder)
        if actual != expected:
            return False
        # A valid read-only copy is not sufficient: Dolphin needs to open
        # codehandler.bin for writing, even though the source is immutable.
        return os.access(folder / "codehandler.bin", os.W_OK)
    except (OSError, ValueError):
        return False


def _copy_sys(source, staging, expected):
    target = staging / "dolphin-emu" / "Sys"
    target.mkdir(parents=True, mode=0o700)
    for relative in expected:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copyfile(source / relative, destination)
        destination.chmod(0o600)
    # Refuse to activate a partial or concurrently modified source copy.
    if not _valid_copy(staging, expected):
        raise RuntimeError("Dolphin user-owned Sys copy failed integrity verification")


def writable_dolphin_system_directory(core_path):
    """Return Dolphin's system root; Linux gets a private user-writable copy.

    The Libretro callback expects the *parent* of dolphin-emu/Sys, not Sys
    itself. Other platforms retain the existing path and behavior.
    """
    packaged = packaged_dolphin_system_directory(core_path)
    if not sys.platform.startswith("linux"):
        return packaged
    import fcntl  # Linux-only: unavailable on Windows, which uses bundled Sys.
    source = packaged / "dolphin-emu" / "Sys"
    identity, expected = _inventory(source)
    # Keep Dolphin runtime files separate from its user memory cards/saves.
    base = _user_save_directory().parent / "dolphin-system"
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    if base.is_symlink():
        raise ValueError("Dolphin runtime cache directory cannot be a symlink")
    target = base / identity
    lock_fd = os.open(
        str(base / ".prepare.lock"),
        os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        if _valid_copy(target, expected):
            return target
        staging = Path(tempfile.mkdtemp(prefix=".stage-", dir=base))
        quarantine = None
        try:
            _copy_sys(source, staging, expected)
            if target.exists() or target.is_symlink():
                if target.is_symlink():
                    raise ValueError("Dolphin Sys cache path cannot be a symlink")
                quarantine = base / (".stale-" + uuid.uuid4().hex)
                os.replace(target, quarantine)
            os.replace(staging, target)
            if not _valid_copy(target, expected):
                raise RuntimeError("Dolphin user Sys copy is not writable")
        finally:
            if staging.exists():
                shutil.rmtree(staging)
            if quarantine is not None and quarantine.exists():
                shutil.rmtree(quarantine)
        return target
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
