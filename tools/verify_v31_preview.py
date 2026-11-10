"""Validate an unreleased 3.1 Preview 1 installer and its SHA-256."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess

FILENAMES = {
    "linux-x64": "anything-plays-31-preview_3.1.0~preview1_amd64.deb",
    "windows-x64": "AnythingPlaysSetup-3.1.0-preview1.exe",
    "macos-arm64": "AnythingPlays-3.1.0-preview1-macos-arm64.dmg",
    "macos-x64": "AnythingPlays-3.1.0-preview1-macos-x64.dmg",
}
STATUS = "UNRELEASED_QA_ARTIFACT"


def verify(target, filename, revision):
    file = Path(filename)
    if target not in FILENAMES or file.name != FILENAMES[target]:
        raise ValueError("Installer filename or target is not Preview 1")
    if not file.is_file() or file.is_symlink() or file.stat().st_size < 1024 * 1024:
        raise ValueError("Missing, unsafe, or incomplete preview installer")
    if not re.fullmatch("[0-9a-f]{40}", revision):
        raise ValueError("Expected an exact source commit")
    if target == "linux-x64":
        for key, expected in (
            ("Package", "anything-plays-31-preview"),
            ("Version", "3.1.0~preview1"),
        ):
            actual = subprocess.check_output(
                ["dpkg-deb", "--field", str(file), key], text=True
            ).strip()
            if actual != expected:
                raise ValueError(f"Unexpected DEB {key}: {actual}")
    elif target.startswith("macos"):
        plist = Path("dist/AnythingPlays31Preview.app/Contents/Info.plist")
        with plist.open("rb") as stream:
            info = plistlib.load(stream)
        if info.get("CFBundleIdentifier") != "com.anythingplays.preview31":
            raise ValueError("macOS 3.1 preview identity is not isolated")
        if info.get("CFBundleShortVersionString") != "3.1.0":
            raise ValueError("Incorrect macOS preview version")
    else:
        with file.open("rb") as stream:
            if stream.read(2) != b"MZ":
                raise ValueError("Installer is not a Windows executable")
    digest = hashlib.sha256()
    with file.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return {
        "status": STATUS,
        "public_release_approved": False,
        "version": "3.1.0-preview1",
        "source_revision": revision,
        "target": target,
        "installer": file.name,
        "sha256": digest.hexdigest(),
        "size_bytes": file.stat().st_size,
        "bundled_console_profiles": ["gb", "gbc", "gba"],
        "physical_controller_verified": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=sorted(FILENAMES), required=True)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("AP_V31_PREVIEW") != "1" or os.environ.get("AP_V30_MINIMAL_CORE_BUILD") != "1":
        parser.error("Both explicit non-release preview flags are required")
    if any(os.environ.get(x) == "1" for x in ("AP_RELEASE_BUILD", "AP_V30_APPROVED_RELEASE", "AP_V30_STABLE_CANDIDATE")):
        parser.error("Never mix Preview 1 with production build flags")
    record = verify(args.target, args.file, os.environ.get("GITHUB_SHA", ""))
    args.output.parent.mkdir(exist_ok=True, parents=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("Verified Preview 1", record["target"], record["sha256"])


if __name__ == "__main__":
    main()
