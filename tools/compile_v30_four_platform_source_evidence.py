"""Consolidate four real 11-source offline installer CI proofs without granting rights.

The full matrix independently builds and checks each installed native SHA.
This step assembles the four successful install reports and original Dolphin
source compiler records into a deterministic reviewer packet. It carries no
emulator binaries, ROMs or automatically asserted legal permissions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from anything_plays.v30_approved_core_map import ELEVEN_EXPECTED, ELEVEN_REPOSITORIES

RUN_ID = re.compile(r"[1-9][0-9]*\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
TARGETS = {
    "windows-x64": "windows-x86_64",
    "linux-x64": "linux-x86_64",
    "macos-arm64": "macos-arm64",
    "macos-x64": "macos-x86_64",
}
ARTIFACT_PREFIX = "AnythingPlays-3.0-ELEVEN-SOURCE-CORE-INSTALLED-"
ARTIFACT_SUFFIX = "-UNAPPROVED"
INSTALLED = "INSTALLED_GPL_ALTERNATIVE_PROVENANCE_UNAPPROVED.json"
STAGED = "ORIGINAL_11_SOURCE_BUILT_STAGING_UNAPPROVED.json"
STAGING_STATUS = "UNAPPROVED-ELEVEN-ORIGINAL-SOURCE-FAMILIES-NO-BUILDBOT-DOLPHIN"
INSTALL_STATUS = "UNAPPROVED-OFFLINE-INSTALLER-GPL-ALTERNATIVE-REAL-4OS"


def _read_small_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError(f"Missing or unsafe source evidence: {path.name}")
    data = json.loads(path.read_text("utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid source evidence JSON: {path.name}")
    return data


def _hash(value: object, label: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ValueError(f"Invalid actual installed SHA256: {label}")
    return value


def consolidate_evidence(artifacts_dir: Path, run_id: str) -> dict:
    """Accept only four exact matrix reports and authentic Dolphin source proof."""
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError("Successful source build GitHub Actions run ID required")
    root = Path(artifacts_dir)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Evidence download root is absent or unsafe")
    expected_folders = {
        ARTIFACT_PREFIX + target + ARTIFACT_SUFFIX for target in TARGETS
    }
    actual_folders = {p.name for p in root.iterdir()}
    if actual_folders != expected_folders:
        raise ValueError("Exactly four original-source core installation artifacts required")
    targets = {}
    for target, lock_target in TARGETS.items():
        folder = root / (ARTIFACT_PREFIX + target + ARTIFACT_SUFFIX)
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError(f"Unsafe source evidence folder: {target}")
        installed = _read_small_json(folder / INSTALLED)
        staged = _read_small_json(folder / STAGED)
        expected_installed = {
            "target": target,
            "status": INSTALL_STATUS,
            "installed_core_count": 11,
            "console_profiles": 18,
            "dolphin_sys_bundled": True,
            "source_provenance_recorded": True,
            "all_eleven_original_source_families_verified": True,
            "physical_hardware_acceptance": False,
            "legal_review_and_redistribution_approved": False,
            "unapproved_installer_uploaded": False,
        }
        if any(installed.get(key) != expected for key, expected in expected_installed.items()):
            raise ValueError(f"{target}: bad installed 11-source-core evidence")
        if (staged.get("status") != STAGING_STATUS or staged.get("target") != target
                or staged.get("native_core_count") != 11
                or staged.get("source_built_families") != 11
                or staged.get("old_buildbot_dolphin_excluded") is not True
                or staged.get("public_binary_distribution_approved") is not False):
            raise ValueError(f"{target}: source-built Dolphin staging not verified")
        digest_map = installed.get("actual_core_sha256")
        if not isinstance(digest_map, dict) or set(digest_map) != set(ELEVEN_EXPECTED):
            raise ValueError(f"{target}: 11 exact source-built native cores required")
        dolphin = staged.get("source_built_dolphin")
        if not isinstance(dolphin, dict) or any((
            dolphin.get("source_commit") != ELEVEN_EXPECTED["dolphin"],
            dolphin.get("source_repository") != ELEVEN_REPOSITORIES["dolphin"],
            dolphin.get("old_unverified_buildbot_replaced") is not True,
            dolphin.get("pristine_unmodified_original_source_compiled") is not True,
            dolphin.get("public_binary_distribution_approved") is not False,
            dolphin.get("direct_original_gitlinks") != 34,
            dolphin.get("nested_original_gitlinks") != 3,
        )):
            raise ValueError(f"{target}: exact original Dolphin source proof missing")
        if _hash(dolphin.get("native_sha256"), target + "/Dolphin") != digest_map["dolphin"]:
            raise ValueError(f"{target}: original-source Dolphin binary does not match installed core")
        if not isinstance(dolphin.get("original_source_notices"), dict) or len(dolphin["original_source_notices"]) != 5:
            raise ValueError(f"{target}: five original Dolphin source notices missing")
        cores = {}
        for name in sorted(ELEVEN_EXPECTED):
            cores[name] = {
                "installed_native_sha256": _hash(digest_map[name], target + "/" + name),
                "upstream_source_repository": ELEVEN_REPOSITORIES[name],
                "pinned_source_commit": ELEVEN_EXPECTED[name],
                "redistribution_license_reviewed": False,
                "complete_corresponding_source_reviewed": False,
            }
        targets[lock_target] = {
            "cores": cores,
            "installed_source_manifest_sha256": _hash(
                installed.get("source_alternative_manifest_sha256"), target + "/manifest"),
            "original_dolphin_native_archive_sha256": _hash(
                dolphin.get("native_archive_sha256"), target + "/Dolphin ZIP"),
            "original_dolphin_compiler_record_sha256": _hash(
                dolphin.get("source_build_report_sha256"), target + "/Dolphin compiler"),
            "dolphin_source_gitlinks_verified": 37,
            "dolphin_sys_bundled": True,
            "physical_hardware_acceptance": False,
            "public_binary_distribution_approved": False,
        }
    return {
        "schema_version": 1,
        "status": "UNAPPROVED-FOUR-PLATFORM-ELEVEN-ORIGINAL-SOURCE-CORE-INVENTORY",
        "source_actions_run_id": int(run_id),
        "native_core_count": 11,
        "system_profile_count": 18,
        "total_platform_native_sha256": 44,
        "source_revisions": dict(sorted(ELEVEN_EXPECTED.items())),
        "corresponding_source_inventory_verified": False,
        "license_compatibility_reviewed": False,
        "public_binary_distribution_approved": False,
        "no_third_party_permission_requested": True,
        "targets": targets,
    }


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--artifacts-dir", type=Path, required=True)
    cli.add_argument("--run-id", required=True)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    report = consolidate_evidence(args.artifacts_dir, args.run_id)
    if args.output.is_symlink() or args.output.exists():
        raise ValueError("Do not overwrite an existing original evidence file")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    print("Recorded 44 verified installed native SHA256s; source/rights approvals remain false.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
