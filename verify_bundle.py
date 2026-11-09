"""Verify staged Anything Plays bundles before creating platform installers.

This checks file presence and binary integrity. It does NOT establish that
third-party redistribution and corresponding-source obligations are satisfied.
"""

import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import sys

from fetch_mgba_core import inspect_core_identity, core_names_for_build


CORE_NAMES = ("mgba", "snes9x")
OPTIONAL_V21_LICENSES = (
    "FCEUmm-GPL-2.0.txt", "Genesis-Plus-GX-LICENSE.txt",
    "Dolphin-GPL-2.0-or-later.txt",
)
REQUIRED_DOCUMENTS = (
    "AnythingPlays-MIT.txt",
    "CODE_OF_CONDUCT.md",
    "THIRD_PARTY_NOTICES.md",
    "THIRD_PARTY_COMPONENTS.md",
    "mGBA-MPL-2.0.txt",
    "Snes9x-LICENSE.txt",
    "Snes9x-snes_ntsc-LGPL-2.1.txt",
)
EXTENSIONS = {"macos": ".dylib", "windows": ".dll", "linux": ".so"}
# Reviewed v2.1 icon. This SHA belongs to its corrected 512px artwork,
# not the stable 2.0 PNG or ICO, which are deliberately not replaced.
V21_ICON_SHA256 = "a2ef1f7415ea9806c0bff5cec5b5b3d1ad0d1b0ca3a87b0cbf0a5b331bbeb380"

# Distribution policy: Anything Plays never ships game images or BIOS ROMs.
# This catches recognizable console/cart and firmware image filenames;
# as with any extension-based check, manual artifact inspection remains needed.
DISALLOWED_GAME_EXTENSIONS = frozenset({
    ".gb", ".gbc", ".gba", ".sfc", ".smc",
    ".nes", ".unf", ".unif", ".n64", ".z64", ".v64", ".rom", ".bios",
    ".smd", ".gen", ".gcm", ".rvz", ".gcz", ".ciso", ".iso",
    ".dol", ".elf", ".tgc", ".wia", ".m3u",
})


def verify_v21_artwork(bundle):
    """Require the reviewed icon inside every test installer, unchanged."""
    files = [
        path for path in Path(bundle).rglob("anything_plays_v21.webp")
        if path.is_file()
    ]
    if not files:
        raise ValueError("Missing corrected 2.1 fish icon from app bundle")
    if not any(
        hashlib.sha256(path.read_bytes()).hexdigest() == V21_ICON_SHA256
        for path in files
    ):
        raise ValueError("Corrected 2.1 fish icon has a checksum mismatch")


def verify_dolphin_sys(cores, main_manifest):
    """Validate every bundled Dolphin Sys file against the build inventory.

    This catches missing/corrupted compatibility data in the actual installer,
    including inside macOS DMGs and unpacked Windows/Linux distributions.
    """
    from tools.fetch_dolphin_sys import (
        MANIFEST_NAME, MAX_FILES, MAX_EXTRACTED_BYTES, SYSTEM_ASSET_URL,
    )

    path = cores / MANIFEST_NAME
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("Dolphin Sys provenance manifest is missing or oversized")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest != main_manifest.get("dolphin_system_assets"):
        raise ValueError("Dolphin Sys provenance does not match the core manifest")
    if manifest.get("source_url") != SYSTEM_ASSET_URL:
        raise ValueError("Unexpected Dolphin Sys archive source")
    records = manifest.get("files")
    if not isinstance(records, dict) or not (5 <= len(records) <= MAX_FILES):
        raise ValueError("Incomplete Dolphin Sys file inventory")

    root = cores / "dolphin-emu" / "Sys"
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Bundled Dolphin Sys directory is missing or symlinked")
    if "codehandler.bin" not in records:
        raise ValueError("Dolphin core requires codehandler.bin")

    expected_paths = set()
    cumulative = 0
    for relative, identity in records.items():
        components = Path(relative)
        if (not relative or components.is_absolute() or
                any(part in ("..", ".") for part in relative.split("/"))):
            raise ValueError("Unsafe Dolphin Sys file name")
        if not isinstance(identity, dict):
            raise ValueError("Malformed Dolphin Sys file inventory")
        expected_file = root / components
        if expected_file.is_symlink() or not expected_file.is_file():
            raise ValueError(f"Missing Dolphin Sys file: {relative}")
        length = identity.get("size_bytes")
        if not isinstance(length, int) or length < 0:
            raise ValueError(f"Invalid Dolphin Sys length: {relative}")
        cumulative += length
        if cumulative > MAX_EXTRACTED_BYTES:
            raise ValueError("Dolphin Sys exceeds memory safety budget")
        if expected_file.stat().st_size != length:
            raise ValueError(f"Dolphin Sys size mismatch: {relative}")
        digest = hashlib.sha256(expected_file.read_bytes()).hexdigest()
        if digest != identity.get("sha256"):
            raise ValueError(f"Dolphin Sys checksum mismatch: {relative}")
        expected_paths.add(expected_file.relative_to(root).as_posix())

    observed = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*") if path.is_file()
    }
    if expected_paths != observed:
        raise ValueError("Dolphin Sys files differ from the reviewed manifest")


