"""3.2 technical freeze and publication gate; cannot publish a release.

Full-native software QA is not owner approval, stable-upgrade verification,
physical hardware coverage or review of native redistribution/source rights.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

SOFTWARE = (
    "python_312_313_native_mgba_tests_passed",
    "four_private_frozen_full_native_installer_qa_passed",
    "linux_18_original_or_pinned_homebrew_qa_passed",
)
PUBLIC = (
    "reviewed_full_native_source_and_redistribution_rights",
    "verified_stable_311_to_320_upgrade_identity_and_game_saves",
    "owner_real_camera_controller_long_gameplay_review",
    "independently_staged_final_public_assets_source_and_sha256",
    "owner_explicit_exact_release_authorization",
)
LIMITS = (
    "physical_camera_verified", "physical_controller_verified",
    "physical_speakers_verified", "commercial_games_all_verified",
    "gamecube_headless_20fps_met", "macos_notarized",
)
PLATFORMS = ["linux-x64", "windows-x64", "macos-arm64", "macos-x64"]


def _flags(value, names):
    if type(value) is not dict or set(value) != set(names):
        raise ValueError("Unknown or missing release gate names")
    if any(type(value[key]) is not bool for key in names):
        raise ValueError("Release gate flags must be true Booleans")
    return value


def assess(record, *, tested_sha=None):
    """Return release status only for the exact, reviewed evidence schema."""
    required = {
        "schema_version", "version", "state", "tested_source_sha",
        "source_workflow", "installer_workflow", "tested_platforms",
        "native_core_families", "console_profiles",
        "linux_homebrew_positive_profiles", "software_evidence",
        "publication_gates", "known_limitations", "public_release_approved",
        "artifacts_expire_at_utc", "note",
    }
    if type(record) is not dict or set(record) != required:
        raise ValueError("Unexpected 3.2 release readiness schema")
    identity = {
        "schema_version": 1, "version": "3.2.0",
        "state": "FEATURE_COMPLETE_PRIVATE_FULL_NATIVE_QA_NOT_PUBLIC",
        "tested_platforms": PLATFORMS,
        "native_core_families": 11, "console_profiles": 18,
        "linux_homebrew_positive_profiles": 18,
    }
    for key, value in identity.items():
        if type(record[key]) is not type(value) or record[key] != value:
            raise ValueError("Invalid release identity or evidence: " + key)
    sha = record["tested_source_sha"]
    if (type(sha) is not str or re.fullmatch(r"[0-9a-f]{40}", sha) is None
            or (tested_sha is not None and sha != tested_sha)):
        raise ValueError("Expected exact tested application SHA")
    if (any(type(record[k]) is not int or record[k] <= 0
            for k in ("source_workflow", "installer_workflow"))):
        raise ValueError("Missing exact tested workflows")
    if (type(record["artifacts_expire_at_utc"]) is not str
            or not record["artifacts_expire_at_utc"].endswith("Z")
            or type(record["note"]) is not str
            or len(record["note"]) < 30):
        raise ValueError("QA expiry and release limitations must be disclosed")
    software = _flags(record["software_evidence"], SOFTWARE)
    public = _flags(record["publication_gates"], PUBLIC)
    limits = _flags(record["known_limitations"], LIMITS)
    if type(record["public_release_approved"]) is not bool:
        raise ValueError("Owner public release approval must be explicit")
    return {
        "software_qa_complete": all(software.values()),
        "public_release_ready": (
            all(software.values()) and all(public.values())
            and record["public_release_approved"]
        ),
        "pending_publication_gates": [k for k in PUBLIC if not public[k]],
        "unverified_field_limits": [k for k in LIMITS if not limits[k]],
        "tested_source_sha": sha,
    }


def read_status(path, *, tested_sha=None):
    file = Path(path)
    if (not file.is_file() or file.is_symlink()
            or not 0 < file.stat().st_size <= 65536):
        raise ValueError("Unsafe 3.2 status file")
    return assess(json.loads(file.read_text("utf-8")), tested_sha=tested_sha)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", type=Path,
                        default=Path("config/v3.2-release-readiness.json"))
    parser.add_argument("--tested-sha")
    parser.add_argument("--require-public-ready", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = read_status(args.status, tested_sha=args.tested_sha)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, "Invalid 3.2 release evidence: " + str(exc) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_public_ready and not result["public_release_ready"]:
        parser.exit(1, "3.2 is NOT authorized for public release\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
