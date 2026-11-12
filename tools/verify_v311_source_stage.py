"""Authenticate a PRIVATE, source-built 3.1.1 mGBA-only stage on each host.

A successful source shell is not a full 18-console release and CANNOT be
published as v3.1.1. Each original source-built package must later be
assembled with all 11 original-source cores and independently installed/QA'd.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess

from anything_plays.build_identity import make_identity
from tools.verify_v31_rc import validate_staged_identity

INSTALLERS = {
    "linux-x64": "anything-plays-311-candidate_3.1.1~qa1_amd64.deb",
    "windows-x64": "AnythingPlaysSetup-3.1.1-qa1.exe",
    "macos-arm64": "AnythingPlays-3.1.1-qa1-macos-arm64.dmg",
    "macos-x64": "AnythingPlays-3.1.1-qa1-macos-x64.dmg",
}
APP_BUNDLE = "AnythingPlays311QA.app"
STATUS = "PRIVATE_3_1_1_MGBA_ONLY_SOURCE_SHELL_NOT_RELEASE"
SOURCE = re.compile(r"[a-f0-9]{40}\Z")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for part in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def verify(target, installer, bundle, expected_source_sha, *, checkout=None):
    if target not in INSTALLERS:
        raise ValueError("Not an approved private 3.1.1 target")
    if not isinstance(expected_source_sha, str) or SOURCE.fullmatch(expected_source_sha) is None:
        raise ValueError("Expected exact source commit SHA required")
    if checkout is None:
        checkout = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, timeout=15,
        ).strip()
    if checkout != expected_source_sha:
        raise ValueError("Source-built package does not match current checkout")
    installer, bundle = Path(installer), Path(bundle)
    if (installer.name != INSTALLERS[target] or not installer.is_file()
            or installer.is_symlink() or installer.stat().st_size <= 1024 * 1024):
        raise ValueError("Wrong or missing 3.1.1 private QA installer")
    if not bundle.is_dir() or bundle.is_symlink():
        raise ValueError("Missing local, unsymlinked original frozen build")
    marker = validate_staged_identity(bundle, channel="v311_candidate")
    ident = make_identity("v311_candidate")
    if ident["version"] != "3.1.1" or ident["public_release_approved"] is not False:
        raise ValueError("Private identity incorrectly claims public release")
    if target.startswith("macos"):
        if bundle.name != APP_BUNDLE:
            raise ValueError("Mac QA app would collide with public 3.1.0")
        with (bundle / "Contents" / "Info.plist").open("rb") as inp:
            plist = plistlib.load(inp)
        if (plist.get("CFBundleIdentifier") != "com.anythingplays.private311qa"
                or plist.get("CFBundleShortVersionString") != "3.1.1"
                or plist.get("CFBundleVersion") != "3.1.1"):
            raise ValueError("3.1.1 macOS QA bundle identifier/version mismatch")
        cores = bundle / "Contents" / "Resources" / "cores"
        suffix = ".dylib"
    else:
        cores = bundle / "cores"
        suffix = ".dll" if target == "windows-x64" else ".so"
    native = sorted(path for path in cores.iterdir()
                    if path.name.endswith("_libretro" + suffix))
    if len(native) != 1 or native[0].name != "mgba_libretro" + suffix:
        raise ValueError("3.1.1 source-stage package must have exactly one core")
    if native[0].is_symlink() or native[0].stat().st_size < 1024:
        raise ValueError("Missing genuine native mGBA source artifact")
    if target == "linux-x64":
        # dpkg-deb labels BOTH values when multiple fields are requested
        # ("Package: foo\\nVersion: bar"), while one field returns a value.
        # Read each field separately to verify the real installed package ID.
        package = subprocess.check_output(
            ["dpkg-deb", "-f", str(installer), "Package"],
            text=True, timeout=15,
        ).strip()
        version = subprocess.check_output(
            ["dpkg-deb", "-f", str(installer), "Version"],
            text=True, timeout=15,
        ).strip()
        if (package, version) != ("anything-plays-311-candidate", "3.1.1~qa1"):
            raise ValueError("Wrong Linux package/version metadata")
    return {
        "schema_version": 1,
        "status": STATUS,
        "target": target,
        "installer": installer.name,
        "sha256": digest(installer),
        "size_bytes": installer.stat().st_size,
        "source_revision": expected_source_sha,
        "version": "3.1.1-qa1",
        "identity_channel": "v311_candidate",
        "settings_namespace": ident["settings_namespace"],
        "embedded_marker": marker,
        "native_core_count": 1,
        "console_profiles": ["gb", "gbc", "gba"],
        "full_18_console_installer": False,
        "public_release_approved": False,
        "physical_controller_tested": False,
        "physical_camera_tested": False,
        "third_party_rights_fully_reviewed": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", required=True, choices=tuple(INSTALLERS))
    p.add_argument("--installer", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--expected-source-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = verify(args.target, args.installer, args.bundle,
                    args.expected_source_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    print("Verified PRIVATE 3.1.1 source stage:", report["target"],
          report["source_revision"], "one native core; NOT public")


if __name__ == "__main__":
    main()
