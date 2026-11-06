"""Verify staged Anything Plays bundles before creating platform installers.

This checks file presence and binary integrity. It does NOT establish that
third-party redistribution and corresponding-source obligations are satisfied.
"""

import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import sys

from fetch_mgba_core import inspect_core_identity


CORE_NAMES = ("mgba", "snes9x")
REQUIRED_DOCUMENTS = (
    "AnythingPlays-MIT.txt",
    "CODE_OF_CONDUCT.md",
    "THIRD_PARTY_NOTICES.md",
    "THIRD_PARTY_COMPONENTS.md",
    "mGBA-MPL-2.0.txt",
    "Snes9x-LICENSE.txt",
)
EXTENSIONS = {"macos": ".dylib", "windows": ".dll", "linux": ".so"}


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
    if platform_name == "macos":
        licenses = bundle / "Contents" / "Resources" / "licenses"
        cores = bundle / "Contents" / "MacOS" / "cores"
    else:
        licenses = bundle / "licenses"
        cores = bundle / "cores"

    missing = [str(licenses / filename) for filename in REQUIRED_DOCUMENTS
               if not (licenses / filename).is_file()]
    if missing:
        raise ValueError("Missing bundled license documents:\n" + "\n".join(missing))
    for filename in REQUIRED_DOCUMENTS:
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
        for notice in distribution.get("license_files", []):
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
    if not isinstance(records, list) or len(records) != len(CORE_NAMES):
        raise ValueError("Manifest must identify all required cores")
    found = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid core manifest entry")
        name = record.get("name")
        if name not in CORE_NAMES or name in found:
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
    print(f"Verified {platform_name} bundle: license files and {len(CORE_NAMES)} core checksums"
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
