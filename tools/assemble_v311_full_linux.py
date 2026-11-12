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
from verify_bundle import verify_bundle

TARGET = "linux-x64"
BASELINE_NAME = "anything-plays-31_3.1.0_amd64.deb"
QA_NAME = INSTALLERS[TARGET]
OUTPUT_STATUS = "PRIVATE_3_1_1_FULL_18_LINUX_QA_NOT_APPROVED"


def prepare(stable, qa, checksums, receipt, camera_receipt, expected_source_sha, destination):
    stable, qa, checksums, receipt, destination = map(
        Path, (stable, qa, checksums, receipt, destination))
    if (stable.name != BASELINE_NAME or qa.name != QA_NAME
            or stable.is_symlink() or qa.is_symlink()
            or not stable.is_file() or not qa.is_file()
            or min(stable.stat().st_size, qa.stat().st_size) <= 1024 * 1024):
        raise ValueError("Need real public 3.1.0 and privately built 3.1.1 DEBs")
    if (digest(stable) + "  " + BASELINE_NAME
            not in checksums.read_text("utf-8").splitlines()):
        raise ValueError("Incorrect original public 3.1.0 stable checksum")
    info = json.loads(receipt.read_text("utf-8"))
    expected = {
        "status": STATUS, "target": TARGET, "installer": QA_NAME,
        "sha256": digest(qa), "size_bytes": qa.stat().st_size,
        "source_revision": expected_source_sha, "version": "3.1.1-qa1",
        "identity_channel": "v311_candidate",
        "settings_namespace": "anything-plays-311-candidate",
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
        new = root/"source/opt/anything-plays-311-candidate"
        if (not old.is_dir() or not new.is_dir()
                or (root/"source/opt/anything-plays-31").exists()):
            raise ValueError("3.1.1 test app would replace public stable 3.1.0")
        validate_staged_identity(new, channel="v311_candidate")
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
        if ("Package: anything-plays-311-candidate" not in metadata
                or "Version: 3.1.1~qa1" not in metadata):
            raise ValueError("Wrong nonpublic 3.1.1 package identity")
        desktop = root/"source/usr/share/applications/anything-plays-311-candidate.desktop"
        if ("Name=Anything Plays 3.1.1 Private QA"
                not in desktop.read_text("utf-8")):
            raise ValueError("Wrong 3.1.1 desktop filename or display name")
        verify_bundle(new, "linux", check_native=True)
        output = destination/QA_NAME
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group",
                        str(root/"source"), str(output)],
                       check=True, timeout=120)
        subprocess.run(["dpkg-deb", "-x", str(output), str(root/"installed")],
                       check=True, timeout=120)
        installed = root/"installed/opt/anything-plays-311-candidate"
        validate_staged_identity(installed, channel="v311_candidate")
        verify_bundle(installed, "linux", check_native=True)
        if validate_trial_core_directory(installed/"cores", ".so") != original:
            raise ValueError("Repacked installer changed native 3.1.0 core bytes")
        if (root/"installed/opt/anything-plays-31").exists():
            raise ValueError("Repacked 3.1.1 would overwrite stable 3.1.0")
        report = {
            "schema_version": 1, "status": OUTPUT_STATUS,
            "target": TARGET, "installer": QA_NAME,
            "installer_sha256": digest(output),
            "installer_size_bytes": output.stat().st_size,
            "source_app_sha256": digest(qa),
            "baseline_3_1_0_sha256": digest(stable),
            "sourcebuilt_ffmpeg_off_camera_wheel_sha256": camera["native_wheel_sha256"],
            "app_source_sha": expected_source_sha,
            "version": "3.1.1", "identity_channel": "v311_candidate",
            "settings_namespace": "anything-plays-311-candidate",
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
    args = p.parse_args()
    report = prepare(args.stable, args.qa, args.checksums,
                     args.source_receipt, args.camera_receipt, args.expected_source_sha,
                     args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
