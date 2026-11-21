"""Private 3.3 full-native Windows QA staged from published 3.2.

Repack the separately installed candidate without publishing or modifying
stable 3.2. Verify original 11-core native payload, hashes, identity, source
notices and exact installer bytes after real Inno setup extraction.
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
from tools.v33_candidate_verify import TARGETS
from tools.stage_v33_full_linux import require_private_stage

BASELINE = "AnythingPlaysSetup-3.2.0.exe"
SOURCE = TARGETS["windows-x64"]
FULL = "AnythingPlaysSetup-3.3.0-fullqa1.exe"
STATUS = "PRIVATE_V33_WINDOWS_FULL_11_CORE_NATIVE_QA_NOT_RELEASE"


def source_gate(stable, candidate, sums, receipt, revision):
    if type(revision) is not str or not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Exact 3.3 source SHA required")
    stable = checked_file(stable, BASELINE)
    candidate = checked_file(candidate, SOURCE)
    sums, receipt = Path(sums), Path(receipt)
    for path, name, size in (
        (sums, "SHA256SUMS.txt", 16384),
        (receipt, "V33_CANDIDATE_QA_RECEIPT.json", 65536),
    ):
        if (path.name != name or not path.is_file() or path.is_symlink()
                or path.stat().st_nlink != 1
                or not 0 < path.stat().st_size <= size):
            raise ValueError("Missing or untrusted public/QA verification file")
    if sha256(stable) + "  " + BASELINE not in sums.read_text("utf-8").splitlines():
        raise ValueError("Published 3.2 Windows package failed SHA256")
    record = json.loads(receipt.read_text("utf-8"))
    expected = {
        "format": "anything-plays-v33-owner-qa",
        "target": "windows-x64",
        "source_sha": revision,
        "channel": "v33_candidate",
        "version": "3.3.0-qa",
        "settings_namespace": "anything-plays-33-candidate",
        "installer_filename": SOURCE,
        "installer_sha256": sha256(candidate),
        "bundled_core_names": ["mgba_libretro.dll"],
        "bundled_core_count": 1,
        "public_release_approved": False,
        "hardware_input_tested": False,
        "physical_camera_tested": False,
        "gamecube_bundled": False,
        "full_18_console_gameplay_tested": False,
        "installer_fully_tested_on_real_host": False,
    }
    if type(record) is not dict or record != expected:
        raise ValueError("Current Windows source receipt failed identity scope")
    return stable, candidate


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
    require_private_stage()
    stable, preview = source_gate(stable, preview, sums, receipt, revision)
    output = Path(output)
    if output.is_symlink() or output.exists():
        raise ValueError("Never overwrite another package or installed Windows app")
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="ap33-full-windows-") as td:
        temp = Path(td)
        unpack(stable, temp/"stable")
        unpack(preview, temp/"minimal")
        old = source_app(temp/"stable", "AnythingPlays.exe")
        new = source_app(temp/"minimal", "AnythingPlays.exe")
        original = full_inventory(old/"cores")
        no_links(old/"licenses")
        validate_staged_identity(new, channel="v33_candidate")
        if sorted(p.name for p in (new / "cores").glob("*_libretro.dll")) != [
                "mgba_libretro.dll"]:
            raise ValueError("Current 3.3 QA installer is not mGBA only")
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
        validate_staged_identity(dest, channel="v33_candidate")
        subprocess.run([iscc(), "/DV33CandidateBuild=1",
                        "/DAppVersion=3.3.0-fullqa1",
                        str(root/"packaging/installer.iss")],
                       cwd=root, check=True, timeout=600)
        produced = root/"release"/FULL
        if not produced.is_file() or produced.is_symlink():
            raise ValueError("Inno did not create 3.3 private full QA installer")
        unpack(produced, temp/"installed")
        installed = source_app(temp/"installed", "AnythingPlays.exe")
        validate_staged_identity(installed, channel="v33_candidate")
        if full_inventory(installed/"cores") != original:
            raise ValueError("Installed Windows QA native cores differ from published originals")
        # The QA Inno AppId is distinct from stable 3.2; never replace it.
        if installed.name == "Anything Plays 3.1" or "anything-plays-31" in str(installed):
            raise ValueError("Private 3.3 candidate appears to replace a stable app")
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
            "private_3_3_mgba_sha256": sha256(preview),
            "published_3_2_sha256": sha256(stable),
            "native_core_count": 11,
            "console_profiles": 18,
            "native_core_bytes_preserved": True,
            "settings_namespace": "anything-plays-33-candidate",
            "public_release_approved": False,
            "real_gameplay_tested": False,
            "physical_camera_tested": False,
            "physical_controller_tested": False,
            "all_18_consoles_gameplay_verified": False,
            "redistribution_audit_complete": False,
        }
        (output/"V33_FULL_WINDOWS_QA_RECEIPT.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
        (output/"SHA256SUMS.txt").write_text(
            report["installer_sha256"] + "  " + FULL + "\n", encoding="utf-8",
        )
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
