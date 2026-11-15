"""Privacy-safe, complete 18-console controls backup for Anything Plays 3.2.

Only portable per-console zones, mappings, colors and detection settings are
exported. No ROMs, paths, camera frames, saves, controller identities or
preferences. Restores are parsed/validated completely before a UI confirmation.
"""
from __future__ import annotations

import json
from pathlib import Path

from anything_plays.atomic_storage import write_json_atomically
from anything_plays.portable_profiles import (
    _reject_duplicate_keys, make_bundle, sanitize_profile,
)
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM

FORMAT = "anything-plays-all-console-controls"
VERSION = 1
MAX_ARCHIVE_BYTES = 1024 * 1024
SYSTEM_NAMES = frozenset(BUTTONS_BY_SYSTEM)


def make_library_archive(profiles):
    """Create a complete, strict, sanitized backup without mutating inputs."""
    if not isinstance(profiles, dict) or set(profiles) != SYSTEM_NAMES:
        raise ValueError("A complete all-console backup is required.")
    clean = {
        key: make_bundle(key, profiles[key])["profile"]
        for key in BUTTONS_BY_SYSTEM
    }
    bundle = {
        "format": FORMAT, "version": VERSION,
        "system_count": len(SYSTEM_NAMES), "profiles": clean,
    }
    if len(json.dumps(bundle, ensure_ascii=True).encode("utf-8")) > MAX_ARCHIVE_BYTES:
        raise ValueError("Control backup is larger than 1 MiB.")
    return bundle


def parse_library_archive(data):
    """Validate exact console coverage and reject unknown/private metadata."""
    if isinstance(data, bytes):
        if len(data) > MAX_ARCHIVE_BYTES:
            raise ValueError("Control backup is larger than 1 MiB.")
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Control backup must be UTF-8.") from exc
    if not isinstance(data, str):
        raise ValueError("Control backup must contain JSON text.")
    if len(data.encode("utf-8")) > MAX_ARCHIVE_BYTES:
        raise ValueError("Control backup is larger than 1 MiB.")
    try:
        doc = json.loads(
            data, object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("Non-finite control backup value.")
            ),
        )
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError("Invalid all-console backup JSON.") from exc
    if not isinstance(doc, dict) or set(doc) != {
        "format", "version", "system_count", "profiles",
    }:
        raise ValueError("Unrecognized all-console backup structure.")
    if (doc["format"] != FORMAT or type(doc["version"]) is not int
            or doc["version"] != VERSION
            or type(doc["system_count"]) is not int
            or doc["system_count"] != len(SYSTEM_NAMES)):
        raise ValueError("Unsupported all-console backup format or version.")
    profiles = doc["profiles"]
    if not isinstance(profiles, dict) or set(profiles) != SYSTEM_NAMES:
        raise ValueError("Backup must contain every supported console exactly once.")
    return {
        key: sanitize_profile(key, profiles[key])
        for key in BUTTONS_BY_SYSTEM
    }


def load_library_archive(path):
    with Path(path).open("rb") as stream:
        data = stream.read(MAX_ARCHIVE_BYTES + 1)
    return parse_library_archive(data)


def save_library_archive(path, profiles):
    backup = make_library_archive(profiles)
    write_json_atomically(path, backup)
