"""Assemble an UNRELEASED 3.2 full-core, stable-identity Linux upgrade QA.

The app comes from exact 3.2 private stable-upgrade source QA. Only the
published checksum-verified 3.1.1 core bytes and required source notices
are reused. No public release or user installation is ever authorized.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from tools.stage_v32_full_linux import (
    checked_file, full_inventory, no_links, sha256,
)
from tools.verify_v31_rc import validate_staged_identity
from tools.verify_v32_stable_upgrade_source import (
    NAMES, STATUS as SOURCE_STATUS, verify as verify_source,
)

BASELINE = "anything-plays-31_3.1.1_amd64.deb"
SOURCE = NAMES["linux-x64"]
FULL = "anything-plays-31_3.2.0~fullupgradeqa1_amd64.deb"
STATUS = "PRIVATE_3_2_FULL_CORE_STABLE_LINUX_UPGRADE_QA_NOT_RELEASE"


def source_gate(stable, source, checksums, receipt, sha):
    if type(sha) is not str or re.fullmatch("[0-9a-f]{40}", sha) is None:
        raise ValueError("Exact 3.2 Git SHA required")
    stable = checked_file(stable, BASELINE)
    source = checked_file(source, SOURCE)
    checksums, receipt = Path(checksums), Path(receipt)
    if (checksums.name != "SHA256SUMS.txt" or not checksums.is_file()
            or checksums.is_symlink()
            or not 0 < checksums.stat().st_size <= 16384
            or not receipt.is_file() or receipt.is_symlink()
            or not 0 < receipt.stat().st_size <= 65536):
        raise ValueError("Missing or unsafe original release/checksum evidence")
    if sha256(stable) + "  " + BASELINE not in checksums.read_text("utf-8").splitlines():
        raise ValueError("Published 3.1.1 Linux installer failed immutable SHA256")
    data = json.loads(receipt.read_text("utf-8"))
    required = {
        "schema_version": 1, "status": SOURCE_STATUS,
        "target": "linux-x64", "source_revision": sha,
        "installer": SOURCE, "installer_sha256": sha256(source),
        "installer_bytes": source.stat().st_size,
        "identity_channel": "v32_stable_candidate",
        "stable_settings_namespace": "anything-plays-31",
        "stable_package_identity_matches_311": True,
        "native_core_count": 1,
        "full_native_release_tested": False,
        "real_user_settings_migration_tested": False,
        "physical_hardware_tested": False,
        "redistribution_approved": False,
        "public_release_approved": False,
    }
    if (type(data) is not dict
            or set(data) != set(required) | {"identity_marker"}
            or not isinstance(data.get("identity_marker"), str)
            or not data["identity_marker"].endswith("v31_build_identity.json")
            or any(type(data.get(key)) is not type(value) or data[key] != value
                   for key, value in required.items())):
        raise ValueError("Source-stage receipt mismatch; refuse untrusted 3.2 app")
    return stable, source


def assemble(stable, source, checksums, receipt, sha, output):
    if (os.environ.get("AP_V32_STABLE_CANDIDATE") != "1"
            or os.environ.get("AP_V30_MINIMAL_CORE_BUILD") != "1"
            or os.environ.get("AP_RELEASE_BUILD") == "1"
            or os.environ.get("AP_V30_APPROVED_RELEASE") == "1"
            or os.environ.get("AP_V32_PREVIEW_BUILD") == "1"):
        raise ValueError("Only the private nonrelease stable-upgrade QA is allowed")
    stable, source = source_gate(stable, source, checksums, receipt, sha)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Cannot overwrite an existing test candidate")
    with tempfile.TemporaryDirectory(prefix="ap32-stable-full-linux-") as temp:
        root = Path(temp)
        old_tree, newer_tree = root / "public-311", root / "new-320"
        subprocess.run(["dpkg-deb", "-x", str(stable), str(old_tree)],
                       check=True, timeout=120)
        subprocess.run(["dpkg-deb", "-R", str(source), str(newer_tree)],
                       check=True, timeout=120)
        old = old_tree / "opt/anything-plays-31"
        candidate = newer_tree / "opt/anything-plays-31"
        native = old / "cores"
        new_native = candidate / "cores"
        original = full_inventory(native)
        no_links(old / "licenses")
        no_links(candidate / "licenses")
        marker = validate_staged_identity(candidate, channel="v32_stable_candidate")
        if not marker:
            raise ValueError("Private stable 3.2 build identity missing")
        # This check also compares actual one-core source package bytes,
        # source SHA and the embedded marker against its build receipt.
        verify_source("linux-x64", source, candidate, sha, checkout_sha=sha)
        no_links(new_native)
        shutil.rmtree(new_native)
        shutil.copytree(native, new_native)
        for file in (old / "licenses").iterdir():
            if file.is_file() and file.name not in {
                "PYTHON_DISTRIBUTIONS.json", "THIRD_PARTY_NOTICES.md",
                "THIRD_PARTY_COMPONENTS.md",
            }:
                shutil.copy2(file, candidate / "licenses" / file.name)
        if full_inventory(new_native) != original:
            raise ValueError("New 3.2 full native bytes differ from public 3.1.1")
        control = newer_tree / "DEBIAN/control"
        info = control.read_text("utf-8")
        old_version = "Version: 3.2.0~upgradeqa1\n"
        if (info.count(old_version) != 1
                or "Package: anything-plays-31\n" not in info):
            raise ValueError("Private source app is not an upgrade of stable 3.1.1")
        control.write_text(info.replace(
            old_version, "Version: 3.2.0~fullupgradeqa1\n"
        ), "utf-8")
        output.mkdir(parents=True, exist_ok=False)
        installer = output / FULL
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group",
                        str(newer_tree), str(installer)],
                       check=True, timeout=240)
        extracted = root / "actual-extracted-upgrade"
        subprocess.run(["dpkg-deb", "-x", str(installer), str(extracted)],
                       check=True, timeout=120)
        installed = extracted / "opt/anything-plays-31"
        validate_staged_identity(installed, channel="v32_stable_candidate")
        if full_inventory(installed / "cores") != original:
            raise ValueError("Repacked installed full-native core bytes changed")
        for field, value in (("Package", "anything-plays-31"),
                             ("Version", "3.2.0~fullupgradeqa1")):
            found = subprocess.check_output(
                ["dpkg-deb", "-f", str(installer), field],
                text=True, timeout=25,
            ).strip()
            if found != value:
                raise ValueError("Repackaged Debian upgrade field mismatched " + field)
        report = {
            "schema_version": 1,
            "status": STATUS, "target": "linux-x64",
            "source_revision": sha, "installer": FULL,
            "installer_sha256": sha256(installer),
            "source_3_2_sha256": sha256(source),
            "public_3_1_1_sha256": sha256(stable),
            "native_core_count": 11, "console_profiles": 18,
            "native_core_bytes_preserved": True,
            "same_debian_stable_package": True,
            "stable_settings_namespace": "anything-plays-31",
            "public_release_approved": False,
            "real_user_upgrade_tested": False,
            "physical_hardware_tested": False,
            "redistribution_approved": False,
            "all_retail_games_verified": False,
        }
        (output / "V32_STABLE_FULL_LINUX_QA_RECEIPT.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8"
        )
        return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stable", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--checksums", type=Path, required=True)
    parser.add_argument("--source-receipt", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = assemble(
        args.stable, args.source, args.checksums, args.source_receipt,
        args.source_sha, args.output,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
