"""Stage unreleased full 11-core 3.2 Windows SAME-INSTALL upgrade QA.

Never upload this installer, publish or install it on user machines.
The exact 3.2 source app and immutable public 3.2.0 cores are combined
only within a disposable Windows runner, and the actual Inno output is
unpacked/checked before recording a private receipt.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from tools.assemble_v31_full_windows import unpack, source_app, iscc
from tools.stage_v32_full_windows import full_inventory
from tools.stage_v32_full_linux import checked_file, no_links, sha256
from tools.stage_v33_stable_full_linux import source_gate
from tools.verify_v31_rc import validate_staged_identity
from tools.verify_v33_stable_upgrade_source import NAMES, verify as verify_source

BASELINE = "AnythingPlaysSetup-3.2.0.exe"
SOURCE = NAMES["windows-x64"]
FULL = "AnythingPlaysSetup-3.3.0.exe"
STATUS = "PRIVATE_3_3_FULL_CORE_STABLE_WINDOWS_UPGRADE_QA_NOT_RELEASE"


def checked_windows_source(stable, newer, checksums, receipt, sha):
    stable = checked_file(stable, BASELINE)
    newer = checked_file(newer, SOURCE)
    # The Linux gate validates Linux filenames; verify the corresponding
    # Windows source receipt with the SAME strict reviewed schema.
    from tools.verify_v33_stable_upgrade_source import STATUS as SOURCE_STATUS
    checksums, receipt = Path(checksums), Path(receipt)
    if (checksums.name != "SHA256SUMS.txt" or not checksums.is_file()
            or checksums.is_symlink() or not 0 < checksums.stat().st_size <= 16384
            or not receipt.is_file() or receipt.is_symlink()
            or not 0 < receipt.stat().st_size <= 65536):
        raise ValueError("Missing immutable baseline or source QA evidence")
    if sha256(stable) + "  " + BASELINE not in checksums.read_text("utf-8").splitlines():
        raise ValueError("Original public 3.2.0 Windows setup SHA256 is wrong")
    data = json.loads(receipt.read_text("utf-8"))
    expected = {
        "schema_version": 1, "status": SOURCE_STATUS,
        "target": "windows-x64", "source_revision": sha,
        "installer": SOURCE, "installer_sha256": sha256(newer),
        "installer_bytes": newer.stat().st_size,
        "identity_channel": "v33_stable_candidate",
        "stable_settings_namespace": "anything-plays-31",
        "stable_package_identity_matches_311": True,
        "native_core_count": 1,
        "full_native_release_tested": False,
        "real_user_settings_migration_tested": False,
        "physical_hardware_tested": False,
        "redistribution_approved": False, "public_release_approved": False,
    }
    if (type(data) is not dict
            or set(data) != set(expected) | {"identity_marker"}
            or type(data.get("identity_marker")) is not str
            or not data["identity_marker"].endswith("v31_build_identity.json")
            or any(type(data.get(k)) is not type(v) or data[k] != v
                   for k, v in expected.items())):
        raise ValueError("Untrusted exact-source Windows upgrade receipt")
    return stable, newer


def assemble(stable, source, checksums, receipt, sha, output):
    if (os.getenv("AP_V33_STABLE_CANDIDATE") != "1"
            or os.getenv("AP_V30_MINIMAL_CORE_BUILD") != "1"
            or os.getenv("AP_V33_PREVIEW_BUILD") == "1"
            or os.getenv("AP_RELEASE_BUILD") == "1"
            or os.getenv("AP_V30_APPROVED_RELEASE") == "1"):
        raise ValueError("Private nonrelease 3.2 stable identity is mandatory")
    stable, source = checked_windows_source(
        stable, source, checksums, receipt, sha,
    )
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Refusing to overwrite existing QA output")
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="ap32-stable-windows-") as directory:
        scratch = Path(directory)
        unpack(stable.resolve(), scratch/"old-stable")
        unpack(source.resolve(), scratch/"new-source")
        old = source_app(scratch/"old-stable", "V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json")
        new = source_app(scratch/"new-source", "AnythingPlays.exe")
        validate_staged_identity(new, channel="v33_stable_candidate")
        verify_source("windows-x64", source, new, sha, checkout_sha=sha)
        original = full_inventory(old/"cores")
        no_links(old/"licenses")
        no_links(new/"cores")
        no_links(new/"licenses")
        dest = root/"dist"/"AnythingPlays"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(new, dest, ignore=shutil.ignore_patterns("unins000.*"))
        shutil.rmtree(dest/"cores")
        shutil.copytree(old/"cores", dest/"cores")
        for item in (old/"licenses").iterdir():
            if item.is_file() and item.name not in {
                "PYTHON_DISTRIBUTIONS.json", "THIRD_PARTY_NOTICES.md",
                "THIRD_PARTY_COMPONENTS.md",
            }:
                shutil.copy2(item, dest/"licenses"/item.name)
        if full_inventory(dest/"cores") != original:
            raise ValueError("Staged Windows native source bytes changed")
        validate_staged_identity(dest, channel="v33_stable_candidate")
        version = "3.3.0"
        subprocess.run(
            [iscc(), "/DV33StableFinalBuild=1", "/DAppVersion=" + version,
             str(root/"packaging/installer.iss")],
            cwd=root, check=True, timeout=600,
        )
        produced = root/"release"/FULL
        if not produced.is_file() or produced.is_symlink():
            raise ValueError("Full 3.2 stable-identity Windows Inno output missing")
        unpack(produced.resolve(), scratch/"installed")
        installed = source_app(
            scratch/"installed", "V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json",
        )
        validate_staged_identity(installed, channel="v33_stable_candidate")
        if full_inventory(installed/"cores") != original:
            raise ValueError("Installed Inno setup changed original 11 native cores")
        output.mkdir(parents=True, exist_ok=False)
        final = output/FULL
        shutil.copy2(produced, final)
        result = {
            "schema_version": 1,
            "status": STATUS, "target": "windows-x64",
            "source_revision": sha, "installer": FULL,
            "installer_sha256": sha256(final),
            "source_3_3_sha256": sha256(source),
            "public_3_2_0_sha256": sha256(stable),
            "native_core_count": 11, "console_profiles": 18,
            "native_core_bytes_preserved": True,
            "stable_windows_inno_identity": True,
            "stable_settings_namespace": "anything-plays-31",
            "public_release_approved": False,
            "real_user_upgrade_tested": False,
            "physical_hardware_tested": False,
            "redistribution_approved": False,
            "all_retail_games_verified": False,
        }
        (output/"V33_STABLE_FULL_WINDOWS_QA_RECEIPT.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", "utf-8"
        )
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("stable", "source", "checksums", "source_receipt", "source_sha", "output"):
        parser.add_argument("--" + name.replace("_", "-"), required=True,
                            type=Path if name not in ("source_sha",) else str)
    args = parser.parse_args(argv)
    receipt = assemble(args.stable, args.source, args.checksums,
                       args.source_receipt, args.source_sha, args.output)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
