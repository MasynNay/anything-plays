"""Build/verify a private FULL 18-console 3.1.1 Windows QA installer.

Copies the unchanged, SHA256-proven original 11-core payload from published
3.1.0 into a freshly source-built, separately installed 3.1.1 QA app.
The resulting EXE is owner-only QA, NOT a public stable release candidate
until exact four-platform installation/source/notice tests complete.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from anything_plays.v30_gpl_trial import (
    enable_windows_trial_runtime, validate_trial_core_directory,
)
from tools.assemble_v31_full_windows import unpack, source_app, iscc
from tools.verify_v311_source_stage import INSTALLERS, STATUS, digest
from tools.verify_v311_stable_source_stage import (
    INSTALLERS as STABLE_INSTALLERS, STATUS as STABLE_STATUS,
)
from tools.verify_v31_rc import validate_staged_identity
from tools.v311_camera_source_gate import require_pinned_native_camera_wheel
from tools.audit_v31_sdl_runtime import UPSTREAM_LGPL_SHA256, inspect_bundle
from verify_bundle import verify_bundle

TARGET = "windows-x64"
OLD = "AnythingPlaysSetup-3.1.0.exe"
NEW = INSTALLERS[TARGET]
FULL_STATUS = "PRIVATE_3_1_1_FULL_18_WINDOWS_QA_NOT_APPROVED"
STABLE_FULL_STATUS = "PRIVATE_3_1_1_FULL_STABLE_UPDATE_WINDOWS_NOT_APPROVED"


def _check_receipt(receipt, *, source, digest_of_installer, size,
                   stable_update=False):
    expected = {
        "status": STABLE_STATUS if stable_update else STATUS,
        "target": TARGET,
        "installer": STABLE_INSTALLERS[TARGET] if stable_update else NEW,
        "sha256": digest_of_installer,
        "source_revision": source,
        "size_bytes": size, "native_core_count": 1,
        "full_18_console_installer": False,
        "public_release_approved": False,
        "identity_channel": "v311_stable_candidate" if stable_update else "v311_candidate",
        "settings_namespace": "anything-plays-31" if stable_update else "anything-plays-311-candidate",
    }
    for key, value in expected.items():
        if type(receipt.get(key)) is not type(value) or receipt.get(key) != value:
            raise ValueError("Not exact original 3.1.1 Windows source: "+key)


def build(stable, preview, checksums, receipt, camera_receipt,
          expected_source_sha, output, *, stable_update=False):
    stable, preview, checksums, receipt, output = map(
        Path, (stable, preview, checksums, receipt, output))
    new_name = STABLE_INSTALLERS[TARGET] if stable_update else NEW
    channel = "v311_stable_candidate" if stable_update else "v311_candidate"
    namespace = "anything-plays-31" if stable_update else "anything-plays-311-candidate"
    if (stable.name != OLD or preview.name != new_name
            or stable.is_symlink() or preview.is_symlink()
            or not stable.is_file() or not preview.is_file()
            or min(stable.stat().st_size, preview.stat().st_size) <= 1024*1024):
        raise ValueError("Must use actual Windows 3.1.0 stable and 3.1.1 QA EXEs")
    if (digest(stable) + "  " + OLD
            not in checksums.read_text("utf-8").splitlines()):
        raise ValueError("Public stable source EXE hash mismatch")
    from tools.verify_v311_source_stage import SOURCE
    if not isinstance(expected_source_sha, str) or SOURCE.fullmatch(expected_source_sha) is None:
        raise ValueError("Missing exact reviewed source commit")
    meta = json.loads(receipt.read_text("utf-8"))
    _check_receipt(meta, source=expected_source_sha,
                   digest_of_installer=digest(preview),
                   size=preview.stat().st_size, stable_update=stable_update)
    if output.exists() or output.is_symlink():
        raise ValueError("No overwrite of package destination")
    camera = require_pinned_native_camera_wheel(camera_receipt, TARGET)
    root = Path(__file__).resolve().parents[1]
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="ap311-full-windows-") as tmp:
        scratch = Path(tmp)
        unpack(stable, scratch/"stable")
        unpack(preview, scratch/"source")
        old = source_app(scratch/"stable", "V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json")
        new = source_app(scratch/"source", "AnythingPlays.exe")
        validate_staged_identity(new, channel=channel)
        original = validate_trial_core_directory(old/"cores", ".dll")
        if (original.get("total_source_built_core_families") != 11
                or original.get("source_built_dolphin") is None
                or original.get("source_built_tia") is None):
            raise ValueError("Missing reviewed 3.1.0 eleven original native cores")
        if any(p.is_symlink() for p in (old/"cores").rglob("*")):
            raise ValueError("Linked public core payload is not safe to repack")
        target = root/"dist"/"AnythingPlays"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(new, target, ignore=shutil.ignore_patterns("unins000.*"))
        shutil.rmtree(target/"cores")
        shutil.copytree(old/"cores", target/"cores")
        if validate_trial_core_directory(target/"cores", ".dll") != original:
            raise ValueError("Native 3.1.0 core bytes were modified")
        src_licenses, dst_licenses = old/"licenses", target/"licenses"
        if not (dst_licenses/"python-distribution-notices").is_dir():
            raise ValueError("Missing new 3.1.1 native Python runtime notices")
        ignored = {"PYTHON_DISTRIBUTIONS.json", "THIRD_PARTY_NOTICES.md",
                   "THIRD_PARTY_COMPONENTS.md"}
        for path in src_licenses.iterdir():
            if path.is_symlink():
                raise ValueError("Unsafe linked source notice")
            if path.is_file() and path.name not in ignored:
                shutil.copy2(path, dst_licenses/path.name)
        pygame_license = root/"licenses"/"Pygame-CE-LGPL-2.1.txt"
        if digest(pygame_license) != UPSTREAM_LGPL_SHA256:
            raise ValueError("Original pygame LGPL license bytes were altered")
        shutil.copy2(pygame_license, dst_licenses/pygame_license.name)
        enable_windows_trial_runtime(target/"cores")
        verify_bundle(target, "windows", check_native=True)
        subprocess.run([__import__("sys").executable,
                        str(root/"tools/render_v21_icon.py")],
                       cwd=root, check=True, timeout=120)
        subprocess.run([iscc(),
                        "/DV31FinalBuild=1" if stable_update else "/DV311QABuild=1",
                        "/DAppVersion=3.1.1" if stable_update else "/DAppVersion=3.1.1-qa1",
                        str(root/"packaging/installer.iss")],
                       cwd=root, check=True, timeout=600)
        produced = root/"release"/new_name
        if not produced.is_file():
            raise ValueError("Original source-built full 3.1.1 setup not created")
        unpack(produced, scratch/"installed")
        installed = source_app(scratch/"installed", "V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json")
        validate_staged_identity(installed, channel=channel)
        # Keep Windows native DLL loads confined to a disposable process
        # so the runner can delete its scratch install afterward.
        subprocess.run([
            __import__("sys").executable, "-c",
            ("import sys; from pathlib import Path; "
             "from anything_plays.v30_gpl_trial import enable_windows_trial_runtime; "
             "from verify_bundle import verify_bundle; "
             "root=Path(sys.argv[1]); "
             "enable_windows_trial_runtime(root/'cores'); "
             "verify_bundle(root,'windows',check_native=True)"),
            str(installed),
        ], cwd=root, check=True, timeout=120)
        if validate_trial_core_directory(installed/"cores", ".dll") != original:
            raise ValueError("3.1.1 Inno final installer mutated original cores")
        audit = inspect_bundle(installed, TARGET)
        (output/"SDL_RUNTIME_AUDIT.json").write_text(
            json.dumps(audit, indent=2)+"\n", "utf-8")
        final = output/new_name
        shutil.copyfile(produced, final)
        report = {
            "schema_version": 1,
            "status": STABLE_FULL_STATUS if stable_update else FULL_STATUS,
            "target": TARGET,
            "installer": new_name, "sha256": digest(final),
            "size_bytes": final.stat().st_size,
            "old_stable_sha256": digest(stable),
            "new_source_sha256": digest(preview),
            "sourcebuilt_ffmpeg_off_camera_wheel_sha256": camera["native_wheel_sha256"],
            "new_source_revision": expected_source_sha,
            "version": "3.1.1", "identity_channel": channel,
            "settings_namespace": namespace,
            "stable_in_place_update": stable_update,
            "native_core_count": 11, "console_profiles": 18,
            "original_core_families": original["total_source_built_core_families"],
            "sdl_audit": "SDL_RUNTIME_AUDIT.json",
            "public_release_approved": False,
            "physical_controller_tested": False,
            "full_four_platform_311_verified": False,
        }
        (output/"V311_FULL_WINDOWS_QA_RECEIPT.json").write_text(
            json.dumps(report, indent=2)+"\n", "utf-8")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("stable", "qa", "checksums", "source-receipt", "camera-receipt", "expected-source-sha", "output"):
        p.add_argument("--"+key, required=True,
                       type=Path if key != "expected-source-sha" else str)
    p.add_argument("--stable-update", action="store_true",
                   help="Assemble true stable 3.1.1 Inno upgrade, NOT a release")
    a = p.parse_args()
    report = build(a.stable, a.qa, a.checksums, a.source_receipt, a.camera_receipt,
                   a.expected_source_sha, a.output, stable_update=a.stable_update)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
