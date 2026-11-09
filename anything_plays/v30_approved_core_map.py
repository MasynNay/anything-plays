"""Offline source-built GPL core map for a FUTURE independently approved 3.0.

An installed marker describes WHICH native core to open and verifies its exact
compiled bytes. It is *not* a legal permission document: only an independently
reviewed immutable production lock, matching corresponding source, legal
decision, and physical QA can authorize bundling/publishing this marker.

Normal v2.0 and unapproved 3.0 preview have no such marker and are unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from anything_plays.v30_gpl_trial import (
    EXPECTED_SOURCE_COMMITS, PCE_SOURCE_COMMIT, PCE_SOURCE_REPO,
    PROFILE_TO_CORE, WINDOWS_RUNTIME, _register_windows_runtime_directory,
    FIVE_ORIGINAL_SOURCE_COMMITS, FIVE_ORIGINAL_SOURCE_REPOSITORIES,
)

MARKER = "V30_SOURCE_BUILT_PRODUCTION_CORE_MAP.json"
STATUS = "SOURCE-REVIEWED-18-PROFILE-11-CORE-ALTERNATIVE-PAYLOAD"
EXPECTED = {
    **EXPECTED_SOURCE_COMMITS,
    "mednafen_pce_fast": PCE_SOURCE_COMMIT,
}
REPOSITORIES = {
    "mednafen_supafaust": "https://github.com/libretro/supafaust",
    "blastem": "https://github.com/libretro/blastem",
    "mednafen_pce_fast": PCE_SOURCE_REPO,
}
EIGHT_EXPECTED = {**EXPECTED, **FIVE_ORIGINAL_SOURCE_COMMITS}
EIGHT_REPOSITORIES = {**REPOSITORIES, **FIVE_ORIGINAL_SOURCE_REPOSITORIES}
# Exact independently pinned original native builds in four-platform research.
# These constants describe identity only; no public redistribution approval.
TEN_EXPECTED = {
    **EIGHT_EXPECTED,
    "mgba": "7a12d6d4b9acb14c0ae62c9166b6a2f3d08007f6",
    "parallel_n64": "e0ef5d673257e2e83bf9b7cffe62eda141af8493",
}
TEN_REPOSITORIES = {
    **EIGHT_REPOSITORIES,
    "mgba": "https://github.com/libretro/mgba",
    "parallel_n64": "https://github.com/libretro/parallel-n64",
}
assert len(TEN_EXPECTED) == len(TEN_REPOSITORIES) == 10
ELEVEN_EXPECTED = {**TEN_EXPECTED, "dolphin": "32c61f9d0e933331bb7087ba57e96883241b4960"}
ELEVEN_REPOSITORIES = {**TEN_REPOSITORIES, "dolphin": "https://github.com/libretro/dolphin"}
assert len(ELEVEN_EXPECTED) == len(ELEVEN_REPOSITORIES) == 11
ADDITIONAL_SYSTEMS = {
    "gb": "mgba", "gbc": "mgba", "gba": "mgba",
    "n64": "parallel_n64",
    "nes":"fceumm", "atari2600":"stella2014",
    "atari7800":"prosystem", "ngp":"mednafen_ngp",
    "ngpc":"mednafen_ngp", "ws":"mednafen_wswan",
    "wsc":"mednafen_wswan",
}
SHA = set("0123456789abcdef")
MAX_LIBRARY = 60 * 1024 * 1024
MAX_MANIFEST = 32768


def _require_hash(value, description):
    if not isinstance(value, str) or len(value) != 64 or any(c not in SHA for c in value):
        raise ValueError(f"Invalid source-built {description}")
    return value


def validate_installed_map(folder, extension, *, verify_native=True):
    root = Path(folder)
    marker = root / MARKER
    if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > MAX_MANIFEST:
        raise ValueError("Missing or unsafe reviewed core mapping")
    info = json.loads(marker.read_text("utf-8"))
    if (not isinstance(info, dict) or info.get("schema_version") != 1
            or info.get("status") != STATUS
            or info.get("core_set_id") not in ("gpl-source-built-alternative", "gpl-source-built-eight", "gpl-source-built-ten", "gpl-source-built-eleven")
            or info.get("all_console_profiles") != 18
            or info.get("native_core_count") != 11
            or info.get("legacy_noncommercial_native_binaries_excluded") is not True):
        raise ValueError("Incorrect source-built production core identity")
    rows = info.get("cores")
    eight = info["core_set_id"] == "gpl-source-built-eight"
    ten = info["core_set_id"] == "gpl-source-built-ten"
    eleven = info["core_set_id"] == "gpl-source-built-eleven"
    expected = ELEVEN_EXPECTED if eleven else TEN_EXPECTED if ten else EIGHT_EXPECTED if eight else EXPECTED
    repositories = ELEVEN_REPOSITORIES if eleven else TEN_REPOSITORIES if ten else EIGHT_REPOSITORIES if eight else REPOSITORIES
    if (not isinstance(rows, dict) or set(rows) != set(expected)
            or (eight and info.get("eight_source_built_families_reviewed") is not True)
            or (eight and info.get("three_unchanged_native_families_reviewed") is not True)
            or (ten and info.get("ten_source_built_families_reviewed") is not True)
            or (ten and info.get("one_unchanged_dolphin_family_reviewed") is not True)
            or (eleven and info.get("eleven_source_built_families_reviewed") is not True)
            or (eleven and info.get("zero_unchanged_native_families_reviewed") is not True)):
        raise ValueError("Reviewed 3.0 original source-built library families incomplete")
    for name, revision in expected.items():
        row = rows[name]
        filename = f"{name}_libretro{extension}"
        if (not isinstance(row, dict) or row.get("native_filename") != filename
                or row.get("source_commit") != revision
                or row.get("source_repository") != repositories[name]):
            raise ValueError(f"Original source-built revision/filename mismatch: {name}")
        _require_hash(row.get("native_sha256"), f"{name} binary digest")
        _require_hash(row.get("license_notice_sha256"), f"{name} original GPL notice")
        if verify_native:
            path = root / filename
            if (path.is_symlink() or not path.is_file()
                    or not 10000 < path.stat().st_size < (512 * 1024 * 1024 if name == "dolphin" else MAX_LIBRARY)
                    or hashlib.sha256(path.read_bytes()).hexdigest() != row["native_sha256"]):
                raise ValueError(f"Missing/tampered approved source-built native image: {name}")
    for forbidden in ("snes9x", "genesis_plus_gx"):
        if (root / f"{forbidden}_libretro{extension}").exists():
            raise ValueError("Original noncommercial library in reviewed alternative installer")
    if extension == ".dll":
        deps = info.get("runtime_dependencies")
        if not isinstance(deps, dict) or set(deps) != {WINDOWS_RUNTIME}:
            raise ValueError("Exact Windows offline MinGW runtime is required")
        _require_hash(deps[WINDOWS_RUNTIME], WINDOWS_RUNTIME)
        path = root / WINDOWS_RUNTIME
        if (path.is_symlink() or not path.is_file()
                or not 10000 < path.stat().st_size < 8 * 1024 * 1024
                or hashlib.sha256(path.read_bytes()).hexdigest() != deps[WINDOWS_RUNTIME]):
            raise ValueError("Windows package contains missing/altered native runtime")
    elif info.get("runtime_dependencies") != {}:
        raise ValueError("Unexpected native runtime dependency on non-Windows platform")
    return info


def enable_windows_offline_runtime(folder, *, verify_native=True):
    """Verify bundled DLL and register once, before or after extracting cores."""
    if os.name != "nt":
        return
    root = Path(folder)
    from anything_plays.v30_gpl_trial import _verify_runtime_dependency
    info = validate_installed_map(root, ".dll", verify_native=verify_native)
    _verify_runtime_dependency(root, info, ".dll")
    _register_windows_runtime_directory(root, info)


def find_approved_core(directories, system, extension):
    """(found, path). A detected but invalid marker must NEVER fall back."""
    if system not in PROFILE_TO_CORE and system != "pce" and system not in ADDITIONAL_SYSTEMS:
        return False, None
    for folder in directories:
        root = Path(folder)
        marker = root / MARKER
        if marker.is_symlink():
            raise ValueError("Symlinked approved source-built core map")
        if not marker.exists():
            continue
        info = validate_installed_map(root, extension)
        name = ("mednafen_pce_fast" if system == "pce" else
                PROFILE_TO_CORE[system] if system in PROFILE_TO_CORE
                else ADDITIONAL_SYSTEMS[system])
        if name not in info["cores"]:
            # Three-source legacy reviewed package does NOT claim new
            # five-family original-source provenance, so ordinary NES/Atari/
            # NGP/WS lookup remains the previous unchanged path.
            continue
        enable_windows_offline_runtime(root)
        return True, str(root / info["cores"][name]["native_filename"])
    return False, None