def verify_no_bundled_game_files(bundle):
    """Reject recognized game cartridges and BIOS images in staged packages."""
    for file in Path(bundle).rglob("*"):
        if file.is_file() and file.suffix.casefold() in DISALLOWED_GAME_EXTENSIONS:
            relative = file.relative_to(bundle).as_posix()
            raise ValueError(f"Game ROM or BIOS file must not ship: {relative}")



class _LibretroCoreInfo(C.Structure):
    """Fields defined by libretro's retro_system_info ABI."""

    _fields_ = [
        ("library_name", C.c_char_p),
        ("library_version", C.c_char_p),
        ("valid_extensions", C.c_char_p),
        ("need_fullpath", C.c_bool),
        ("block_extract", C.c_bool),
    ]


def _validate_mgba_core(path):
    """Confirm the actual platform binary supports each advertised Game Boy system."""
    library = C.CDLL(str(path))
    describe = library.retro_get_system_info
    describe.argtypes = [C.POINTER(_LibretroCoreInfo)]
    describe.restype = None
    info = _LibretroCoreInfo()
    describe(C.byref(info))
    reported = (info.valid_extensions or b"").decode("utf-8", "replace")
    extensions = {item.strip(". ").lower() for item in reported.replace(";", "|").split("|")}
    if not {"gb", "gbc", "gba"} <= extensions:
        raise ValueError(f"mGBA binary lacks required GB/GBC/GBA support: {reported}")


