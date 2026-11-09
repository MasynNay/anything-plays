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
PCE_SOURCE_COMMIT = "2de1ce1c3f237b161c126c54ba407990bb86d1e9"
PCE_SOURCE_REPO = "https://github.com/libretro/beetle-pce-fast-libretro"
FIVE_ORIGINAL_SOURCE_COMMITS = {
    "fceumm": "e0f3086a8104f8fbbe49a2615b10401504a9533f",
    "stella2014": "7d1361e407e63f29e52892655069e5fb4096e691",
    "prosystem": "8a88014287c7a01cd568067e5a557d0a2b2a051f",
    "mednafen_ngp": "a50d5ac288a81f2104ddf43195a4efdd15c72227",
    "mednafen_wswan": "4b01295838ea89e3f1355bbe4cb5cf98aa6108cd",
}
FIVE_ORIGINAL_SOURCE_REPOSITORIES = {
    "fceumm": "https://github.com/libretro/libretro-fceumm",
    "stella2014": "https://github.com/libretro/stella2014-libretro",
    "prosystem": "https://github.com/libretro/prosystem-libretro",
    "mednafen_ngp": "https://github.com/libretro/beetle-ngp-libretro",
    "mednafen_wswan": "https://github.com/libretro/beetle-wswan-libretro",
}
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
    # Optional forward-only pinned PC Engine source-built research variant:
    # the ORIGINAL nightly PCE had no reported source revision; never
    # mislabel its native bytes as coming from the new exact source checkout.
    pce = info.get("source_built_pce")
    if pce is not None:
        if (not isinstance(pce, dict)
                or pce.get("source_repository") != PCE_SOURCE_REPO
                or pce.get("source_commit") != PCE_SOURCE_COMMIT
                or pce.get("native_filename") != f"mednafen_pce_fast_libretro{extension}"
                or pce.get("old_unknown_source_nightly_substituted") is not True
                or type(pce.get("original_source_build_run_id")) is not int
                or pce["original_source_build_run_id"] != 42444367068):
            raise ValueError("Unrecognized PCE pinned-source replacement record")
        for field in ("native_sha256", "source_archive_sha256", "native_archive_sha256", "notice_sha256"):
            digest = pce.get(field)
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError(f"Invalid PCE exact source/native {field}")
        if verify_native:
            native = root / pce["native_filename"]
            if native.is_symlink() or not native.is_file() or native.stat().st_size > 60 * 1024 * 1024:
                raise ValueError("Missing source-built PC Engine native core")
            if hashlib.sha256(native.read_bytes()).hexdigest() != pce["native_sha256"]:
                raise ValueError("Source-built PC Engine native hash mismatch")
    # Source-built 8/11 integrated complete offline variant. These are
    # NEW original source builds, never relabeled historical native-nightlies.
    remaining = info.get("source_built_remaining_five")
    if remaining is not None:
        if (not isinstance(remaining, dict)
                or set(remaining) != set(FIVE_ORIGINAL_SOURCE_COMMITS)
                or info.get("total_source_built_core_families") != (
                    11 if info.get("source_built_dolphin") is not None else
                    10 if info.get("source_built_n64") is not None else
                    9 if info.get("source_built_mgba") is not None else 8)
                or info.get("original_unchanged_core_archives") != (
                    0 if info.get("source_built_dolphin") is not None else
                    1 if info.get("source_built_n64") is not None else
                    2 if info.get("source_built_mgba") is not None else 3)
                or info.get("five_source_family_run_id") != 42515151314
                or pce is None):
            raise ValueError("Eight source-built families are not complete and exact")
        for name, revision in FIVE_ORIGINAL_SOURCE_COMMITS.items():
            row=remaining[name]
            if (not isinstance(row, dict)
                    or row.get("source_repository") != FIVE_ORIGINAL_SOURCE_REPOSITORIES[name]
                    or row.get("source_commit") != revision
                    or row.get("native_filename") != f"{name}_libretro{extension}"
                    or row.get("source_build_run_id") != 42515151314
                    or row.get("old_unknown_source_buildbot_replaced") is not True
                    or row.get("original_license_notice_copied") is not True):
                raise ValueError(f"Wrong original source-built core family: {name}")
            for field in ("native_sha256","source_archive_sha256",
                          "native_archive_sha256"):
                value=row.get(field)
                if (not isinstance(value,str) or len(value)!=64
                        or any(c not in "0123456789abcdef" for c in value)):
                    raise ValueError(f"Missing real compiled core/source fingerprint: {name}/{field}")
            notice=row.get("original_license_notice_sha256")
            if (not isinstance(notice,str) or len(notice)!=64
                  or any(c not in "0123456789abcdef" for c in notice)):
                raise ValueError(f"Missing original GPL source notice: {name}")
            if verify_native:
                native=root/row["native_filename"]
                if (native.is_symlink() or not native.is_file()
                        or not 10000<native.stat().st_size<60*1024*1024
                        or hashlib.sha256(native.read_bytes()).hexdigest()!=row["native_sha256"]):
                    raise ValueError(f"Modified source-built 3.0 original core: {name}")
    # Optional ninth, separately compiled MPL2 mGBA candidate. Never treat
    # its old unverified buildbot native as an independently sourced binary.
    mgba = info.get("source_built_mgba")
    if mgba is not None:
        SOURCE_REVISION = "7a12d6d4b9acb14c0ae62c9166b6a2f3d08007f6"
        SOURCE_REPOSITORY = "https://github.com/libretro/mgba"
        if (remaining is None or pce is None or not isinstance(mgba, dict)
                or mgba.get("source_repository") != SOURCE_REPOSITORY
                or mgba.get("source_commit") != SOURCE_REVISION
                or mgba.get("native_filename") != f"mgba_libretro{extension}"
                or mgba.get("source_build_run_id") != 42527449154
                or mgba.get("old_unverified_source_buildbot_replaced") is not True
                or mgba.get("original_mpl_notice_copied") is not True
                or not isinstance(mgba.get("original_native_av_report_sha256"), dict)
                or set(mgba["original_native_av_report_sha256"])
                != {f"ORIGINAL_{system}_NATIVE_AV.json" for system in ("GB", "GBC", "GBA")}):
            raise ValueError("Unverified ninth original source-built MPL2 mGBA candidate")
        for key in ("native_sha256", "source_archive_sha256",
                    "native_archive_sha256", "original_license_notice_sha256"):
            value = mgba.get(key)
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"Missing ninth original source-native fingerprint: {key}")
        for value in mgba["original_native_av_report_sha256"].values():
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("Missing original GB/GBC/GBA A/V report fingerprints")
        if verify_native:
            native = root / mgba["native_filename"]
            if (native.is_symlink() or not native.is_file()
                    or not 50000 < native.stat().st_size < 70 * 1024 * 1024
                    or hashlib.sha256(native.read_bytes()).hexdigest() != mgba["native_sha256"]):
                raise ValueError("Installed ninth original source-built mGBA binary is not authentic")
    # The tenth source-built core is genuine upstream ParaLLEl-N64, not
    # the earlier buildbot library with an assumed source revision.
    n64 = info.get("source_built_n64")
    if n64 is not None:
        if (remaining is None or pce is None or mgba is None or not isinstance(n64, dict)
                or n64.get("source_repository") != "https://github.com/libretro/parallel-n64"
                or n64.get("source_commit") != "e0ef5d673257e2e83bf9b7cffe62eda141af8493"
                or n64.get("native_filename") != f"parallel_n64_libretro{extension}"
                or n64.get("source_build_run_id") != 42534736496
                or n64.get("old_unverified_buildbot_replaced") is not True):
            raise ValueError("Unverified tenth source-built ParaLLEl-N64 original")
        for key in ("native_sha256","original_source_sha256",
                    "original_native_av_sha256","native_archive_sha256"):
            value = n64.get(key)
            if not isinstance(value,str) or len(value)!=64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"Missing exact original source-built N64 fingerprint: {key}")
        notices = n64.get("original_notice_sha256")
        names = {f"GPL-TRIAL-N64-NOTICE-{i:02}.txt" for i in range(1,12)}
        if (not isinstance(notices,dict) or set(notices)!=names
                or not isinstance(n64.get("original_notice_sources"),dict)
                or set(n64["original_notice_sources"])!=names
                or len(set(n64["original_notice_sources"].values()))!=11):
            raise ValueError("Incomplete eleven original N64 GPL/LGPL/MIT notices")
        for name,value in notices.items():
            if not isinstance(value,str) or len(value)!=64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"Missing original N64 license blob: {name}")
        if verify_native:
            native=root/n64["native_filename"]
            if (native.is_symlink() or not native.is_file()
                    or not 100000<native.stat().st_size<120*1024*1024
                    or hashlib.sha256(native.read_bytes()).hexdigest()!=n64["native_sha256"]):
                raise ValueError("Modified tenth original source-built N64 core")
    # Eleventh source-built native: the NEW pristine original Dolphin,
    # never a historical buildbot DLL renamed to claim matching source.
    dolphin = info.get("source_built_dolphin")
    if dolphin is not None:
        notice_paths = {
            "GPL-TRIAL-DOLPHIN-ORIGINAL-COPYING.txt": "COPYING",
            "GPL-TRIAL-DOLPHIN-ORIGINAL-GPL2-OR-LATER.txt": "LICENSES/GPL-2.0-or-later.txt",
            "GPL-TRIAL-DOLPHIN-ORIGINAL-BSD3.txt": "LICENSES/BSD-3-Clause.txt",
            "GPL-TRIAL-DOLPHIN-ORIGINAL-CC0.txt": "LICENSES/CC0-1.0.txt",
            "GPL-TRIAL-DOLPHIN-ORIGINAL-MIT.txt": "LICENSES/MIT.txt",
        }
        if (n64 is None or remaining is None or mgba is None or pce is None
                or not isinstance(dolphin, dict)
                or dolphin.get("source_repository") != "https://github.com/libretro/dolphin"
                or dolphin.get("source_commit") != "32c61f9d0e933331bb7087ba57e96883241b4960"
                or dolphin.get("native_filename") != f"dolphin_libretro{extension}"
                or dolphin.get("direct_original_gitlinks") != 34
                or dolphin.get("nested_original_gitlinks") != 3
                or dolphin.get("old_unverified_buildbot_replaced") is not True
                or dolphin.get("pristine_unmodified_original_source_compiled") is not True
                or dolphin.get("production_hardware_gameplay_reviewed") is not False
                or dolphin.get("full_corresponding_source_and_transitive_rights_reviewed") is not False
                or dolphin.get("public_binary_distribution_approved") is not False):
            raise ValueError("Missing genuine eleventh original source-built Dolphin native")
        if (type(dolphin.get("native_size_bytes")) is not int
                or not 200000 < dolphin["native_size_bytes"] < 512 * 1024 * 1024):
            raise ValueError("Invalid original Dolphin native length")
        for key in ("native_sha256", "native_archive_sha256"):
            value = dolphin.get(key)
            if (not isinstance(value, str) or len(value) != 64
                    or any(k not in "0123456789abcdef" for k in value)):
                raise ValueError(f"Missing source-native Dolphin {key}")
        notices = dolphin.get("original_source_notices")
        if not isinstance(notices, dict) or set(notices) != set(notice_paths):
            raise ValueError("Missing original upstream Dolphin GPL/MIT/BSD/CC0 notices")
        for name, path in notice_paths.items():
            notice = notices[name]
            if (not isinstance(notice, dict) or notice.get("source_path") != path
                    or not isinstance(notice.get("sha256"), str)
                    or len(notice["sha256"]) != 64
                    or any(k not in "0123456789abcdef" for k in notice["sha256"])):
                raise ValueError(f"Forged original Dolphin source license record: {name}")
        sys_origin = info.get("source_exact_original_dolphin_sys")
        if (not isinstance(sys_origin, dict)
                or sys_origin.get("public_distribution_approved") is not False):
            raise ValueError("The eleventh source-built Dolphin requires the exact source-pinned Sys files")
        if verify_native:
            native = root / dolphin["native_filename"]
            if (native.is_symlink() or not native.is_file()
                    or native.stat().st_size != dolphin["native_size_bytes"]
                    or hashlib.sha256(native.read_bytes()).hexdigest() != dolphin["native_sha256"]):
                raise ValueError("Installed newly source-built Dolphin native differs from reviewed SHA")
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
