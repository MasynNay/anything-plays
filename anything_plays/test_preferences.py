"""Seed isolated, 3.1 preview / release-candidate settings safely.

This must NEVER write to or replace the stable 3.0 preferences. Every new
candidate file is made from a complete temporary copy and hard-linked
with no-replace semantics, so concurrent startups cannot clobber settings.
The source is never modified. No configuration data is uploaded.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import tempfile

from anything_plays.build_identity import current_identity, make_identity


LEGACY_DIR = Path(".config") / "fish-plays-pokemon-studio"
TEST_DIR = Path(".config") / "anything-plays-31-preview"
PREVIOUS_PREVIEW_DIR = Path(".config") / "anything-plays-30-preview"
CANDIDATE_DIR = Path(".config") / "anything-plays-31-rc1"
MIGRATED_FILENAMES = ("preferences.json", "system_profiles.json")
MAX_SETTINGS_BYTES = 8 * 1024 * 1024


def _checked_directory(path):
    """Reject a symlinked destination instead of writing via it to stable."""
    if path.is_symlink():
        raise ValueError("A 3.1 settings destination must not be a symlink")
    if path.exists() and not path.is_dir():
        raise ValueError("A 3.1 settings destination must be a directory")
    path.mkdir(exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise ValueError("Unsafe 3.1 settings destination")


def _copy_once_atomic(source, destination):
    """Copy a complete source file, publishing only if dest does not exist.

    Hard-linking a newly completed temporary file is a create-only atomic
    operation on supported local filesystems, unlike replace/rename, which
    could overwrite settings written by another instance of the app.

    A failed or partial temporary copy is cleaned up without ever unlinking
    a destination file, including one another process created concurrently.
    """
    if destination.exists() or destination.is_symlink():
        return
    if source.is_symlink() or not source.is_file():
        return

    temporary = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(source, flags)
        with os.fdopen(descriptor, "rb") as original:
            info = os.fstat(original.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SETTINGS_BYTES:
                return
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination.parent,
                prefix=".anything-plays-31-seed-", suffix=".tmp",
                delete=False,
            ) as staged:
                temporary = Path(staged.name)
                size = 0
                while True:
                    data = original.read(1024 * 1024)
                    if not data:
                        break
                    size += len(data)
                    if size > MAX_SETTINGS_BYTES:
                        raise ValueError("Legacy settings exceed candidate size limit")
                    staged.write(data)
                staged.flush()
                os.fsync(staged.fileno())
        # One hard link inserts the finished bytes only when no target exists.
        # This does not write to existing RC preferences or stable settings.
        os.link(temporary, destination)
    except (FileExistsError, FileNotFoundError, PermissionError):
        # Another RC instance may have seeded it first. Do not touch theirs.
        pass
    except (OSError, ValueError):
        # Unsupported source permissions/filesystem/size: retain safe defaults.
        # In particular, never leave a half-copied preferences.json behind.
        pass
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def prepare_test_preferences(home=None, *, channel=None):
    """Seed private 3.1 settings from the prior preview or stable source.

    The source is read-only. RC settings and legacy settings have distinct
    directory names; both RC and preview install modes remain nonpublic.
    """
    home = Path.home() if home is None else Path(home)
    if channel is None:
        channel = current_identity()["channel"]
    identity = make_identity(channel)  # Reject unsupported/stable aliases.
    root = home / ".config"
    _checked_directory(root)
    previous_preview = home / PREVIOUS_PREVIEW_DIR
    preview = home / TEST_DIR
    if channel == "rc1" and preview.is_dir() and not preview.is_symlink():
        source_dir = preview
    else:
        source_dir = (
            previous_preview
            if previous_preview.is_dir() and not previous_preview.is_symlink()
            else home / LEGACY_DIR
        )
    destination = root / identity["settings_namespace"]
    _checked_directory(destination)
    for filename in MIGRATED_FILENAMES:
        _copy_once_atomic(source_dir / filename, destination / filename)
    return destination / "preferences.json"
