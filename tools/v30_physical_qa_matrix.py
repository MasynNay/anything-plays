"""Offline reconciliation of four owner-reported physical 3.0 QA evidence packets.

This tool requires the *actual* four installer bytes to generate a target SHA
catalog, then checks all four private owner-reported QA JSON/checksum pairs.
Even 600/600 self-reported passes NEVER grant independent hardware review,
third-party redistribution rights, or public release approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from tools.v30_physical_qa import (
    ANSWERS, CONSOLE_CHECKS, HOST_CHECKS, TARGETS, SHA256, COMMIT,
    load_report, sha_file, validate_report,
)

CATALOG_STATUS = "REVIEWER-HASHED-FOUR-OS-INSTALLERS-UNAPPROVED"
SUMMARY_STATUS = "FOUR-OS-OWNER-QA-RECONCILED-UNREVIEWED"
REPORT_NAME = "V30_PHYSICAL_QA_OWNER_REPORTED_UNREVIEWED.json"
SUMMARY_NAME = "V30_FOUR_OS_PHYSICAL_QA_REVIEW_UNAPPROVED.json"
HASHFILE = "SHA256SUMS.txt"
CLEAN_NAME = re.compile(r"[A-Za-z0-9_.() ~-]+\.(?:exe|deb|dmg)\Z")
TARGET_SUFFIX = {
    "windows-x64": ".exe",
    "linux-x64": ".deb",
    "macos-arm64": ".dmg",
    "macos-x86_64": ".dmg",
}


def _safe_file(path):
    path = Path(path).expanduser()
    if not path.is_file() or path.is_symlink() or path.stat().st_size <= 0:
        raise ValueError("Expected nonempty regular local reviewer file")
    return path


def _ensure_private_name(name, target):
    if (not isinstance(name, str) or len(name) > 180
            or not CLEAN_NAME.fullmatch(name)
            or not name.endswith(TARGET_SUFFIX[target])):
        raise ValueError(f"{target}: unsafe or mismatched installer basename")
    return name


def hash_four_installers(source_revision, installers):
    """Hash actual bytes; no game files or local filesystem paths in output."""
    if not isinstance(source_revision, str) or not COMMIT.fullmatch(source_revision):
        raise ValueError("Installer catalog requires a full source Git revision")
    if not isinstance(installers, dict) or set(installers) != TARGETS:
        raise ValueError("Hash exactly four installer files, one per native architecture")
    targets = {}
    for target in sorted(TARGETS):
        file = _safe_file(installers[target])
        _ensure_private_name(file.name, target)
        targets[target] = {
            "installer_filename": file.name,
            "installer_sha256": sha_file(file),
            "installer_size_bytes": file.stat().st_size,
        }
    return {
        "schema_version": 1,
        "status": CATALOG_STATUS,
        "source_revision": source_revision,
        "targets": targets,
        "binary_to_source_independently_reviewed": False,
        "external_license_rights_approved": False,
        "public_release_approved": False,
    }


def validate_catalog(catalog):
    if (not isinstance(catalog, dict)
            or set(catalog) != {
                "schema_version", "status", "source_revision", "targets",
                "binary_to_source_independently_reviewed",
                "external_license_rights_approved", "public_release_approved",
            }
            or catalog["schema_version"] != 1
            or catalog["status"] != CATALOG_STATUS
            or not isinstance(catalog.get("source_revision"), str)
            or not COMMIT.fullmatch(catalog["source_revision"])
            or not isinstance(catalog.get("targets"), dict)
            or set(catalog["targets"]) != TARGETS):
        raise ValueError("Incorrect four-installer immutable review catalog schema")
    for field in ("binary_to_source_independently_reviewed",
                  "external_license_rights_approved", "public_release_approved"):
        if catalog.get(field) is not False:
            raise ValueError(f"Catalog cannot assert unverified approval: {field}")
    for target, row in catalog["targets"].items():
        if (not isinstance(row, dict)
                or set(row) != {
                    "installer_filename", "installer_sha256", "installer_size_bytes"}
                or not isinstance(row.get("installer_sha256"), str)
                or not SHA256.fullmatch(row["installer_sha256"])
                or type(row.get("installer_size_bytes")) is not int
                or row["installer_size_bytes"] <= 0):
            raise ValueError(f"{target}: invalid installer catalog fingerprint")
        _ensure_private_name(row.get("installer_filename"), target)
    return catalog


def _read_verified_qa_packet(folder):
    folder = Path(folder)
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("Missing, unsafe physical QA packet directory")
    if {x.name for x in folder.iterdir()} != {REPORT_NAME, HASHFILE}:
        raise ValueError("Expected exactly one private QA JSON plus SHA256SUMS per OS")
    report_file = _safe_file(folder / REPORT_NAME)
    checksums = _safe_file(folder / HASHFILE).read_bytes()
    expected = f"{sha_file(report_file)}  {REPORT_NAME}\n".encode("ascii")
    if checksums != expected:
        raise ValueError("Owner QA report has a wrong or altered SHA256SUMS")
    report = load_report(report_file)
    return report, hashlib.sha256(report_file.read_bytes()).hexdigest()


def reconcile(catalog, packets_directory):
    """Summarize actual, manually reported results; NEVER assert release rights."""
    validate_catalog(catalog)
    root = Path(packets_directory)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Expected one local directory with four QA evidence packets")
    if {p.name for p in root.iterdir()} != TARGETS:
        raise ValueError("Must provide exactly four distinct platform QA packets")
    targets = {}
    total = {name: 0 for name in sorted(ANSWERS)}
    for target in sorted(TARGETS):
        report, report_sha = _read_verified_qa_packet(root / target)
        if report["target"] != target:
            raise ValueError(f"{target}: QA report is for the wrong machine")
        if report["source_revision"] != catalog["source_revision"]:
            raise ValueError(f"{target}: physical QA belongs to another source revision")
        expected = catalog["targets"][target]
        for field in ("installer_filename", "installer_sha256",
                      "installer_size_bytes"):
            if report[field] != expected[field]:
                raise ValueError(
                    f"{target}: tested installer differs from independently hashed "
                    f"reviewer catalog ({field})"
                )
        values = list(report["host_checks"].values())
        values += [
            row[check]
            for row in report["console_checks"].values()
            for check in CONSOLE_CHECKS
        ]
        if len(values) != len(HOST_CHECKS) + 18 * len(CONSOLE_CHECKS):
            raise ValueError(f"{target}: incomplete actual 18-console inventory")
        count = {key: values.count(key) for key in sorted(ANSWERS)}
        for key in count:
            total[key] += count[key]
        blockers = [
            f"host/{check}={value}"
            for check, value in report["host_checks"].items()
            if value != "pass"
        ]
        blockers.extend(
            f"{system}/{check}={value}"
            for system, row in report["console_checks"].items()
            for check, value in row.items()
            if value != "pass"
        )
        targets[target] = {
            "installer_sha256": report["installer_sha256"],
            "installer_size_bytes": report["installer_size_bytes"],
            "owner_evidence_json_sha256": report_sha,
            "total_required_observations": len(values),
            "counts": count,
            "outstanding_manual_checks": blockers,
            "all_owner_observations_pass": not blockers,
            "independently_verified_on_hardware": False,
        }
    complete = total.get("pass") == 4 * (len(HOST_CHECKS) + 18 * len(CONSOLE_CHECKS))
    result = {
        "schema_version": 1,
        "status": SUMMARY_STATUS,
        "source_revision": catalog["source_revision"],
        "platform_count": len(targets),
        "console_profiles_per_platform": 18,
        "required_observations": 600,
        "counts": total,
        "targets": targets,
        "owner_reports_complete_for_independent_review": complete,
        "owner_reports_are_not_independent_hardware_proof": True,
        "independent_hardware_reviewed": False,
        "source_to_binary_correspondence_reviewed": False,
        "external_license_redistribution_reviewed": False,
        "production_approval": False,
        "public_release_approved": False,
        "no_rom_names_paths_saves_or_camera_data_collected": True,
    }
    if sum(total.values()) != 600 or len(targets) != 4:
        raise ValueError("Four-OS QA reviewer summary did not cover all 600 checks")
    return result


def save_record(document, path):
    path = Path(path).expanduser()
    if path.is_symlink() or path.exists():
        raise ValueError("New catalog destination required (never overwrite)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(document, indent=2, sort_keys=True)
                      + "\n").encode("utf-8"))
    return path


def export_summary(summary, output):
    output = Path(output).expanduser()
    if (output.is_symlink() or
            (output.exists()
             and (not output.is_dir() or any(output.iterdir())))):
        raise ValueError("Summary destination must be a new or empty directory")
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / SUMMARY_NAME
    report_path.write_bytes(
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    (output / HASHFILE).write_bytes(
        f"{sha_file(report_path)}  {SUMMARY_NAME}\n".encode("ascii"))
    return report_path


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    catalog_p = sub.add_parser("hash-installers",
                               help="Hash four ORIGINAL local preview/production installer files")
    catalog_p.add_argument("--source-commit", required=True)
    catalog_p.add_argument("--installer", action="append", required=True,
                           help="target=/actual/local/path, repeat once per OS")
    catalog_p.add_argument("--out", type=Path, required=True)
    review_p = sub.add_parser("reconcile",
                              help="Check all four owner QA packets against actual installer hashes")
    review_p.add_argument("--catalog", type=Path, required=True)
    review_p.add_argument("--packets", type=Path, required=True)
    review_p.add_argument("--output", type=Path, required=True)
    review_p.add_argument("--require-complete", action="store_true",
                          help="Fail if any of the 600 human observations is missing or failed")
    args = p.parse_args(argv)
    try:
        if args.command == "hash-installers":
            rows = {}
            for item in args.installer:
                target, sep, local = item.partition("=")
                if sep != "=" or target not in TARGETS or target in rows or not local:
                    raise ValueError("Each of four --installer arguments must be unique target=path")
                rows[target] = local
            report = hash_four_installers(args.source_commit, rows)
            save_record(report, args.out)
            print("Hashed four genuine local installers; source/legal/public approval NOT granted.")
            return 0
        catalog = validate_catalog(json.loads(args.catalog.read_text("utf-8")))
        report = reconcile(catalog, args.packets)
        export_summary(report, args.output)
        print("FOUR-OS PHYSICAL QA SELF-REPORT:",
              report["counts"]["pass"], "/600 owner observations pass;",
              report["counts"]["fail"], "fail;",
              report["counts"]["not-tested"], "unperformed; "
              "independent release/rights approval ALWAYS FALSE")
        if args.require_complete and not report["owner_reports_complete_for_independent_review"]:
            print("STILL BLOCKED: one or more owner observations missing/failed.")
            return 1
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as err:
        p.exit(1, f"FOUR-OS PHYSICAL QA RECONCILIATION REJECTED: {err}\n")


if __name__ == "__main__":
    sys.exit(main())
