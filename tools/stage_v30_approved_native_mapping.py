"""Stage future approved (not trial) 3.0 source-built core map and DLL.

Requires an independently approved immutable 44-native source+rights lock.
Cannot turn research flags into an approval, cannot fetch dependencies and
does not create production assets while the tracked lock remains unapproved.
The verified alternate actual emulator inputs are staged separately by CI.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from anything_plays.v30_approved_core_map import (
    EXPECTED, REPOSITORIES, EIGHT_EXPECTED, EIGHT_REPOSITORIES,
    MARKER, STATUS, WINDOWS_RUNTIME, _require_hash, validate_installed_map,
)
from tools.v30_release_lock import (
    ALTERNATIVE_CORE_NAMES, selected_core_set, selected_source_families,
    SOURCE_BUILT_EIGHT, TARGETS, load_approved_lock,
)

EXT = {
    "windows-x86_64": ".dll",
    "linux-x86_64": ".so",
    "macos-arm64": ".dylib",
    "macos-x86_64": ".dylib",
}


def approved_core_map_from_lock(lock, target):
    """Strict pure production metadata builder, called only AFTER approval."""
    if target not in TARGETS or selected_core_set(lock) != ALTERNATIVE_CORE_NAMES:
        raise ValueError("Only the EXACT reviewed GPL-alternative 11-core build is accepted")
    for flag in ("approved_for_binary_distribution", "license_compatibility_reviewed",
                 "corresponding_source_inventory_verified",
                 "legacy_noncommercial_native_binaries_excluded",
                 "source_built_alternative_binary_rights_reviewed"):
        if lock.get(flag) is not True:
            raise ValueError(f"Missing genuine reviewed production approval: {flag}")
    row = lock["targets"][target]
    if row.get("approved_for_distribution") is not True:
        raise ValueError("Platform's core distribution is not reviewed")
    cores = row.get("cores")
    if not isinstance(cores, dict) or set(cores) != ALTERNATIVE_CORE_NAMES:
        raise ValueError("Source-reviewed production core inventory does not have 11 names")
    eight = selected_source_families(lock) == SOURCE_BUILT_EIGHT
    expected = EIGHT_EXPECTED if eight else EXPECTED
    repositories = EIGHT_REPOSITORIES if eight else REPOSITORIES
    result = {
        "schema_version": 1, "status": STATUS,
        "core_set_id": lock.get("core_set_id"),
        "all_console_profiles": 18, "native_core_count": 11,
        "legacy_noncommercial_native_binaries_excluded": True,
        "cores": {}, "runtime_dependencies": {},
    }
    if eight:
        result["eight_source_built_families_reviewed"] = True
        result["three_unchanged_native_families_reviewed"] = True
    ext = EXT[target]
    for name, source in expected.items():
        core = cores[name]
        if (core.get("source_commit_sha") != source
                or core.get("upstream_source_repository") != repositories[name]
                or core.get("file") != f"{name}_libretro{ext}"
                or core.get("corresponding_source_verified") is not True
                or core.get("redistribution_approved") is not True):
            raise ValueError(f"Core is NOT the actual source-reviewed {name} binary")
        _require_hash(core.get("native_sha256"), name)
        _require_hash(core.get("original_license_notice_sha256"), f"{name} original notice")
        result["cores"][name] = {
            "native_filename": core["file"],
            "native_sha256": core["native_sha256"],
            "source_commit": source,
            "source_repository": repositories[name],
            "license_notice_sha256": core["original_license_notice_sha256"],
        }
    if target == "windows-x86_64":
        if row.get("runtime_dependency_source_reviewed") is not True:
            raise ValueError("Windows source-built MinGW dependency source and license not reviewed")
        dep = row.get("runtime_dependencies")
        if not isinstance(dep, dict) or set(dep) != {WINDOWS_RUNTIME}:
            raise ValueError("Windows exact native source dependency not listed")
        result["runtime_dependencies"][WINDOWS_RUNTIME] = _require_hash(
            dep[WINDOWS_RUNTIME], WINDOWS_RUNTIME)
    elif row.get("runtime_dependencies") not in (None, {}):
        raise ValueError("Unexpected Windows runtime in non-Windows production lock")
    return result


def stage_approved_map(lock, target, core_dir, archive_dir):
    """Copy nothing until the exact approved review+input validation passes."""
    info = approved_core_map_from_lock(lock, target)
    folder = Path(core_dir)
    archived = Path(archive_dir)
    if folder.is_symlink() or not folder.is_dir() or archived.is_symlink() or not archived.is_dir():
        raise ValueError("Missing or unsafe reviewed production core/archive directories")
    mapping = folder / MARKER
    if mapping.exists() or mapping.is_symlink():
        raise ValueError("Production source-built core marker must not preexist")
    runtime_payload = None
    if target == "windows-x86_64":
        path = archived / WINDOWS_RUNTIME
        if (path.is_symlink() or not path.is_file()
                or not 10000 < path.stat().st_size < 8 * 1024 * 1024):
            raise ValueError("Missing source-reviewed Windows native runtime input")
        runtime_payload = path.read_bytes()
        if hashlib.sha256(runtime_payload).hexdigest() != info["runtime_dependencies"][WINDOWS_RUNTIME]:
            raise ValueError("Windows source-built runtime differs from the REVIEWED immutable lock")
    for name in info["cores"]:
        original = folder / f"{name}_libretro{EXT[target]}"
        if original.exists() or original.is_symlink():
            raise ValueError("Approved core map must be staged BEFORE extracting replacement cores")
    if any((folder / f"{name}_libretro{EXT[target]}").exists()
           for name in ("snes9x", "genesis_plus_gx")):
        raise ValueError("Original noncommercial core still present in production core directory")
    mapping.write_text(json.dumps(info, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if runtime_payload is not None:
        (folder / WINDOWS_RUNTIME).write_bytes(runtime_payload)
    # Full native verify is performed *after* extracting and SHA-locking cores.
    # Here the exact original reviewed runtime is still validated.
    validate_installed_map(folder, EXT[target], verify_native=False)
    return info


def stage_from_approved_lock(core_dir, archive_dir, target):
    """Entrypoint never succeeds with current unapproved repository lock."""
    return stage_approved_map(load_approved_lock(), target, core_dir, archive_dir)
