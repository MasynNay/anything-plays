"""Fail-closed release gate for Anything Plays 2.1.

A green alpha build verifies that source compiles and an installer packages;
it does not prove every console is self-contained and playable.

This gate must pass before tagging/publishing a public 2.1 release. Use
--report-only in the alpha CI workflow to report blockers without preventing
ongoing engineering builds. Do not automatically set acceptance flags based
on unit tests: real games, packaged installs and sustained camera play need
independently reviewed evidence on each supported platform.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from anything_plays.systems import SYSTEMS  # noqa: E402

ACCEPTANCE_FILE = ROOT / "config" / "v2.1-release-acceptance.json"
SYSTEM_FLAGS = ("bundled", "in_app_video", "camera_controls", "real_game_verified")
PLATFORM_FLAGS = ("clean_install", "all_consoles_verified", "long_run_verified")
RELEASE_FLAGS = (
    "third_party_license_audit_complete",
    "no_external_emulator_setup_required",
    "packaged_binary_integrity_verified",
)
PLATFORMS = ("windows-x64", "macos-arm64", "macos-x86_64", "linux-x64")


def release_blockers(policy, systems=None):
    """Describe unmet acceptance requirements; do not silently waive any."""
    systems = SYSTEMS if systems is None else systems
    blockers = []

    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        return ["Missing or invalid 2.1 release acceptance schema"]

    entries = policy.get("systems")
    if not isinstance(entries, dict):
        return ["Missing per-console release acceptance records"]

    # An unlisted console must never become silently supported or forgotten.
    if set(entries) != set(systems):
        missing = sorted(set(systems) - set(entries))
        extra = sorted(set(entries) - set(systems))
        blockers.append(f"Console inventory mismatch: missing={missing}, extra={extra}")

    for key in sorted(systems):
        row = entries.get(key)
        if not isinstance(row, dict):
            blockers.append(f"{key}: no evidence record")
            continue
        for field in SYSTEM_FLAGS:
            if row.get(field) is not True:
                blockers.append(f"{key}: {field} not verified")
        # The metadata 'backend' field identifies the optional launcher;
        # the actual default runtime is the embedded Libretro software
        # frontend, selected by App.uses_embedded_emulator(). Keep that
        # explicit in acceptance evidence. Switching back to an external
        # required runtime must fail even if all boolean flags are signed.
        if (key in ("n64", "gamecube") and
                row.get("primary_runtime") != "embedded-libretro-software"):
            blockers.append(
                f"{key}: in-app Libretro runtime not selected/verified"
            )

    platforms = policy.get("platform_validation")
    if not isinstance(platforms, dict) or set(platforms) != set(PLATFORMS):
        blockers.append("Platform validation inventory incomplete")
    for platform in PLATFORMS:
        row = platforms.get(platform) if isinstance(platforms, dict) else None
        if not isinstance(row, dict):
            blockers.append(f"{platform}: no installation evidence")
            continue
        for field in PLATFORM_FLAGS:
            if row.get(field) is not True:
                blockers.append(f"{platform}: {field} not verified")

    release = policy.get("required_release_evidence")
    for field in RELEASE_FLAGS:
        if not isinstance(release, dict) or release.get(field) is not True:
            blockers.append(f"Release evidence: {field} not verified")
    return blockers


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-only", action="store_true",
        help="Show what blocks 2.1 without failing development/test builds",
    )
    parser.add_argument(
        "--manifest", type=Path, default=ACCEPTANCE_FILE,
        help="Read the explicitly reviewed 2.1 release acceptance record",
    )
    args = parser.parse_args(argv)
    try:
        policy = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"2.1 RELEASE BLOCKED: Cannot read acceptance record: {exc}")
        return 0 if args.report_only else 1

    blockers = release_blockers(policy)
    if not blockers:
        print("2.1 release acceptance passed. Review signed artifact evidence.")
        return 0

    print(f"2.1 RELEASE BLOCKED: {len(blockers)} unresolved requirements")
    for blocker in blockers:
        print("  - " + blocker)
    print("Test installers may still be built; no public 2.1 release is approved.")
    return 0 if args.report_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
