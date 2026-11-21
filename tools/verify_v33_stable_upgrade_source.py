"""Private 3.3 real stable-upgrade *source-shell* package verifier.

The actual full-native stable update and 3.1.1 data migration are separate
release gates. This verifies only immutable embedded identity, package
metadata, installed-core scope and exact source SHA. Never grant approval.
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

NAMES = {
    "linux-x64": "anything-plays-31_3.3.0~upgradeqa1_amd64.deb",
    "windows-x64": "AnythingPlaysSetup-3.3.0-PRIVATE-UPGRADE-QA.exe",
    "macos-arm64": "AnythingPlays-3.3.0-UPGRADE-QA-macos-arm64.dmg",
    "macos-x64": "AnythingPlays-3.3.0-UPGRADE-QA-macos-x64.dmg",
}
STATUS = "PRIVATE_3_3_STABLE_UPGRADE_ONE_CORE_SOURCE_QA_NOT_RELEASE"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(target, installer, bundle, source_revision, *, checkout_sha=None):
    if target not in NAMES:
        raise ValueError("Unrecognized private 3.3 upgrade target")
    if type(source_revision) is not str or not re.fullmatch("[0-9a-f]{40}", source_revision):
        raise ValueError("Exact source SHA required")
    if checkout_sha is None:
        checkout_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, timeout=12
        ).strip()
    if checkout_sha != source_revision:
        raise ValueError("Package is not from the exact reviewed commit")

    installer, bundle = Path(installer), Path(bundle)
    if (installer.name != NAMES[target] or not installer.is_file()
            or installer.is_symlink() or installer.stat().st_size <= 1024 * 1024
            or not bundle.is_dir() or bundle.is_symlink()):
        raise ValueError("Untrusted or incomplete private stable-upgrade package")
    marker = validate_staged_identity(bundle, channel="v33_stable_candidate")
    identity = make_identity("v33_stable_candidate")
    if (identity["version"] != "3.3.0"
            or identity["settings_namespace"] != "anything-plays-31"
            or identity["public_release_approved"] is not False):
        raise ValueError("Stable-upgrade identity is not safe")

    if target.startswith("macos"):
        if bundle.name != "AnythingPlays31.app":
            raise ValueError("Mac build cannot update the actual 3.1.x app")
        with (bundle / "Contents" / "Info.plist").open("rb") as fd:
            info = plistlib.load(fd)
        if (info.get("CFBundleIdentifier") != "com.anythingplays.release31"
                or info.get("CFBundleShortVersionString") != "3.3.0"
                or info.get("CFBundleVersion") != "3.3.0"):
            raise ValueError("Mac package does not use the stable 3.1.x identity")
        cores = bundle / "Contents" / "Resources" / "cores"
        suffix = ".dylib"
    else:
        cores = bundle / "cores"
        suffix = ".dll" if target == "windows-x64" else ".so"
    if not cores.is_dir() or cores.is_symlink():
        raise ValueError("Private upgrade core directory missing")
    found = sorted(p.name for p in cores.iterdir() if p.name.endswith("_libretro" + suffix))
    if found != ["mgba_libretro" + suffix]:
        raise ValueError("Private one-core source package must not imply 18 bundled cores")
    core = cores / found[0]
    if core.is_symlink() or not core.is_file() or core.stat().st_size <= 1024:
        raise ValueError("Unsafe or missing mGBA native library")

    if target == "linux-x64":
        for key, value in (("Package", "anything-plays-31"),
                           ("Version", "3.3.0~upgradeqa1")):
            actual = subprocess.check_output(
                ["dpkg-deb", "-f", str(installer), key],
                text=True, timeout=15,
            ).strip()
            if actual != value:
                raise ValueError("Linux package cannot upgrade stable: " + key)
    elif target == "windows-x64":
        with installer.open("rb") as f:
            if f.read(2) != b"MZ":
                raise ValueError("Windows upgrade setup lacks the PE header")

    return {
        "schema_version": 1,
        "status": STATUS,
        "target": target,
        "source_revision": source_revision,
        "installer": NAMES[target],
        "installer_sha256": sha256(installer),
        "installer_bytes": installer.stat().st_size,
        "identity_channel": "v33_stable_candidate",
        "identity_marker": marker,
        "stable_settings_namespace": "anything-plays-31",
        "stable_package_identity_matches_311": True,
        "native_core_count": 1,
        "full_native_release_tested": False,
        "real_user_settings_migration_tested": False,
        "physical_hardware_tested": False,
        "redistribution_approved": False,
        "public_release_approved": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=sorted(NAMES), required=True)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = verify(args.target, args.installer, args.bundle, args.source_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", "utf-8")
    print("PRIVATE 3.3 one-core upgrade identity verified:", result["target"],
          result["installer_sha256"], "NOT A PUBLIC RELEASE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
