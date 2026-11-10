"""Fail-closed 3.1 publication gate; informational until all evidence exists.

Technical QA is necessary but cannot automate a copyright/licensing judgment
or substitute for real controller acceptance. GitHub Actions must not create
a public release from a preview-only build.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "config" / "v3.1-release-readiness.json"
REQUIRED_GATES = (
    "full_eighteen_console_installer",
    "four_platform_full_installer_verification",
    "real_controller_hardware_acceptance",
    "pygame_sdl_redistribution_review",
    "corresponding_source_material",
    "release_notes_and_rollout",
)


def blockers(report):
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        return ("invalid release-readiness schema",)
    if report.get("version") != "3.1.0":
        return ("unknown release version",)
    gates = report.get("release_gates")
    if not isinstance(gates, dict) or set(gates) != set(REQUIRED_GATES):
        return ("missing or extra release acceptance gates",)
    failures = []
    for gate in REQUIRED_GATES:
        item = gates[gate]
        if not isinstance(item, dict) or item.get("verified") is not True:
            failures.append(gate)
        elif not isinstance(item.get("evidence"), str) or not item["evidence"].startswith(
            "https://github.com/MasynNay/anything-plays/"
        ):
            failures.append(gate + ": missing explicit GitHub evidence")
    if report.get("public_release_approved") is not True:
        failures.append("owner has not approved this exact release")
    return tuple(failures)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default=str(FILE))
    args = p.parse_args()
    try:
        report = json.loads(Path(args.manifest).read_text("utf-8"))
    except (OSError, ValueError) as exc:
        p.exit(1, f"3.1 RELEASE BLOCKED: cannot read acceptance manifest: {exc}\n")
    pending = blockers(report)
    if pending:
        for item in pending:
            print(f"3.1 RELEASE BLOCKED: {item}")
        raise SystemExit(1)
    print("All documented evidence fields present; conduct final independent review.")


if __name__ == "__main__":
    main()
