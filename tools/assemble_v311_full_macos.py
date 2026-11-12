"""Assemble both private full-18-console 3.1.1 Mac QA DMGs.

Do not relabel or resign the public 3.1.0 app. Unchanged, publicly released
source-verified cores and original notices are transferred into a separately
source-built QA app with its own version, bundle ID and preference namespace.
No public release, Apple notarization or physical hardware acceptance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile

from anything_plays.v30_gpl_trial import validate_trial_core_directory
from tools.assemble_v31_full_macos import mount, create_disk_image
from tools.audit_v31_sdl_runtime import inspect_bundle
from tools.verify_v31_rc import validate_staged_identity
from tools.v311_camera_source_gate import require_pinned_native_camera_wheel
from tools.verify_v311_source_stage import INSTALLERS, STATUS, digest
from verify_bundle import verify_bundle

STATUS_FULL = "PRIVATE_3_1_1_FULL_18_MACOS_QA_NOT_APPROVED"


def build(arch, stable, qa, checksums, receipt, camera_receipt, expected_source_sha, output):
    if arch not in ("arm64", "x64"):
        raise ValueError("Wrong native Mac architecture")
    stable, qa, checksums, receipt, output = map(
        Path, (stable, qa, checksums, receipt, output))
    target = "macos-"+arch
    old_name = "AnythingPlays-3.1.0-macos-"+arch+".dmg"
    qa_name = INSTALLERS[target]
    if (stable.name != old_name or qa.name != qa_name
            or stable.is_symlink() or qa.is_symlink()
            or not stable.is_file() or not qa.is_file()
            or min(stable.stat().st_size, qa.stat().st_size) <= 1024 * 1024):
        raise ValueError("Actual 3.1.0 public and 3.1.1 QA DMGs required")
    if (digest(stable) + "  " + old_name
            not in checksums.read_text("utf-8").splitlines()):
        raise ValueError("Original public Mac stable SHA256 mismatch")
    original = json.loads(receipt.read_text("utf-8"))
    expected = {
        "target": target, "status": STATUS, "installer": qa_name,
        "sha256": digest(qa), "size_bytes": qa.stat().st_size,
        "source_revision": expected_source_sha, "version": "3.1.1-qa1",
        "identity_channel": "v311_candidate",
        "settings_namespace": "anything-plays-311-candidate",
        "native_core_count": 1, "full_18_console_installer": False,
        "public_release_approved": False,
    }
    for key, value in expected.items():
        if type(original.get(key)) is not type(value) or original.get(key) != value:
            raise ValueError("Exact 3.1.1 Mac source receipt mismatch: "+key)
    from tools.verify_v311_source_stage import SOURCE
    if not isinstance(expected_source_sha, str) or SOURCE.fullmatch(expected_source_sha) is None:
        raise ValueError("Missing exact new version source commit")
    camera = require_pinned_native_camera_wheel(camera_receipt, target)
    if output.exists() or output.is_symlink():
        raise ValueError("Do not overwrite prior build artifacts")
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="ap311-full-macos-") as temp:
        tmp = Path(temp)
        with mount(stable, tmp/"stable"), mount(qa, tmp/"preview"):
            old_app = tmp/"stable/AnythingPlays31.app"
            qa_app = tmp/"preview/AnythingPlays311QA.app"
            if not old_app.is_dir() or not qa_app.is_dir():
                raise ValueError("Cannot combine wrong public and QA Mac app identities")
            app = tmp/"AnythingPlays311QA.app"
            shutil.copytree(qa_app, app, symlinks=True)
            validate_staged_identity(app, channel="v311_candidate")
            old_cores = old_app/"Contents/Resources/cores"
            new_cores = app/"Contents/Resources/cores"
            core_manifest = validate_trial_core_directory(old_cores, ".dylib")
            if (core_manifest.get("total_source_built_core_families") != 11
                    or core_manifest.get("source_built_dolphin") is None
                    or core_manifest.get("source_built_tia") is None):
                raise ValueError("Public 3.1.0 did not contain 11 reviewed core families")
            if any(p.is_symlink() for p in old_cores.rglob("*")):
                raise ValueError("Linked original-source emulator core is unsafe")
            shutil.rmtree(new_cores)
            shutil.copytree(old_cores, new_cores, symlinks=True)
            if validate_trial_core_directory(new_cores, ".dylib") != core_manifest:
                raise ValueError("Native source provenance changed in copied app")
            base_notices = old_app/"Contents/Resources/licenses"
            current_notices = app/"Contents/Resources/licenses"
            ignored = {"PYTHON_DISTRIBUTIONS.json", "THIRD_PARTY_NOTICES.md",
                       "THIRD_PARTY_COMPONENTS.md"}
            for item in base_notices.iterdir():
                if item.is_symlink():
                    raise ValueError("Linked original license notice")
                if item.is_file() and item.name not in ignored:
                    shutil.copy2(item, current_notices/item.name)
            if not (current_notices/"python-distribution-notices").is_dir():
                raise ValueError("The new pygame/SDL source notices are absent")
        with (app/"Contents/Info.plist").open("rb") as stream:
            plist=plistlib.load(stream)
        if (plist.get("CFBundleIdentifier") != "com.anythingplays.private311qa"
                or plist.get("CFBundleShortVersionString") != "3.1.1"
                or plist.get("CFBundleVersion") != "3.1.1"):
            raise ValueError("QA app would overwrite or mislabel public stable")
        verify_bundle(app, "macos", check_native=True)
        subprocess.run(["codesign", "--force", "--sign", "-", str(app)],
                       check=True, timeout=120)
        subprocess.run(["codesign", "--verify", "--verbose=2", str(app)],
                       check=True, timeout=60)
        verify_bundle(app, "macos", check_native=True)
        final = output/qa_name
        create_disk_image(app, final,
                          volume_name="Anything Plays 3.1.1 Private Full QA")
        with mount(final, tmp/"installed"):
            installed=tmp/"installed"/app.name
            if not installed.is_dir():
                raise ValueError("Final Mac DMG is not installable")
            # Dynamic loading from mounted DMG can make detach fail;
            # complete native verification was performed on the copied app.
            verify_bundle(installed, "macos", check_native=False)
            if validate_trial_core_directory(installed/"Contents/Resources/cores",
                                             ".dylib") != core_manifest:
                raise ValueError("Signed DMG changed original 11-core bytes")
            validate_staged_identity(installed, channel="v311_candidate")
            audit = inspect_bundle(installed, target)
        (output/"SDL_RUNTIME_AUDIT.json").write_text(
            json.dumps(audit, indent=2)+"\n", "utf-8")
        report = {
            "schema_version": 1, "status": STATUS_FULL,
            "target": target, "installer": qa_name,
            "sha256": digest(final), "size_bytes": final.stat().st_size,
            "old_stable_sha256": digest(stable),
            "new_source_sha256": digest(qa),
            "sourcebuilt_ffmpeg_off_camera_wheel_sha256": camera["native_wheel_sha256"],
            "new_source_revision": expected_source_sha,
            "version": "3.1.1", "identity_channel": "v311_candidate",
            "settings_namespace": "anything-plays-311-candidate",
            "native_core_count": 11, "console_profiles": 18,
            "original_core_families": core_manifest["total_source_built_core_families"],
            "sdl_audit": "SDL_RUNTIME_AUDIT.json",
            "adhoc_signed": True, "notarized": False,
            "public_release_approved": False,
            "physical_controller_tested": False,
            "full_four_platform_311_verified": False,
        }
        (output/"V311_FULL_MACOS_QA_RECEIPT.json").write_text(
            json.dumps(report, indent=2)+"\n", "utf-8")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--arch", choices=("arm64","x64"), required=True)
    for key in ("stable", "qa", "checksums", "source-receipt", "camera-receipt",
                "expected-source-sha", "output"):
        p.add_argument("--"+key, required=True,
                       type=str if key=="expected-source-sha" else Path)
    a = p.parse_args()
    report=build(a.arch,a.stable,a.qa,a.checksums,a.source_receipt,
                 a.camera_receipt,a.expected_source_sha,a.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
