"""Build private full-native-core 3.2 Windows QA from published 3.1.1.

No arbitrary emulator downloads, real games, public release or stable
replacement. The 3.2 source-built app is retained byte-for-byte; only the
checksum-verified original native cores and their notices are reused.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from anything_plays.v30_gpl_trial import (
    enable_windows_trial_runtime, validate_trial_core_directory,
)
from tools.assemble_v31_full_windows import unpack, source_app, iscc
from tools.stage_v32_full_linux import sha256, checked_file, no_links
from tools.verify_v31_rc import validate_staged_identity
from tools.verify_v32_preview import FILES, verify as verify_minimal

BASELINE = "AnythingPlaysSetup-3.1.1.exe"
FULL = "AnythingPlaysSetup-3.2.0-fullqa1.exe"
STATUS = "PRIVATE_V32_WINDOWS_FULL_11_CORE_NATIVE_QA_NOT_RELEASE"


def source_gate(stable, preview, sums, receipt, revision):
    if not re.fullmatch(r"[a-f0-9]{40}", str(revision)):
        raise ValueError("Expected exact 3.2 Git source revision")
    stable = checked_file(stable, BASELINE)
    preview = checked_file(preview, FILES["windows-x64"])
    sums, receipt = Path(sums), Path(receipt)
    if (sums.name != "SHA256SUMS.txt" or not sums.is_file()
            or sums.is_symlink() or sums.stat().st_size > 16384
            or not receipt.is_file() or receipt.is_symlink()
            or receipt.stat().st_size > 32768):
        raise ValueError("Missing or unsafe public checksum / 3.2 receipt")
    if sha256(stable) + "  " + BASELINE not in sums.read_text("utf-8").splitlines():
        raise ValueError("Published 3.1.1 Windows installer checksum mismatch")
    record = json.loads(receipt.read_text("utf-8"))
    if not isinstance(record, dict):
        raise ValueError("Private source receipt is not an object")
    checks = {
        "status": "UNRELEASED_PRIVATE_QA_ONLY",
        "channel": "v32_preview",
        "version": "3.2.0-preview1",
        "target": "windows-x64",
        "installer": FILES["windows-x64"],
        "source_revision": revision,
        "sha256": sha256(preview),
        "size_bytes": preview.stat().st_size,
        "settings_namespace": "anything-plays-32-preview",
        "bundled_console_profiles": ["gb", "gbc", "gba"],
        "bundled_core_names": ["mgba"],
        "public_release_approved": False,
        "all_18_consoles_verified": False,
    }
    if any(type(record.get(key)) is not type(value) or record[key] != value
           for key, value in checks.items()):
        raise ValueError("Incorrect source-built minimal 3.2 Windows receipt")
    return stable, preview


def full_inventory(cores):
    no_links(cores)
    enable_windows_trial_runtime(cores)
    record = validate_trial_core_directory(cores, ".dll")
    if (record.get("native_core_count") != 11
            or record.get("all_console_profiles") != 18
            or record.get("total_source_built_core_families") != 11
            or not record.get("source_built_dolphin")
            or not record.get("source_built_tia")
            or len(list(cores.glob("*_libretro.dll"))) != 11):
        raise ValueError("Missing reviewed 11 original-source Windows emulator cores")
    return record


def assemble(stable, preview, sums, receipt, revision, output):
    if (os.environ.get("AP_V32_PREVIEW_BUILD") != "1"
            or os.environ.get("AP_RELEASE_BUILD") == "1"
            or os.environ.get("AP_V30_APPROVED_RELEASE") == "1"):
        raise ValueError("Windows 3.2 full QA requires isolated non-release flags")
    stable, preview = source_gate(stable, preview, sums, receipt, revision)
    output = Path(output)
    if output.is_symlink() or output.exists():
        raise ValueError("Never overwrite another package or installed Windows app")
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="ap32-full-windows-") as td:
        temp = Path(td)
        unpack(stable, temp/"stable")
        unpack(preview, temp/"minimal")
        old = source_app(temp/"stable", "V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json")
        new = source_app(temp/"minimal", "AnythingPlays.exe")
        original = full_inventory(old/"cores")
        no_links(old/"licenses")
        validate_staged_identity(new, channel="v32_preview")
        verify_minimal("windows-x64", preview, revision, bundle=new)
        no_links(new/"cores")
        dest = root/"dist"/"AnythingPlays"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(new, dest, ignore=shutil.ignore_patterns("unins000.*"))
        shutil.rmtree(dest/"cores")
        shutil.copytree(old/"cores", dest/"cores")
        no_links(dest/"licenses")
        for item in (old/"licenses").iterdir():
            if item.is_file() and item.name not in {
                    "PYTHON_DISTRIBUTIONS.json", "THIRD_PARTY_NOTICES.md",
                    "THIRD_PARTY_COMPONENTS.md"}:
                shutil.copy2(item, dest/"licenses"/item.name)
        if full_inventory(dest/"cores") != original:
            raise ValueError("Windows source-built core bytes changed during QA stage")
        validate_staged_identity(dest, channel="v32_preview")
        subprocess.run([iscc(), "/DV32PreviewBuild=1",
                        "/DAppVersion=3.2.0-fullqa1",
                        str(root/"packaging/installer.iss")],
                       cwd=root, check=True, timeout=600)
        produced = root/"release"/FULL
        if not produced.is_file() or produced.is_symlink():
            raise ValueError("Inno did not create the dedicated 3.2 full QA EXE")
        unpack(produced, temp/"installed")
        installed = source_app(temp/"installed", "V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json")
        validate_staged_identity(installed, channel="v32_preview")
        if full_inventory(installed/"cores") != original:
            raise ValueError("Installed Windows QA native cores differ from published originals")
        # Keep the different 3.2 preview AppId/installation identity. This
        # application must never claim to update the public 3.1.1 installation.
        if installed.name == "Anything Plays 3.1" or "anything-plays-31" in str(installed):
            raise ValueError("Private 3.2 candidate appears to replace a stable app")
        output.mkdir(parents=True, exist_ok=False)
        target = output/FULL
        shutil.copy2(produced, target)
        report = {
            "schema_version": 1,
            "status": STATUS,
            "target": "windows-x64",
            "installer": FULL,
            "installer_sha256": sha256(target),
            "source_revision": revision,
            "source_3_2_preview_sha256": sha256(preview),
            "published_3_1_1_sha256": sha256(stable),
            "native_core_count": 11,
            "console_profiles": 18,
            "native_core_bytes_preserved": True,
            "settings_namespace": "anything-plays-32-preview",
            "public_release_approved": False,
            "real_gameplay_tested": False,
            "physical_camera_tested": False,
            "physical_controller_tested": False,
            "all_18_consoles_gameplay_verified": False,
        }
        (output/"V32_FULL_WINDOWS_QA_RECEIPT.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
        return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stable", type=Path, required=True)
    p.add_argument("--preview", type=Path, required=True)
    p.add_argument("--checksums", type=Path, required=True)
    p.add_argument("--source-receipt", type=Path, required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(assemble(
        a.stable, a.preview, a.checksums,
        a.source_receipt, a.source_sha, a.output,
    ), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
