"""Private, offline 3.0 physical QA checklist with original installer SHA-256.

This records what a *human actually verified* on a physically installed app.
The CLI does not run a game, grant redistribution rights, or modify release
acceptance flags. It never stores ROM filenames/paths, camera images or saves.

Examples:
  python -m tools.v30_physical_qa init --installer path/to/preview.deb --out ~/qa.json
  python -m tools.v30_physical_qa wizard --report ~/qa.json
  python -m tools.v30_physical_qa status --report ~/qa.json
  python -m tools.v30_physical_qa export --report ~/qa.json --output ~/qa-evidence
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile

from anything_plays.systems import SYSTEMS

STATUS = "OWNER-REPORTED-PHYSICAL-QA-UNREVIEWED"
TARGETS = frozenset(("windows-x64", "linux-x64", "macos-arm64", "macos-x86_64"))
CONSOLE_CHECKS = (
    "offline_start", "embedded_video", "audible_audio",
    "keyboard_gameplay", "camera_controls", "rom_change_restart",
    "save_then_reload", "extended_play_stable",
)
HOST_CHECKS = (
    "fresh_installer_clean_install", "no_extra_emulators",
    "native_integrity_match", "camera_device_live",
    "long_run_session_stable", "no_unexpected_network",
)
ANSWERS = frozenset(("pass", "fail", "not-tested"))
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")


REPORT_STATEMENT = (
    "Manual owner-reported observations only. Not automated gameplay proof, "
    "legal clearance, signed installer evidence or authorization for a public release."
)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def detected_target(system=None, machine=None):
    system = (platform.system() if system is None else system).lower()
    machine = (platform.machine() if machine is None else machine).lower()
    if system == "windows" and machine in ("amd64", "x86_64"):
        return "windows-x64"
    if system == "linux" and machine in ("x86_64", "amd64"):
        return "linux-x64"
    if system == "darwin" and machine in ("arm64", "aarch64"):
        return "macos-arm64"
    if system == "darwin" and machine == "x86_64":
        return "macos-x86_64"
    raise ValueError(f"Unsupported physical 3.0 QA host: {system}/{machine}")


def sha_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _output(path):
    path = Path(path).expanduser()
    if path.is_symlink():
        raise ValueError("QA file must never be a symlink")
    return path


def create_report(installer, *, commit, target=None):
    installer = _output(installer)
    if not installer.is_file() or installer.stat().st_size <= 0:
        raise ValueError("A real local installer file is required")
    if not COMMIT.fullmatch(commit):
        raise ValueError("Pin a full forty-character 3.0 source revision")
    detected = detected_target()
    if target is not None and target != detected:
        raise ValueError("Physical QA target does not match this computer")
    target = detected
    expected_ext = (".exe" if target.startswith("windows") else
                    ".deb" if target == "linux-x64" else ".dmg")
    if installer.suffix.lower() != expected_ext:
        raise ValueError("Installer extension does not match physical test OS")
    return {
        "schema_version": 1,
        "status": STATUS,
        "source_revision": commit,
        "target": target,
        "installer_filename": installer.name,
        "installer_sha256": sha_file(installer),
        "installer_size_bytes": installer.stat().st_size,
        "created_utc": now(),
        "last_updated_utc": now(),
        "host_checks": {name: "not-tested" for name in HOST_CHECKS},
        "console_checks": {
            name: {check: "not-tested" for check in CONSOLE_CHECKS}
            for name in SYSTEMS
        },
        "independent_hardware_reviewed": False,
        "external_license_redistribution_reviewed": False,
        "source_to_binary_correspondence_reviewed": False,
        "production_approval": False,
        "public_release_approved": False,
        "contains_rom_names_paths_or_game_files": False,
        "statement": REPORT_STATEMENT,
    }


REQUIRED_REPORT_KEYS = frozenset((
    "schema_version", "status", "source_revision", "target",
    "installer_filename", "installer_sha256", "installer_size_bytes",
    "created_utc", "last_updated_utc", "host_checks", "console_checks",
    "independent_hardware_reviewed", "external_license_redistribution_reviewed",
    "source_to_binary_correspondence_reviewed", "production_approval",
    "public_release_approved", "contains_rom_names_paths_or_game_files",
    "statement",
))


def validate_report(report):
    # Privacy is part of the evidence format, not just the CLI. Reject
    # unexpected keys (e.g., ROM paths or private photos) even if someone
    # directly edits a report before export or four-host reconciliation.
    if not isinstance(report, dict) or set(report) != REQUIRED_REPORT_KEYS:
        raise ValueError("Physical QA report includes missing or private extra fields")
    if report.get("statement") != REPORT_STATEMENT:
        raise ValueError("QA report statement cannot contain private user information")
    name = report.get("installer_filename")
    if (not isinstance(name, str)
            or len(name) > 180
            or not re.fullmatch(r"[A-Za-z0-9_.() ~-]+\.(?:exe|deb|dmg)", name)
            or name in (".", "..")):
        raise ValueError("Physical QA installer name must be a private-safe basename")
    expected_ext = (".exe" if report.get("target") == "windows-x64" else
                    ".deb" if report.get("target") == "linux-x64" else
                    ".dmg")
    if not name.endswith(expected_ext):
        raise ValueError("Physical QA filename does not match the target platform")
    if (not isinstance(report, dict) or report.get("schema_version") != 1
            or report.get("status") != STATUS
            or report.get("target") not in TARGETS
            or not isinstance(report.get("source_revision"), str)
            or not COMMIT.fullmatch(report["source_revision"])
            or not isinstance(report.get("installer_sha256"), str)
            or not SHA256.fullmatch(report["installer_sha256"])
            or type(report.get("installer_size_bytes")) is not int
            or report["installer_size_bytes"] <= 0):
        raise ValueError("Physical QA report has inconsistent metadata")
    if (not isinstance(report.get("host_checks"), dict)
            or set(report["host_checks"]) != set(HOST_CHECKS)
            or not isinstance(report.get("console_checks"), dict)
            or set(report["console_checks"]) != set(SYSTEMS)):
        raise ValueError("Physical QA inventory does not cover all 18 consoles")
    for system, row in report["console_checks"].items():
        if not isinstance(row, dict) or set(row) != set(CONSOLE_CHECKS):
            raise ValueError(f"{system}: missing or extra hardware QA checks")
        if any(value not in ANSWERS for value in row.values()):
            raise ValueError(f"{system}: invalid manual test result")
    if any(value not in ANSWERS for value in report["host_checks"].values()):
        raise ValueError("Invalid installer/host test result")
    for key in (
        "independent_hardware_reviewed",
        "external_license_redistribution_reviewed",
        "source_to_binary_correspondence_reviewed",
        "production_approval", "public_release_approved",
        "contains_rom_names_paths_or_game_files",
    ):
        if report.get(key) is not False:
            raise ValueError(f"Forbidden owner-side approval or private data: {key}")
    return report


def _store(path, obj, *, existing=False):
    """Atomic replace with no additional files or ROM-related metadata."""
    path = _output(path)
    validate_report(obj)
    if existing != path.is_file():
        raise ValueError("QA report must exist for an edit, or be new for init")
    path.parent.mkdir(parents=True, exist_ok=True)
    if existing:
        current = validate_report(json.loads(path.read_text(encoding="utf-8")))
        for key in ("source_revision", "target", "installer_sha256",
                    "installer_size_bytes", "installer_filename", "created_utc"):
            if current[key] != obj[key]:
                raise ValueError(f"Immutable physical QA identity changed: {key}")
    data = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=".ap-qa-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def load_report(path):
    path = _output(path)
    return validate_report(json.loads(path.read_text(encoding="utf-8")))


def record_result(report, *, check, result, system=None):
    if result not in ANSWERS:
        raise ValueError("QA result must be pass, fail or not-tested")
    if system is None:
        if check not in HOST_CHECKS:
            raise ValueError("Unknown installed host/installer QA check")
        report["host_checks"][check] = result
    else:
        if system not in SYSTEMS or check not in CONSOLE_CHECKS:
            raise ValueError("Unknown console or required gameplay check")
        report["console_checks"][system][check] = result
    report["last_updated_utc"] = now()
    validate_report(report)
    return report


def counts(report):
    validate_report(report)
    observed = list(report["host_checks"].values())
    observed.extend(value for entry in report["console_checks"].values()
                    for value in entry.values())
    return {value: observed.count(value) for value in sorted(ANSWERS)}


def brief(report):
    totals = counts(report)
    tested = totals["pass"] + totals["fail"]
    outstanding = totals["not-tested"]
    ready = outstanding == 0 and totals["fail"] == 0
    return (
        f"PHYSICAL QA SELF-REPORT [{report['target']}]: "
        f"{tested}/{len(HOST_CHECKS)+len(CONSOLE_CHECKS)*len(SYSTEMS)} "
        f"checks performed; {totals['pass']} pass, {totals['fail']} fail, "
        f"{outstanding} not tested. "
        + ("COMPLETE FOR INDEPENDENT REVIEW; NOT APPROVED FOR DISTRIBUTION"
           if ready else "NOT COMPLETE; PUBLIC 3.0 RELEASE BLOCKED")
    )


def review_wizard(report, *, reader=input, printer=print, on_record=None):
    """Physical walkthrough; optional callback atomically saves EACH answer."""
    for label, system, results in (
        [("Installed application", None, report["host_checks"])]
        + [(SYSTEMS[key].title, key, report["console_checks"][key])
           for key in SYSTEMS]
    ):
        printer(f"\n{label}: operate the ACTUAL installed app while offline.")
        for check in results:
            if results[check] != "not-tested":
                continue
            printer(f"  Verify {check.replace('_', ' ')} in person.")
            answer = reader("  [p]ass, [f]ail, [s]kip, [q]uit and save: ").strip().lower()
            if answer in ("q", "quit"):
                return report
            if answer not in ("p", "f", "s"):
                printer("  Unrecognized answer; remains NOT TESTED.")
                continue
            record_result(report, check=check,
                          result={"p": "pass", "f": "fail",
                                  "s": "not-tested"}[answer],
                          system=system)
            if on_record is not None:
                on_record(report)
    return report


def export_review(report, output):
    """Write only an unapproved reviewer report and independent checksum."""
    validate_report(report)
    output = _output(output)
    if (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        raise ValueError("Evidence destination must be new or empty")
    output.mkdir(parents=True, exist_ok=True)
    prepared = output / "V30_PHYSICAL_QA_OWNER_REPORTED_UNREVIEWED.json"
    prepared.write_bytes((json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    checksum = f"{sha_file(prepared)}  {prepared.name}\n"
    (output / "SHA256SUMS.txt").write_bytes(checksum.encode("ascii"))
    return prepared


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="cmd", required=True)
    begin = commands.add_parser("init", help="Pin the actual local installer and all 18 checklists")
    begin.add_argument("--installer", required=True, type=Path)
    begin.add_argument("--commit", required=True)
    begin.add_argument("--out", required=True, type=Path)
    for name in ("wizard", "record", "status", "export"):
        sub = commands.add_parser(name)
        sub.add_argument("--report", required=True, type=Path)
        if name == "record":
            sub.add_argument("--system", choices=sorted(SYSTEMS))
            sub.add_argument("--check", required=True)
            sub.add_argument("--result", required=True, choices=sorted(ANSWERS))
        if name == "export":
            sub.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "init":
            obj = create_report(args.installer, commit=args.commit)
            _store(args.out, obj)
            print(f"Created owner-side OFFLINE physical checklist: {args.out}")
        else:
            obj = load_report(args.report)
            if args.cmd == "wizard":
                # Persist each observed step, so a killed terminal, accidental
                # Ctrl+C, or power loss cannot discard verified progress.
                review_wizard(
                    obj,
                    on_record=lambda progress: _store(
                        args.report, progress, existing=True),
                )
                _store(args.report, obj, existing=True)
            elif args.cmd == "record":
                record_result(obj, check=args.check, result=args.result, system=args.system)
                _store(args.report, obj, existing=True)
            elif args.cmd == "export":
                path = export_review(obj, args.output)
                print(f"Saved unapproved private QA report: {path}")
            print(brief(obj))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        parser.exit(1, f"PHYSICAL QA EVIDENCE REJECTED: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