def verify_bundle(bundle, platform_name, check_native=False):
    """Raise ValueError on missing documentation or mismatched core binaries."""
    bundle = Path(bundle)
    if platform_name not in EXTENSIONS:
        raise ValueError(f"Unsupported platform: {platform_name}")
    verify_no_bundled_game_files(bundle)
    if platform_name == "macos":
        licenses = bundle / "Contents" / "Resources" / "licenses"
        cores = bundle / "Contents" / "Resources" / "cores"
    else:
        licenses = bundle / "licenses"
        cores = bundle / "cores"

    expected_cores = core_names_for_build()
    if os.environ.get("AP_V30_APPROVED_RELEASE") == "1":
        # The production binary's installed paths MUST match the 44-asset
        # independently reviewed native lock, not the original Snes9x /
        # Genesis Plus GX paths or any test-only research marker.
        from tools.v30_release_lock import (
            ALTERNATIVE_CORE_NAMES, load_approved_lock, selected_core_set,
        )
        from tools.core_release_lock import release_target
        approved_lock = load_approved_lock()
        if selected_core_set(approved_lock) == ALTERNATIVE_CORE_NAMES:
            from anything_plays.v30_approved_core_map import (
                MARKER as PRODUCTION_MAP, validate_installed_map,
            )
            if (cores / "V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json").exists():
                raise ValueError("Production installer contains unapproved research marker")
            selected = validate_installed_map(cores, EXTENSIONS[platform_name])
            records = approved_lock["targets"][
                release_target(sys.platform, __import__("platform").machine())]["cores"]
            notices = {
                "mednafen_supafaust": "Supafaust-COPYING.txt",
                "blastem": "BlastEm-COPYING.txt",
                "mednafen_pce_fast": "PCE-COPYING.txt",
            }
            if selected["core_set_id"] in ("gpl-source-built-eight", "gpl-source-built-ten", "gpl-source-built-eleven"):
                # A native same-name buildbot ZIP is NOT the verified
                # original source-built NES/Atari/NGP/WonderSwan binary.
                for name in ("fceumm","stella2014","prosystem",
                             "mednafen_ngp","mednafen_wswan"):
                    notices[name] = f"GPL-TRIAL-{name}-ORIGINAL-COPYING.txt"
            for name, filename in notices.items():
                row = selected["cores"][name]
                if row["native_sha256"] != records[name]["native_sha256"]:
                    raise ValueError(f"Approved 3.0 native mapping differs from core lock: {name}")
                license_file = licenses / filename
                if license_file.is_symlink() or not license_file.is_file():
                    raise ValueError(f"Missing original source license notice: {filename}")
                if (hashlib.sha256(license_file.read_bytes()).hexdigest()
                        != row["license_notice_sha256"]):
                    raise ValueError(f"Unreviewed GPL source notice bytes: {name}")
            if selected["core_set_id"] in ("gpl-source-built-ten", "gpl-source-built-eleven"):
                # mGBA MPL original license plus 11 individually pinned
                # ParaLLEl-N64 upstream GPL/LGPL/MIT notice files must be
                # present. The aggregate SHA binds every filename and byte
                # digest to the independently approved immutable native lock.
                mpl = licenses / "MPL-TRIAL-mGBA-ORIGINAL-LICENSE.txt"
                if (mpl.is_symlink() or not mpl.is_file()
                        or hashlib.sha256(mpl.read_bytes()).hexdigest()
                        != selected["cores"]["mgba"]["license_notice_sha256"]):
                    raise ValueError("Production mGBA original MPL notice missing/changed")
                notice_hashes = {}
                for number in range(1, 12):
                    filename = f"GPL-TRIAL-N64-NOTICE-{number:02}.txt"
                    notice = licenses / filename
                    if (notice.is_symlink() or not notice.is_file()
                            or not 0 < notice.stat().st_size <= 1024 * 1024):
                        raise ValueError(f"Missing source-built N64 original notice: {filename}")
                    notice_hashes[filename] = hashlib.sha256(notice.read_bytes()).hexdigest()
                combined_notice_sha = hashlib.sha256(json.dumps(
                    notice_hashes, sort_keys=True,
                    separators=(",", ":")).encode("utf-8")).hexdigest()
                if combined_notice_sha != selected["cores"]["parallel_n64"]["license_notice_sha256"]:
                    raise ValueError("Source-built N64 original notices do not match approved lock")
                for name in ("mgba", "parallel_n64"):
                    if (selected["cores"][name]["native_sha256"]
                            != records[name]["native_sha256"]):
                        raise ValueError(f"Production {name} compiled binary differs from lock")
            if selected["core_set_id"] == "gpl-source-built-eleven":
                # Source-built Dolphin original upstream license notices are
                # preserved individually; one sorted digest protects all five.
                dolphin_notices = {
                    "GPL-TRIAL-DOLPHIN-ORIGINAL-COPYING.txt",
                    "GPL-TRIAL-DOLPHIN-ORIGINAL-GPL2-OR-LATER.txt",
                    "GPL-TRIAL-DOLPHIN-ORIGINAL-BSD3.txt",
                    "GPL-TRIAL-DOLPHIN-ORIGINAL-CC0.txt",
                    "GPL-TRIAL-DOLPHIN-ORIGINAL-MIT.txt",
                }
                digest_map = {}
                for filename in sorted(dolphin_notices):
                    notice = licenses / filename
                    if (notice.is_symlink() or not notice.is_file()
                            or not 50 < notice.stat().st_size <= 1024 * 1024):
                        raise ValueError(f"Missing original upstream Dolphin license: {filename}")
                    digest_map[filename] = hashlib.sha256(notice.read_bytes()).hexdigest()
                original_notice_sha = hashlib.sha256(json.dumps(
                    digest_map, sort_keys=True,
                    separators=(",", ":")).encode("utf-8")).hexdigest()
                if (original_notice_sha != selected["cores"]["dolphin"]["license_notice_sha256"]
                        or selected["cores"]["dolphin"]["native_sha256"] != records["dolphin"]["native_sha256"]):
                    raise ValueError("New source-built Dolphin native or original notices differ from approved lock")
            if platform_name == "windows":
                win_notice = licenses / "Winpthreads-COPYING.txt"
                if win_notice.is_symlink() or not win_notice.is_file() or not win_notice.read_bytes().strip():
                    raise ValueError("Original Winpthreads source notice is required")
    if os.environ.get("AP_V30_GPL_TRIAL") == "1":
        # Never mistake test-only noncommercial-core substitutions for an
        # approved 3.0 production input. Validate the actual installed native
        # images, unapproved marker and source identities before inspecting DLLs.
        from anything_plays.v30_gpl_trial import validate_trial_core_directory
        trial_marker = validate_trial_core_directory(cores, EXTENSIONS[platform_name])
        notices = ["GPL-TRIAL-Supafaust-COPYING.txt",
                   "GPL-TRIAL-BlastEm-COPYING.txt"]
        pinned_pce = trial_marker.get("source_built_pce")
        if pinned_pce is not None:
            notices.append("GPL-TRIAL-PCE-COPYING.txt")
        for name in notices:
            notice = licenses / name
            if notice.is_symlink() or not notice.is_file() or not notice.read_bytes().strip():
                raise ValueError(f"GPL trial missing original license: {name}")
        if pinned_pce is not None:
            source_notice = licenses / "GPL-TRIAL-PCE-COPYING.txt"
            expected_sha = pinned_pce["notice_sha256"]
            if hashlib.sha256(source_notice.read_bytes()).hexdigest() != expected_sha:
                raise ValueError("Wrong original pinned-source PCE GPL2 notice")
        remaining = trial_marker.get("source_built_remaining_five")
        if remaining is not None:
            if set(remaining) != {
                "fceumm", "stella2014", "prosystem", "mednafen_ngp", "mednafen_wswan",
            }:
                raise ValueError("Incomplete five original source-built GPL notices")
            for name,row in remaining.items():
                original = licenses / f"GPL-TRIAL-{name}-ORIGINAL-COPYING.txt"
                if original.is_symlink() or not original.is_file():
                    raise ValueError(f"Original source-built GPL notice missing: {name}")
                if hashlib.sha256(original.read_bytes()).hexdigest()!=row["original_license_notice_sha256"]:
                    raise ValueError(f"Wrong original 3.0 GPL license notice: {name}")
        mgba = trial_marker.get("source_built_mgba")
        if mgba is not None:
            original = licenses / "MPL-TRIAL-mGBA-ORIGINAL-LICENSE.txt"
            if original.is_symlink() or not original.is_file():
                raise ValueError("Missing original MPL2 source license for the ninth core")
            if hashlib.sha256(original.read_bytes()).hexdigest() != mgba["original_license_notice_sha256"]:
                raise ValueError("Original ninth source-built mGBA MPL2 license was modified")
        n64 = trial_marker.get("source_built_n64")
        if n64 is not None:
            notices = n64["original_notice_sha256"]
            if len(notices) != 11:
                raise ValueError("Missing original source-built N64 license set")
            for filename, exact_sha in notices.items():
                original = licenses / filename
                if (original.is_symlink() or not original.is_file()
                        or hashlib.sha256(original.read_bytes()).hexdigest() != exact_sha):
                    raise ValueError(f"Original source-built N64 license changed: {filename}")
        if "snes9x" in expected_cores or "genesis_plus_gx" in expected_cores:
            raise ValueError("Noncommercial core entered the GPL alternative test lineup")
        if platform_name == "windows":
            win_notice = licenses / "Winpthreads-COPYING.txt"
            if (win_notice.is_symlink() or not win_notice.is_file()
                    or not win_notice.read_bytes().strip()):
                raise ValueError("Bundled MinGW runtime requires original Winpthreads permission notice")
    if len(expected_cores) > len(CORE_NAMES):
        verify_v21_artwork(bundle)
    required_notices = (
        REQUIRED_DOCUMENTS + OPTIONAL_V21_LICENSES
        if len(expected_cores) > len(CORE_NAMES) else REQUIRED_DOCUMENTS
    )
    missing = [str(licenses / filename) for filename in required_notices
               if not (licenses / filename).is_file()]
    if missing:
        raise ValueError("Missing bundled license documents:\n" + "\n".join(missing))
    for filename in required_notices:
        if not (licenses / filename).read_bytes().strip():
            raise ValueError(f"Empty bundled license document: {filename}")

    python_inventory_path = licenses / "PYTHON_DISTRIBUTIONS.json"
    if not python_inventory_path.is_file():
        raise ValueError(f"Missing Python dependency inventory: {python_inventory_path}")
    python_inventory = json.loads(python_inventory_path.read_text(encoding="utf-8"))
    distributions = python_inventory.get("distributions")
    if not isinstance(distributions, list) or not distributions:
        raise ValueError("Empty Python dependency inventory")
    python_notices = 0
    for distribution in distributions:
        listed_notice_files = distribution.get("license_files", [])
        # OpenCV wheels include FFmpeg on all platforms and Qt on non-headless
        # Linux wheels. Their distinct third-party terms must not be omitted.
        if (distribution.get("name", "").casefold() in {"opencv-python", "opencv-python-headless"}
                and not any(
                    Path(record.get("original_path", "")).name.casefold()
                    == "license-3rd-party.txt"
                    for record in listed_notice_files
                )):
            raise ValueError("Missing OpenCV third-party dependency license notice")
        for notice in listed_notice_files:
            relative = Path(notice.get("bundled_path", ""))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unsafe Python dependency notice path")
            notice_path = licenses / relative
            if not notice_path.is_file() or not notice_path.read_bytes().strip():
                raise ValueError(f"Missing/empty Python dependency notice: {relative}")
            python_notices += 1
    if not python_notices:
        raise ValueError("No bundled Python dependency notices")

    manifest_path = cores / "CORE_PROVENANCE.json"
    if not manifest_path.is_file():
        raise ValueError(f"Missing core manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest.get("cores")
    if not isinstance(records, list) or len(records) != len(expected_cores):
        raise ValueError("Manifest must identify all required cores")
    found = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid core manifest entry")
        name = record.get("name")
        if name not in expected_cores or name in found:
            raise ValueError(f"Unexpected or duplicated core: {name}")
        found.add(name)
        expected_filename = f"{name}_libretro{EXTENSIONS[platform_name]}"
        if record.get("file") != expected_filename:
            raise ValueError(f"Incorrect filename in manifest for {name}")
        path = cores / expected_filename
        if not path.is_file():
            raise ValueError(f"Missing bundled core: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != record.get("sha256"):
            raise ValueError(f"Checksum mismatch: {path}")
        if path.stat().st_size != record.get("size_bytes"):
            raise ValueError(f"Size mismatch: {path}")
        if not isinstance(record.get("source_url"), str) or not record["source_url"].startswith("https://"):
            raise ValueError(f"Missing HTTPS source URL for {name}")
        if not isinstance(record.get("libretro_library_version"), str) or not record["libretro_library_version"]:
            raise ValueError(f"Missing recorded native version for {name}")
        if not isinstance(record.get("source_repository_url"), str) or not record["source_repository_url"].startswith("https://"):
            raise ValueError(f"Missing upstream source repository for {name}")
    if "dolphin" in expected_cores:
        verify_dolphin_sys(cores, manifest)
    # Verify the staged file hashes against the approved release lock BEFORE
    # any ctypes-based native-core inspection can load the libraries.
    release_mode = os.environ.get("AP_RELEASE_BUILD", "0")
    if release_mode not in ("0", "1"):
        raise ValueError("AP_RELEASE_BUILD must be 0 or 1")
    if release_mode == "1":
        if os.environ.get("AP_V30_APPROVED_RELEASE") == "1":
            from tools.v30_release_lock import (
                load_approved_lock, verify_native_bundle,
            )
            verify_native_bundle(load_approved_lock(), manifest)
        else:
            # Old published 2.0 checks must not be affected by 3.0.
            from tools.core_release_lock import LOCK_PATH, verify_release_lock
            lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            verify_release_lock(manifest, lock)

    if check_native:
        _validate_mgba_core(cores / f"mgba_libretro{EXTENSIONS[platform_name]}")
        for record in records:
            name = record["name"]
            path = cores / record["file"]
            observed = inspect_core_identity(path, name)
            for field in ("libretro_library_name", "libretro_library_version",
                          "reported_source_revision", "source_repository_url",
                          "reported_source_commit_url"):
                if record.get(field) != observed[field]:
                    raise ValueError(f"Recorded {field} mismatch for {name}: {path}")
    print(f"Verified {platform_name} bundle: license files and {len(expected_cores)} core checksums"
          + (" and native GB/GBC/GBA coverage" if check_native else ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=tuple(EXTENSIONS))
    parser.add_argument("bundle", type=Path, help="Staged .app or application directory")
    parser.add_argument("--check-native", action="store_true",
                        help="Load the mGBA core and verify supported Game Boy formats")
    args = parser.parse_args()
    try:
        verify_bundle(args.bundle, args.platform, check_native=args.check_native)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Bundle verification FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
