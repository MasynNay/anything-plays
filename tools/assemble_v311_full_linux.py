"""Assemble private *real* full-18-console Linux 3.1.1 source candidate.

Rebuild the 3.1.1 application from current checkout; copy ONLY unchanged,
SHA-authenticated original 11-core payload from the PUBLIC 3.1.0 package.
Keep source app's newly built Python/SDL/OpenCV runtime and settings separate.
The result is a private QA installer, never permission to publish binaries.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from anything_plays.v30_gpl_trial import validate_trial_core_directory
from tools.verify_v31_rc import validate_staged_identity
from tools.v311_camera_source_gate import require_pinned_native_camera_wheel
from tools.verify_v311_source_stage import INSTALLERS, STATUS, digest
from tools.verify_v311_stable_source_stage import (
    INSTALLERS as STABLE_INSTALLERS, STATUS as STABLE_STATUS,
)
from verify_bundle import verify_bundle

TARGET = "linux-x64"
BASELINE_NAME = "anything-plays-31_3.1.0_amd64.deb"
QA_NAME = INSTALLERS[TARGET]
OUTPUT_STATUS = "PRIVATE_3_1_1_FULL_18_LINUX_QA_NOT_APPROVED"
STABLE_FULL_STATUS = "PRIVATE_3_1_1_FULL_STABLE_UPDATE_LINUX_NOT_APPROVED"


def prepare(stable, qa, checksums, receipt, camera_receipt, expected_source_sha,
            destination, *, stable_update=False):
    stable, qa, checksums, receipt, destination = map(
        Path, (stable, qa, checksums, receipt, destination))
    new_name = STABLE_INSTALLERS[TARGET] if stable_update else QA_NAME
    channel = "v311_stable_candidate" if stable_update else "v311_candidate"
    namespace = "anything-plays-31" if stable_update else "anything-plays-311-candidate"
    if (stable.name != BASELINE_NAME or qa.name != new_name
            or stable.is_symlink() or qa.is_symlink()
            or not stable.is_file() or not qa.is_file()
            or min(stable.stat().st_size, qa.stat().st_size) <= 1024 * 1024):
        raise ValueError("Need real public 3.1.0 and privately built 3.1.1 DEBs")
    if (digest(stable) + "  " + BASELINE_NAME
            not in checksums.read_text("utf-8").splitlines()):
        raise ValueError("Incorrect original public 3.1.0 stable checksum")
    info = json.loads(receipt.read_text("utf-8"))
    expected = {
        "status": STABLE_STATUS if stable_update else STATUS,
        "target": TARGET, "installer": new_name,
        "sha256": digest(qa), "size_bytes": qa.stat().st_size,
        "source_revision": expected_source_sha,
        "version": "3.1.1" if stable_update else "3.1.1-qa1",
        "identity_channel": channel,
        "settings_namespace": namespace,
        "native_core_count": 1, "full_18_console_installer": False,
        "public_release_approved": False,
    }
    for key, value in expected.items():
        if type(info.get(key)) is not type(value) or info.get(key) != value:
            raise ValueError("Wrong original 3.1.1 source-stage receipt: " + key)
    camera = require_pinned_native_camera_wheel(camera_receipt, TARGET)
    if not isinstance(expected_source_sha, str) or len(expected_source_sha) != 40:
        raise ValueError("Missing exact source revision")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Refusing to overwrite any installer destination")
    destination.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="ap311-full-linux-") as tmp:
        root = Path(tmp)
        subprocess.run(["dpkg-deb", "-x", str(stable), str(root/"stable")],
                       check=True, timeout=120)
        subprocess.run(["dpkg-deb", "-R", str(qa), str(root/"source")],
                       check=True, timeout=120)
        old = root/"stable/opt/anything-plays-31"
        new = root/("source/opt/anything-plays-31" if stable_update
                    else "source/opt/anything-plays-311-candidate")
        if not old.is_dir() or not new.is_dir():
            raise ValueError("Missing separate current 3.1.1 and original 3.1.0 core installs")
        if (stable_update and (root/"source/opt/anything-plays-311-candidate").exists()
                or not stable_update and (root/"source/opt/anything-plays-31").exists()):
            raise ValueError("Installer has a mislabeled stable/QA path")
        validate_staged_identity(new, channel=channel)
        originals = old/"cores"
        destination_cores = new/"cores"
        original = validate_trial_core_directory(originals, ".so")
        if (original.get("total_source_built_core_families") != 11
                or original.get("source_built_dolphin") is None
                or original.get("source_built_tia") is None):
            raise ValueError("Public 3.1.0 missing the reviewed full 11-core set")
        if any(p.is_symlink() for p in originals.rglob("*")):
            raise ValueError("Refusing to reuse a linked emulator source core")
        # Critical: do not copy the baseline 3.1.0 Python app or settings.
        shutil.rmtree(destination_cores)
        shutil.copytree(originals, destination_cores)
        if validate_trial_core_directory(destination_cores, ".so") != original:
            raise ValueError("Original core bytes mutated while assembling 3.1.1")
        skip = {
            "PYTHON_DISTRIBUTIONS.json", "THIRD_PARTY_NOTICES.md",
            "THIRD_PARTY_COMPONENTS.md",
        }
        old_notices, new_notices = old/"licenses", new/"licenses"
        if not (new_notices/"python-distribution-notices").is_dir():
            raise ValueError("Missing private app's own pygame/SDL source notices")
        for p in old_notices.iterdir():
            if p.is_symlink():
                raise ValueError("Symlinked historical source notice")
            if p.is_file() and p.name not in skip:
                shutil.copy2(p, new_notices/p.name)
        control = root/"source/DEBIAN/control"
        metadata = control.read_text("utf-8")
        expected_pkg = "anything-plays-31" if stable_update else "anything-plays-311-candidate"
        expected_version = "3.1.1" if stable_update else "3.1.1~qa1"
        if ("Package: " + expected_pkg not in metadata
                or "Version: " + expected_version not in metadata):
            raise ValueError("Wrong exact 3.1.1 source-stage package/version")
        desktop = root/"source/usr/share/applications"/(expected_pkg+".desktop")
        expected_title = "Anything Plays 3.1.1" + ("" if stable_update else " Private QA")
        if "Name="+expected_title not in desktop.read_text("utf-8"):
            raise ValueError("Wrong 3.1.1 desktop filename or stable update name")
        verify_bundle(new, "linux", check_native=True)
        output = destination/new_name
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group",
                        str(root/"source"), str(output)],
                       check=True, timeout=120)
        subprocess.run(["dpkg-deb", "-x", str(output), str(root/"installed")],
                       check=True, timeout=120)
        installed = root/("installed/opt/anything-plays-31" if stable_update
                          else "installed/opt/anything-plays-311-candidate")
        validate_staged_identity(installed, channel=channel)
        verify_bundle(installed, "linux", check_native=True)
        if validate_trial_core_directory(installed/"cores", ".so") != original:
            raise ValueError("Repacked installer changed native 3.1.0 core bytes")
        if not stable_update and (root/"installed/opt/anything-plays-31").exists():
            raise ValueError("Private QA would overwrite stable 3.1.0")
        if stable_update and (root/"installed/opt/anything-plays-311-candidate").exists():
            raise ValueError("Stable upgrade unexpectedly retained the private QA install")
        report = {
            "schema_version": 1,
            "status": STABLE_FULL_STATUS if stable_update else OUTPUT_STATUS,
            "target": TARGET, "installer": new_name,
            "installer_sha256": digest(output),
            "installer_size_bytes": output.stat().st_size,
            "source_app_sha256": digest(qa),
            "baseline_3_1_0_sha256": digest(stable),
            "sourcebuilt_ffmpeg_off_camera_wheel_sha256": camera["native_wheel_sha256"],
            "app_source_sha": expected_source_sha,
            "version": "3.1.1", "identity_channel": channel,
            "settings_namespace": namespace,
            "stable_in_place_update": stable_update,
            "core_families": original["total_source_built_core_families"],
            "native_core_count": 11, "console_profiles": 18,
            "source_reviewed_core_hashes_preserved": True,
            "public_release_approved": False,
            "physical_gamepad_or_camera_verified": False,
            "full_four_platform_311_verified": False,
        }
        (destination/"V311_FULL_LINUX_QA_RECEIPT.json").write_text(
            json.dumps(report, indent=2) + "\n", "utf-8")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stable", type=Path, required=True)
    p.add_argument("--qa", type=Path, required=True)
    p.add_argument("--checksums", type=Path, required=True)
    p.add_argument("--source-receipt", type=Path, required=True)
    p.add_argument("--camera-receipt", type=Path, required=True)
    p.add_argument("--expected-source-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--stable-update", action="store_true",
                   help="Privately assemble true 3.1.1 upgrade identity, not QA")
    args = p.parse_args()
    report = prepare(args.stable, args.qa, args.checksums,
                     args.source_receipt, args.camera_receipt, args.expected_source_sha,
                     args.output, stable_update=args.stable_update)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
