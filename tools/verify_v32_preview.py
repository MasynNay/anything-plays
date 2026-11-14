"""Verify private 3.2 minimal-core preview artifacts from exact source.

This audit records truthful, redacted QA evidence. It does NOT grant release
rights, certify hardware, create a tag or upload a public installer.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess

from anything_plays.build_identity import make_identity

FILES = {
    "linux-x64": "anything-plays-32-preview_3.2.0~preview1_amd64.deb",
    "windows-x64": "AnythingPlaysSetup-3.2.0-preview1.exe",
    "macos-arm64": "AnythingPlays-3.2.0-preview1-macos-arm64.dmg",
    "macos-x64": "AnythingPlays-3.2.0-preview1-macos-x64.dmg",
}


def verify(target, installer, source_revision, *, bundle=None):
    if target not in FILES:
        raise ValueError("Unsupported 3.2 private QA target.")
    file = Path(installer)
    if (file.name != FILES[target] or not file.is_file()
            or file.is_symlink() or file.stat().st_size < 1024 * 1024):
        raise ValueError("Missing, incorrectly named, or unsafe QA installer.")
    if not re.fullmatch(r"[0-9a-f]{40}", source_revision or ""):
        raise ValueError("3.2 QA must use one exact 40-character source revision.")

    if target == "linux-x64":
        for key, expected in (
            ("Package", "anything-plays-32-preview"),
            ("Version", "3.2.0~preview1"),
        ):
            actual = subprocess.check_output(
                ["dpkg-deb", "--field", str(file), key], text=True
            ).strip()
            if actual != expected:
                raise ValueError(f"Incorrect 3.2 Debian {key}.")
    elif target == "windows-x64":
        with file.open("rb") as stream:
            if stream.read(2) != b"MZ":
                raise ValueError("Private Windows QA file is not an executable.")
    else:
        location = (
            Path(bundle) if bundle is not None
            else Path("dist/AnythingPlays32Preview.app")
        )
        plist = location / "Contents" / "Info.plist"
        with plist.open("rb") as stream:
            info = plistlib.load(stream)
        if info.get("CFBundleIdentifier") != "com.anythingplays.privatepreview32":
            raise ValueError("macOS preview bundle identifier is not isolated.")
        if (info.get("CFBundleShortVersionString") != "3.2.0"
                or info.get("CFBundleVersion") != "3.2.0.1"):
            raise ValueError("Incorrect macOS 3.2 QA version metadata.")

    # Verify the identity actually embedded in the generated frozen app.
    root = (
        Path(bundle) if bundle is not None
        else (Path("dist/AnythingPlays32Preview.app")
              if target.startswith("macos") else Path("dist/AnythingPlays"))
    )
    markers = list(root.rglob("v31_build_identity.json"))
    if len(markers) != 1 or markers[0].is_symlink():
        raise ValueError("Frozen app needs exactly one immutable preview marker.")
    identity = json.loads(markers[0].read_text(encoding="utf-8"))
    if identity != make_identity("v32_preview"):
        raise ValueError("Frozen 3.2 app contains the wrong build identity.")

    digest = hashlib.sha256()
    with file.open("rb") as stream:
        for part in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(part)
    return {
        "status": "UNRELEASED_PRIVATE_QA_ONLY",
        "version": "3.2.0-preview1",
        "channel": "v32_preview",
        "public_release_approved": False,
        "source_revision": source_revision,
        "target": target,
        "installer": file.name,
        "sha256": digest.hexdigest(),
        "size_bytes": file.stat().st_size,
        "settings_namespace": identity["settings_namespace"],
        "bundled_console_profiles": ["gb", "gbc", "gba"],
        "physical_camera_verified": False,
        "physical_controller_verified": False,
        "all_18_consoles_verified": False,
        "notarized": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=sorted(FILES), required=True)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if (os.environ.get("AP_V32_PREVIEW_BUILD") != "1"
            or os.environ.get("AP_V30_MINIMAL_CORE_BUILD") != "1"):
        parser.error("Both isolated 3.2 and minimal-core flags are required.")
    if any(os.environ.get(flag) == "1" for flag in (
            "AP_RELEASE_BUILD", "AP_V30_APPROVED_RELEASE",
            "AP_V30_STABLE_CANDIDATE", "AP_V30_TEST_CORES",
            "AP_V30_GPL_TRIAL", "AP_V30_TIA_TRIAL")):
        parser.error("Private QA cannot combine public or full-core flags.")
    record = verify(
        args.target, args.installer,
        os.environ.get("AP_V32_QA_SOURCE_SHA", ""),
        bundle=args.bundle,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("PRIVATE 3.2 QA verified:", record["target"], record["sha256"])


if __name__ == "__main__":
    main()
