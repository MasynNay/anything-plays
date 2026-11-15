"""Finalize private, VERIFIED full-native 3.2 package into real 3.2.0 metadata.

Release candidates are produced on native GitHub Actions runners only.
This script cannot publish GitHub releases and never grants license approval.
The app remains exactly the already-tested v32_stable_candidate identity.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile

from tools.stage_v32_full_linux import sha256, full_inventory as linux_inventory
from tools.stage_v32_stable_full_linux import STATUS as LINUX_STATUS
from tools.stage_v32_stable_full_windows import STATUS as WINDOWS_STATUS
from tools.stage_v32_stable_full_macos import STATUS as MAC_STATUS
from tools.verify_v31_rc import validate_staged_identity

TARGETS = {
    "linux-x64": ("anything-plays-31_3.2.0~fullupgradeqa1_amd64.deb",
                  "anything-plays-31_3.2.0_amd64.deb", LINUX_STATUS),
    "windows-x64": ("AnythingPlaysSetup-3.2.0-fullupgradeqa1-PRIVATE-UPGRADE-QA.exe",
                    "AnythingPlaysSetup-3.2.0.exe", WINDOWS_STATUS),
    "macos-arm64": ("AnythingPlays-3.2.0-fullupgradeqa1-macos-arm64.dmg",
                    "AnythingPlays-3.2.0-macos-arm64.dmg", MAC_STATUS),
    "macos-x64": ("AnythingPlays-3.2.0-fullupgradeqa1-macos-x64.dmg",
                  "AnythingPlays-3.2.0-macos-x64.dmg", MAC_STATUS),
}
STATUS = "3_2_FINAL_NATIVE_RELEASE_CANDIDATE_VERIFIED_NOT_YET_PUBLISHED"


def validate_qa_receipt(target, source, receipt, revision):
    if target not in TARGETS:
        raise ValueError("Unknown native 3.2 platform")
    expected_name, public_name, expected_status = TARGETS[target]
    source = Path(source)
    receipt = Path(receipt)
    if (source.name != expected_name or not source.is_file()
            or source.is_symlink() or source.stat().st_size < 1024 * 1024
            or not receipt.is_file() or receipt.is_symlink()
            or not 0 < receipt.stat().st_size <= 65536):
        raise ValueError("Expected full-native private staged artifact missing")
    data = json.loads(receipt.read_text("utf-8"))
    if (type(data) is not dict
            or data.get("status") != expected_status
            or data.get("target") != target
            or data.get("source_revision") != revision
            or data.get("installer") != expected_name
            or data.get("installer_sha256") != sha256(source)
            or type(data.get("native_core_count")) is not int
            or data["native_core_count"] != 11
            or data.get("console_profiles") != 18
            or data.get("native_core_bytes_preserved") is not True
            or data.get("stable_settings_namespace",
                        data.get("settings_namespace")) != "anything-plays-31"
            or data.get("public_release_approved") is not False
            or data.get("redistribution_approved", False) is not False):
        raise ValueError("Unreviewed full-native 3.2 source or receipt")
    return source, public_name


def _linux(source, destination):
    with tempfile.TemporaryDirectory(prefix="ap32-finalize-deb-") as td:
        root = Path(td) / "package"
        subprocess.run(["dpkg-deb", "-R", str(source), str(root)],
                       check=True, timeout=180)
        app = root / "opt" / "anything-plays-31"
        validate_staged_identity(app, channel="v32_stable_candidate")
        core_before = linux_inventory(app / "cores")
        control = root / "DEBIAN" / "control"
        body = control.read_text("utf-8")
        old = "Version: 3.2.0~fullupgradeqa1\n"
        if body.count(old) != 1 or "Package: anything-plays-31\n" not in body:
            raise ValueError("Candidate is not a stable 3.1.x Debian upgrade")
        control.write_text(body.replace(old, "Version: 3.2.0\n"), "utf-8")
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group",
                        str(root), str(destination)], check=True, timeout=180)
        extracted = Path(td) / "extracted"
        subprocess.run(["dpkg-deb", "-x", str(destination), str(extracted)],
                       check=True, timeout=180)
        installed = extracted / "opt" / "anything-plays-31"
        validate_staged_identity(installed, channel="v32_stable_candidate")
        if linux_inventory(installed / "cores") != core_before:
            raise ValueError("Final Debian repack changed original 11 cores")
        for field, value in (("Package", "anything-plays-31"),
                             ("Version", "3.2.0")):
            if subprocess.check_output(
                ["dpkg-deb", "-f", str(destination), field],
                text=True, timeout=15,
            ).strip() != value:
                raise ValueError("Incorrect stable 3.2 Debian metadata")


def _windows(source, destination):
    from tools.assemble_v31_full_windows import unpack, source_app, iscc
    from tools.stage_v32_full_windows import full_inventory
    root = Path(__file__).resolve().parents[1]
    app = root / "dist" / "AnythingPlays"
    validate_staged_identity(app, channel="v32_stable_candidate")
    before = full_inventory(app / "cores")
    if before.get("native_core_count") != 11:
        raise ValueError("Full 3.2 Windows native source app incomplete")
    script = root / "packaging" / "installer.iss"
    subprocess.run([iscc(), "/DV32UpgradeQABuild=1",
                    "/DAppVersion=3.2.0", str(script)],
                   check=True, timeout=600, cwd=root)
    built = root / "release" / "AnythingPlaysSetup-3.2.0-PRIVATE-UPGRADE-QA.exe"
    if not built.is_file() or built.is_symlink():
        raise ValueError("Actual new 3.2.0 Inno output missing")
    with tempfile.TemporaryDirectory(prefix="ap32-finalize-inno-") as td:
        unpack(built, Path(td)/"payload")
        staged = source_app(Path(td)/"payload", "V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json")
        validate_staged_identity(staged, channel="v32_stable_candidate")
        if full_inventory(staged/"cores") != before:
            raise ValueError("Final stable Inno setup changed 11 core bytes")
        shutil.copyfile(built, destination)


def _mac(source, destination):
    from tools.assemble_v31_full_macos import create_disk_image, mount
    from tools.stage_v32_stable_full_macos import full_inventory, verify_identity
    with tempfile.TemporaryDirectory(prefix="ap32-finalize-mac-") as td:
        root=Path(td)
        with mount(source, root/"source"):
            app = root/"source"/"AnythingPlays31.app"
            verify_identity(app)
            before=full_inventory(app/"Contents/Resources/cores")
            if before.get("native_core_count") != 11:
                raise ValueError("Original Mac full native library set missing")
            shutil.copytree(app, root/"AnythingPlays31.app", symlinks=True)
        final_app=root/"AnythingPlays31.app"
        verify_identity(final_app)
        create_disk_image(final_app, destination, volume_name="Anything Plays 3.2")
        with mount(destination, root/"final"):
            actual=root/"final"/"AnythingPlays31.app"
            verify_identity(actual)
            if full_inventory(actual/"Contents/Resources/cores")!=before:
                raise ValueError("Final Mac DMG changed original 11 native cores")
            subprocess.run(["codesign","--verify","--verbose=2",str(actual)],
                           check=True, timeout=60)


def finalize(target, source, receipt, revision, output):
    source, public_name = validate_qa_receipt(
        target, source, receipt, revision,
    )
    if (os.getenv("GITHUB_ACTIONS") != "true"
            or os.getenv("AP_V32_STABLE_CANDIDATE") != "1"
            or os.getenv("AP_RELEASE_BUILD") == "1"):
        raise ValueError("Only full-native staged CI candidates can be finalized")
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Refuse to overwrite existing release candidate")
    output.mkdir(parents=True)
    dest = output/public_name
    if target == "linux-x64":
        _linux(source, dest)
    elif target == "windows-x64":
        _windows(source, dest)
    else:
        _mac(source, dest)
    result = {
        "schema_version": 1,
        "status": STATUS,
        "source_revision": revision,
        "target": target,
        "file": public_name,
        "sha256": sha256(dest),
        "bytes": dest.stat().st_size,
        "native_core_families": 11,
        "console_profiles": 18,
        "same_stable_311_install_identity": True,
        "original_311_core_binary_bytes_preserved": True,
        "installer_release_version": "3.2.0",
        "physical_webcam_or_controller_tested": False,
        "all_commercial_games_tested": False,
        "final_redistribution_approved": False,
        "published": False,
    }
    (output/"V32_NATIVE_RELEASE_CANDIDATE.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n","utf-8"
    )
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target",choices=sorted(TARGETS),required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--receipt",type=Path,required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(finalize(a.target,a.source,a.receipt,a.source_sha,a.output),
                     indent=2,sort_keys=True))


if __name__=="__main__":
    main()
