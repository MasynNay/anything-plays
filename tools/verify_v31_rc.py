"""Verify the source-built, isolated 3.1 RC1 application-stage installer.

This is an intentionally **mGBA-only staging build**, not the complete
18-console release candidate. Passing cannot authorize a public release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess

from anything_plays.build_identity import make_identity, validate_identity

INSTALLERS = {
    "linux-x64": "anything-plays-31-rc1_3.1.0~rc1_amd64.deb",
    "windows-x64": "AnythingPlaysSetup-3.1.0-rc1.exe",
    "macos-arm64": "AnythingPlays-3.1.0-rc1-macos-arm64.dmg",
    "macos-x64": "AnythingPlays-3.1.0-rc1-macos-x64.dmg",
}
STATUS = "UNRELEASED_3_1_RC1_APP_STAGE_ONLY"
RC2_STATUS = "UNRELEASED_3_1_RC2_APP_STAGE_ONLY"
RC2_INSTALLERS = {
    "linux-x64": "anything-plays-31-rc2_3.1.0~rc2_amd64.deb",
    "windows-x64": "AnythingPlaysSetup-3.1.0-rc2.exe",
    "macos-arm64": "AnythingPlays-3.1.0-rc2-macos-arm64.dmg",
    "macos-x64": "AnythingPlays-3.1.0-rc2-macos-x64.dmg",
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_staged_identity(bundle, *, channel="rc1"):
    bundle = Path(bundle)
    if not bundle.is_dir() or bundle.is_symlink():
        raise ValueError("Missing or linked frozen application directory")
    matches = list(bundle.rglob("v31_build_identity.json"))
    if len(matches) != 1:
        raise ValueError("Expected exactly one 3.1 build identity in frozen app")
    marker = matches[0]
    if marker.is_symlink() or not marker.resolve().is_relative_to(bundle.resolve()):
        raise ValueError("Unsafe frozen build identity")
    try:
        identity = validate_identity(json.loads(marker.read_text("utf-8")))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Invalid frozen app identity JSON") from exc
    if identity != make_identity(channel):
        raise ValueError("App is a preview or has incorrect release-candidate identity")
    return marker.relative_to(bundle).as_posix()


def verify(target, installer, bundle, source_revision, *, channel="rc1"):
    installer, bundle = Path(installer), Path(bundle)
    installers = RC2_INSTALLERS if channel == "rc2" else INSTALLERS if channel == "rc1" else None
    if installers is None or target not in installers or installer.name != installers[target]:
        raise ValueError("Unknown 3.1 RC1 installer or target")
    if not re.fullmatch(r"[a-f0-9]{40}", source_revision):
        raise ValueError("RC build requires an exact git revision")
    if (not installer.is_file() or installer.is_symlink()
            or installer.stat().st_size < 1024 * 1024):
        raise ValueError("Missing or incomplete 3.1 RC candidate")
    identity_file = validate_staged_identity(bundle, channel=channel)
    if target == "linux-x64":
        for field, expected in (("Package", "anything-plays-31-" + channel),
                                ("Version", "3.1.0~" + channel)):
            found = subprocess.check_output(
                ["dpkg-deb", "--field", str(installer), field], text=True,
            ).strip()
            if found != expected:
                raise ValueError(f"Unexpected Linux RC1 {field}: {found}")
    elif target == "windows-x64":
        with installer.open("rb") as binary:
            if binary.read(2) != b"MZ":
                raise ValueError("Windows RC installer lacks PE signature")
    else:
        plist = bundle / "Contents" / "Info.plist"
        with plist.open("rb") as stream:
            info = plistlib.load(stream)
        bundle_id = "com.anythingplays.rc31v2" if channel == "rc2" else "com.anythingplays.rc31"
        if (info.get("CFBundleIdentifier") != bundle_id
                or info.get("CFBundleShortVersionString") != "3.1.0"):
            raise ValueError("Mac RC identity or version mismatch")
    return {
        "schema_version": 1,
        "status": RC2_STATUS if channel == "rc2" else STATUS,
        "public_release_approved": False,
        "final_release_candidate": False,
        "stage": "source-built application and mGBA only; full 11-core package pending",
        "target": target,
        "source_revision": source_revision,
        "version": "3.1.0-" + channel,
        "identity_file": identity_file,
        "settings_namespace": make_identity(channel)["settings_namespace"],
        "installer": installer.name,
        "sha256": digest(installer),
        "size_bytes": installer.stat().st_size,
        "bundled_console_profiles": ["gb", "gbc", "gba"],
        "hardware_controller_verified": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", choices=sorted(INSTALLERS), required=True)
    p.add_argument("--channel", choices=("rc1", "rc2"), default="rc1")
    p.add_argument("--installer", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if (os.environ.get("AP_V31_RC2" if args.channel == "rc2" else "AP_V31_RC") != "1"
            or os.environ.get("AP_V31_RC" if args.channel == "rc2" else "AP_V31_RC2") == "1"
            or os.environ.get("AP_V30_MINIMAL_CORE_BUILD") != "1"):
        p.error("Explicit RC application-stage flags are required")
    if os.environ.get("AP_RELEASE_BUILD") == "1":
        p.error("RC application stage must never enable public release mode")
    record = verify(args.target, args.installer, args.bundle,
                    os.environ.get("GITHUB_SHA", ""), channel=args.channel)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n",
                           encoding="utf-8")
    print(f"Verified isolated {record['target']} {args.channel.upper()} app stage; "
          "full 18-console release candidate is NOT built yet")


if __name__ == "__main__":
    main()
