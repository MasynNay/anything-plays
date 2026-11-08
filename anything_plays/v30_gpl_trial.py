"""Explicit, checksum-verified research-only offline GPL alternative core mapping.

No persistent configuration or environment switch is needed for an installed
trial bundle. The presence of a complete validated test-only manifest in the
SAME core directory is the sole opt-in. Missing/tampered alternate images
fail closed, never silently falling back to noncommercial originals.
This is technical research, NOT redistribution approval or license clearance.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

MARKER = "V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json"
STATUS = "UNAPPROVED-18-PROFILE-11-CORE-GPL-ALTERNATIVE-OFFLINE-TRIAL"
PROFILE_TO_CORE = {
    "snes": "mednafen_supafaust",
    "genesis": "blastem",
    "mastersystem": "blastem",
    "gamegear": "blastem",
    "sg1000": "blastem",
}
EXPECTED_SOURCE_COMMITS = {
    "mednafen_supafaust": "642d1d1b6684aa7e306a02a89885f3f5456a5157",
    "blastem": "2230addc4dd74dd094fd264987fd808abba32d0e",
}
ALTERNATIVE_PROFILES = 5
ALTERNATIVE_CORES = 2
EXPECTED_PROFILES = 18
EXPECTED_CORES = 11
WINDOWS_RUNTIME = "libwinpthread-1.dll"
# Keep os.add_dll_directory handles alive for the loaded native cores.
# A list would add a new OS DLL-search directory handle on EVERY console
# switch, leaking one native handle per ROM opened for the lifetime of the UI.
# One verified canonical directory gets exactly one retained handle.
_WINDOWS_NATIVE_DLL_HANDLES = {}


def _verify_runtime_dependency(root, info, extension):
    deps = info.get("runtime_dependencies")
    if extension != ".dll":
        if deps != {}:
            raise ValueError("Unexpected Windows runtime in non-Windows trial")
        return
    if not isinstance(deps, dict) or set(deps) != {WINDOWS_RUNTIME}:
        raise ValueError("Windows GPL trial is missing its offline native runtime")
    digest = deps[WINDOWS_RUNTIME]
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Unverified Windows runtime dependency SHA")
    runtime = Path(root) / WINDOWS_RUNTIME
    if runtime.is_symlink() or not runtime.is_file() or not 10000 < runtime.stat().st_size < 8 * 1024 * 1024:
        raise ValueError("Missing unsafe Windows native dependency")
    if hashlib.sha256(runtime.read_bytes()).hexdigest() != digest:
        raise ValueError("Windows native runtime dependency was modified")


def enable_windows_trial_runtime(folder):
    """Register only the exact SHA-verified core directory on Windows.

    Python 3.8+ does not use normal PATH for ctypes dependency resolution.
    The packaged MinGW libwinpthread runtime MUST be present, without
    dependence on any globally installed MSYS2/RetroArch program.
    """
    if os.name != "nt":
        return
    root = Path(folder)
    marker = root / MARKER
    if (marker.is_symlink() or not marker.is_file()
            or marker.stat().st_size > 32768):
        raise ValueError("Missing/unsafe Windows original source-built trial marker")
    info = json.loads(marker.read_text("utf-8"))
    _register_windows_runtime_directory(root, info)


def _register_windows_runtime_directory(root, info):
    """Verify native dependency EVERY call, but register its directory ONCE.

    This helper is deliberately independent of os.name so the handle-lifetime
    contract can be tested on Linux/macOS without loading any Windows DLLs.
    """
    root = Path(root)
    _verify_runtime_dependency(root, info, ".dll")
    canonical = str(root.resolve(strict=True))
    if canonical not in _WINDOWS_NATIVE_DLL_HANDLES:
        # Registration takes place only after the runtime's native bytes have
        # passed the original source-built manifest's exact SHA-256 check.
        _WINDOWS_NATIVE_DLL_HANDLES[canonical] = os.add_dll_directory(canonical)


def validate_trial_core_directory(folder, extension, *, verify_native=True):
    """Validate exact alternate identities in the installed bundle.

    No runtime mutation and no network. The original release does not have
    this marker and continues to behave exactly as before.
    """
    root = Path(folder)
    marker = root / MARKER
    if not marker.is_file() or marker.is_symlink() or marker.stat().st_size > 32768:
        raise ValueError("Missing/unsafe complete GPL-alternative research marker")
    info = json.loads(marker.read_text("utf-8"))
    if (not isinstance(info, dict) or info.get("status") != STATUS
            or info.get("schema_version") != 1
            or info.get("all_console_profiles") != EXPECTED_PROFILES
            or info.get("native_core_count") != EXPECTED_CORES
            or info.get("public_binary_distribution_approved") is not False
            or info.get("combined_gpl_license_reviewed") is not False
            or info.get("physical_qa_approved") is not False
            or info.get("production_core_substitution_approved") is not False):
        raise ValueError("Invalid or falsely approved GPL-alternative marker")
    entries = info.get("alternatives")
    if not isinstance(entries, dict) or set(entries) != set(EXPECTED_SOURCE_COMMITS):
        raise ValueError("Missing/extra GPL alternative core identities")
    for name, revision in EXPECTED_SOURCE_COMMITS.items():
        row = entries[name]
        if not isinstance(row, dict) or row.get("source_commit") != revision:
            raise ValueError(f"Unexpected pinned source for {name}")
        if row.get("source_repository") != {
            "mednafen_supafaust": "https://github.com/libretro/supafaust",
            "blastem": "https://github.com/libretro/blastem",
        }[name]:
            raise ValueError(f"Unexpected source repository for {name}")
        digest = row.get("native_sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"Missing real native source SHA for {name}")
        if row.get("native_filename") != f"{name}_libretro{extension}":
            raise ValueError(f"Wrong native file platform/identity for {name}")
        if verify_native:
            native = root / row["native_filename"]
            if native.is_symlink() or not native.is_file() or native.stat().st_size > 60 * 1024 * 1024:
                raise ValueError(f"Missing unsafe GPL alternative core: {name}")
            sha = hashlib.sha256(native.read_bytes()).hexdigest()
            if sha != digest:
                raise ValueError(f"Tampered GPL alternative native binary: {name}")
    _verify_runtime_dependency(root, info, extension)
    # The research installer must NOT distribute the two replaced noncommercial cores.
    for forbidden in ("snes9x", "genesis_plus_gx"):
        if (root / f"{forbidden}_libretro{extension}").exists():
            raise ValueError("Unapproved noncommercial core remains in GPL trial")
    return info


def find_trial_core(directories, system, extension):
    """Return (detected_trial_marker, native_path); wrong/missing native is fatal.

    A marker in the first legitimate bundled core folder takes priority over
    optional developer/user-managed packs for only the five test profiles.
    Normal releases without the marker do not enter this pathway.
    """
    if system not in PROFILE_TO_CORE:
        return False, None
    for folder in directories:
        root = Path(folder)
        marker = root / MARKER
        if marker.is_symlink():
            raise ValueError("Symlinked GPL trial manifest")
        if marker.exists():
            info = validate_trial_core_directory(root, extension)
            enable_windows_trial_runtime(root)
            name = PROFILE_TO_CORE[system]
            return True, str(root / info["alternatives"][name]["native_filename"])
    return False, None
