"""Verify four-platform 3.3 *unreleased* QA installers before retaining.

Checks installer bytes, independent identity and mGBA-only core scope.
This is NOT an approval to distribute native cores, a test of actual installed
desktop behavior, or evidence of real webcam/controller/GameCube performance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from anything_plays.build_identity import make_identity, validate_identity

TARGETS = {
    "linux-x64": "anything-plays-33-candidate_3.3.0~qa1_amd64.deb",
    "windows-x64": "AnythingPlaysSetup-3.3.0-qa1.exe",
    "macos-arm64": "AnythingPlays-3.3.0-qa1-macos-arm64.dmg",
    "macos-x64": "AnythingPlays-3.3.0-qa1-macos-x64.dmg",
}
_SHA = re.compile(r"^[a-f0-9]{40}$")


def verify_candidate(*, target, bundle, installer, source_sha):
    if target not in TARGETS:
        raise ValueError("Unrecognized 3.3 QA platform")
    if not _SHA.fullmatch(source_sha):
        raise ValueError("Full exact 40-digit source commit required")
    bundle, installer = Path(bundle), Path(installer)
    if installer.name != TARGETS[target] or not installer.is_file():
        raise ValueError("3.3 QA installer missing or unexpected filename")
    if installer.stat().st_size <= 10000:
        raise ValueError("3.3 QA installer appears empty/truncated")
    markers = list(bundle.rglob("v31_build_identity.json"))
    if len(markers) != 1:
        raise ValueError("Expected one frozen, immutable 3.3 identity")
    identity = validate_identity(json.loads(markers[0].read_text("utf-8")))
    if identity != make_identity("v33_candidate"):
        raise ValueError("Stable/previous-preview build is not 3.3 QA")
    if target.startswith("macos"):
        core_root = bundle / "Contents" / "Resources" / "cores"
        expected_suffix = ".dylib"
    else:
        core_root = bundle / "cores"
        expected_suffix = ".dll" if target.startswith("windows") else ".so"
    if not core_root.is_dir():
        raise ValueError("Bundled native core folder missing")
    cores = sorted(
        child.name for child in core_root.iterdir()
        if child.is_file() and child.name.endswith("_libretro" + expected_suffix)
    )
    if cores != ["mgba_libretro" + expected_suffix]:
        raise ValueError("Only original mGBA permitted in 3.3 QA candidate")
    if (core_root / "dolphin-emu").exists():
        raise ValueError("GameCube and Dolphin Sys must not ship in QA candidate")
    digest = hashlib.sha256()
    with installer.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "format": "anything-plays-v33-owner-qa",
        "target": target,
        "source_sha": source_sha,
        "channel": identity["channel"],
        "version": identity["version"],
        "settings_namespace": identity["settings_namespace"],
        "installer_filename": installer.name,
        "installer_sha256": digest.hexdigest(),
        "bundled_core_names": cores,
        "bundled_core_count": len(cores),
        "public_release_approved": False,
        "hardware_input_tested": False,
        "physical_camera_tested": False,
        "gamecube_bundled": False,
        "full_18_console_gameplay_tested": False,
        "installer_fully_tested_on_real_host": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=sorted(TARGETS), required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = verify_candidate(
        target=args.target, bundle=args.bundle,
        installer=args.installer, source_sha=args.source_sha,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("Verified unpublished 3.3 mGBA-only QA candidate:", args.target)


if __name__ == "__main__":
    main()
