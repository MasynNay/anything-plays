"""Fail-closed stable binary release check with separate physical QA disclosure.

Real hardware acceptance is a QA quality check, not itself a license mandate.
Unperformed real-controller testing must be explicitly disclosed, and cannot
stand in for LGPL source, notices, replacement/redistribution clearance.
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
# Physical controller validation must stay truthfully unverified until a real
# device is tested. For a clearly labeled free portfolio release it may be
# disclosed rather than silently converted to a fake technical PASS.
ADVISORY_GATE = "real_controller_hardware_acceptance"
PUBLICATION_GATES = tuple(g for g in REQUIRED_GATES if g != ADVISORY_GATE)


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
        if not isinstance(item, dict):
            failures.append(gate)
            continue
        if gate == ADVISORY_GATE and item.get("verified") is False:
            disclosure = report.get("hardware_acceptance_disclosure")
            if (not isinstance(disclosure, dict)
                    or disclosure.get("owner_accepts_uncertified_hardware") is not True
                    or disclosure.get("physical_controller_tested") is not False
                    or not isinstance(disclosure.get("evidence"), str)
                    or not disclosure["evidence"].startswith(
                        "https://github.com/MasynNay/anything-plays/")):
                failures.append("missing explicit untested-hardware disclosure")
            continue
        if item.get("verified") is not True:
            failures.append(gate)
        elif not isinstance(item.get("evidence"), str) or not item["evidence"].startswith(
            "https://github.com/MasynNay/anything-plays/"
        ):
            failures.append(gate + ": missing explicit GitHub evidence")
    if report.get("public_release_approved") is not True:
        failures.append("owner has not approved this exact release")
    else:
        decision = report.get("release_decision")
        expected = {
            "scope": "FREE_NONCOMMERCIAL_NONPROMOTIONAL_NO_DONATIONS_NO_ADS",
            "source_companion_name": "AnythingPlays-3.1.0-PYGAME-SDL-MPG123-ORIGINAL-SOURCE.zip",
            "asset_count": 8,
            "exact_approved_source_revision": "104b96621ec4cb8dc39fde8c3fe96fc854c406ed",
            "owner_requested_publication": True,
            "physical_controller_tested": False,
            "legal_compliance_guaranteed": False,
        }
        if (not isinstance(decision, dict)
                or any(type(decision.get(key)) is not type(val)
                       or decision[key] != val for key, val in expected.items())
                or not isinstance(decision.get("review"), str)
                or not decision["review"].startswith(
                    "https://github.com/MasynNay/anything-plays/")):
            failures.append("approved release missing exact free-source scope and risk record")
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
