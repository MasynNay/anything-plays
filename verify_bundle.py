"""Verify staged Anything Plays bundles before creating platform installers.

This checks file presence and binary integrity. It does NOT establish that
third-party redistribution and corresponding-source obligations are satisfied.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys


CORE_NAMES = ("gambatte", "mgba", "snes9x")
REQUIRED_DOCUMENTS = (
    "AnythingPlays-MIT.txt",
    "CODE_OF_CONDUCT.md",
    "THIRD_PARTY_NOTICES.md",
    "THIRD_PARTY_COMPONENTS.md",
    "Gambatte-GPL-2.0.txt",
    "mGBA-MPL-2.0.txt",
    "Snes9x-LICENSE.txt",
)
EXTENSIONS = {"macos": ".dylib", "windows": ".dll", "linux": ".so"}


def verify_bundle(bundle, platform_name):
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

    manifest_path = cores / "CORE_PROVENANCE.json"
    if not manifest_path.is_file():
        raise ValueError(f"Missing core manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest.get("cores")
    if not isinstance(records, list) or len(records) != len(CORE_NAMES):
        raise ValueError("Manifest must identify all three cores")
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
    print(f"Verified {platform_name} bundle: license files and 3 core checksums")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=tuple(EXTENSIONS))
    parser.add_argument("bundle", type=Path, help="Staged .app or application directory")
    args = parser.parse_args()
    try:
        verify_bundle(args.bundle, args.platform)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Bundle verification FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
