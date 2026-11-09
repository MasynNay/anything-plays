"""Audit the EXACT eleven Tia original-source cores from the successful four-OS 3.0 run.

The older 10-source review workflow is historical; it audits Stella2014 and
Snes9x and cannot be used to determine the selected 3.0 composition. This
script refuses those historical native names and validates original Git source
snapshots, real-installed SHA-256 receipts, and seven-session A/V tests.

It never invents licenses, user-device QA, or an approved distribution lock.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from anything_plays.v30_approved_core_map import (
    ELEVEN_TIA_EXPECTED, ELEVEN_TIA_REPOSITORIES,
)
from tools.prepare_v30_source_companion import validate_captured_sources

TARGETS = ("windows-x64", "linux-x64", "macos-arm64", "macos-x64")
REPORTS = (
    "ORIGINAL_10_SOURCE_BUILT_NATIVE_STAGING_UNAPPROVED.json",
    "ORIGINAL_11_SOURCE_BUILT_STAGING_UNAPPROVED.json",
    "ORIGINAL_11_SOURCE_TIA_REPLACEMENT_UNAPPROVED.json",
    "INSTALLED_GPL_ALTERNATIVE_PROVENANCE_UNAPPROVED.json",
    "ACTUAL_INSTALLED_7_CYCLE_SWITCH_UNAPPROVED.json",
    "ACTUAL_FROZEN_GUI_STARTUP_UNAPPROVED.json",
)
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
FIVE = ("fceumm", "prosystem", "mednafen_ngp", "mednafen_wswan")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(file: Path):
    require(file.is_file() and not file.is_symlink() and file.stat().st_size < 2_000_000,
            "Missing or unsafe evidence: " + str(file))
    return json.loads(file.read_text(encoding="utf-8"))


def sha_record(row, name, sources):
    require(isinstance(row, dict), "Missing native build proof " + name)
    digest = row.get("native_sha256")
    require(isinstance(digest, str) and HEX64.fullmatch(digest),
            "Invalid original native SHA-256: " + name)
    require(row.get("source_commit") == sources[name]["source_commit"],
            "Source revision mismatch: " + name)
    require(row.get("source_repository") == ELEVEN_TIA_REPOSITORIES[name],
            "Wrong upstream source: " + name)
    return digest


def audit_original_tia(reports_root: Path, source_dir: Path):
    manifest = validate_captured_sources(source_dir)
    require(manifest["source_set_id"] == "original-eleven-gpl2plus-tia",
            "Historical Stella/noncommercial source set is forbidden")
    require(manifest["core_count"] == 11 and set(manifest["sources"]) == set(ELEVEN_TIA_EXPECTED),
            "Expected eleven and only eleven pinned original sources")
    sources = manifest["sources"]
    for name, commit in ELEVEN_TIA_EXPECTED.items():
        require(sources[name]["source_commit"] == commit,
                "Wrong pinned original commit for " + name)
        require(sources[name]["source_repository"] == ELEVEN_TIA_REPOSITORIES[name],
                "Wrong original Git repository for " + name)
    require(sources["dolphin"]["nested_gitlink_source_count"] == 37,
            "All 37 Dolphin original Gitlink trees are required")
    targets = {}
    for target in TARGETS:
        folder = Path(reports_root) / target
        reports = {name: read_json(folder / name) for name in REPORTS}
        require(all(item.get("target") == target for item in reports.values()),
                "Mixed-platform original evidence: " + target)
        ten = reports[REPORTS[0]]
        eleven = reports[REPORTS[1]]
        tia = reports[REPORTS[2]]
        installed = reports[REPORTS[3]]
        sessions = reports[REPORTS[4]]
        gui = reports[REPORTS[5]]
        require(ten["native_core_count"] == 11
                and eleven["native_core_count"] == 11
                and eleven["source_built_families"] == 11
                and eleven["old_buildbot_dolphin_excluded"] is True
                and tia["original_core_count"] == 11
                and tia["original_profile_count"] == 18
                and tia["original_stella2014_native_excluded"] is True,
                "Not the current 11-original Tia composition")
        require(installed["installed_core_count"] == 11
                and installed["console_profiles"] == 18
                and installed["dolphin_sys_bundled"] is True
                and installed["all_eleven_original_source_families_verified"] is True,
                "Not a complete real installed four-OS desktop app")
        require(sessions.get("passed") is True
                and sessions.get("sessions_completed") == sessions.get("sessions_expected") == 7
                and sessions.get("native_child_exit_code") == 0
                and sessions.get("timed_out") is False
                and sessions.get("test_uses_real_installed_original_core_bytes") is True,
                "Seven session real installed audio/video restart tests incomplete")
        require(ten["public_binary_distribution_approved"] is False
                and eleven["public_binary_distribution_approved"] is False
                and tia["public_binary_distribution_approved"] is False
                and installed["legal_review_and_redistribution_approved"] is False,
                "Research records must not impersonate a public license approval")
        native = {}
        for name in ("mednafen_supafaust", "blastem"):
            native[name] = sha_record(ten["alternatives"][name], name, sources)
        for name in FIVE:
            native[name] = sha_record(ten["source_built_remaining_five"][name], name, sources)
        for name, field in (("mgba", "source_built_mgba"),
                            ("parallel_n64", "source_built_n64"),
                            ("mednafen_pce_fast", "source_built_pce")):
            native[name] = sha_record(ten[field], name, sources)
        native["dolphin"] = sha_record(eleven["source_built_dolphin"], "dolphin", sources)
        native["tia"] = sha_record(tia["source_built_tia"], "tia", sources)
        require(set(native) == set(ELEVEN_TIA_EXPECTED) and "stella2014" not in native,
                "A historical or missing emulator leaked into current 3.0")
        require(installed["actual_core_sha256"] == native,
                "Source-built SHA-256 does not match ACTUAL installed native images")
        require(sessions["installed_core_sha256"] == native,
                "Installed seven-session native SHA-256 does not match source proof")
        require(sources["tia"]["source_commit"] == "6ae5bf998fe7a7842294089db17fc86fd73db1f0",
                "Original GPL2-or-later Tia revision mismatch")
        require(tia["source_built_tia"]["source_file_grants_gpl_2_or_later"] is True
                and tia["source_built_tia"]["original_license_notice_copied"] is True,
                "Original Tia source license/notice preservation missing")
        require(eleven["source_built_dolphin"]["pristine_unmodified_original_source_compiled"] is True
                and eleven["source_built_dolphin"]["direct_original_gitlinks"] == 34
                and eleven["source_built_dolphin"]["nested_original_gitlinks"] == 3,
                "Original pristine Dolphin source build and 37 Gitlinks unverified")
        targets[target] = {
            "installed_original_native_sha256": dict(sorted(native.items())),
            "console_profiles": 18,
            "native_core_count": 11,
            "source_compiled_and_installed_sha256_match": True,
            "real_installed_sequential_video_audio_sessions": 7,
            "frozen_gui_report_recorded": gui.get("status") is not None,
            "physical_hardware_all_games_reviewed": False,
            "independent_full_binary_rights_review_complete": False,
        }
    return {
        "schema_version": 1,
        "evidence_status": "EXACT-11-TIA-ORIGINAL-SOURCE-AND-FOUR-OS-NATIVE-MATCH-VERIFIED",
        "selected_core_set": "gpl-source-built-eleven-tia",
        "original_sources": {
            name: {
                "git_revision": sources[name]["source_commit"],
                "original_source_sha256": sources[name]["sha256"],
                "original_tar_bytes": sources[name]["size_bytes"],
                "upstream": sources[name]["source_repository"],
                "dolphin_gitlink_subtrees": sources[name]["nested_gitlink_source_count"],
            }
            for name in sorted(ELEVEN_TIA_EXPECTED)
        },
        "targets": targets,
        "native_sha256_count": 44,
        "original_source_count": 11,
        "original_dolphin_gitlink_trees": 37,
        "historical_stella_and_noncommercial_cores_excluded": True,
        "source_archive_checksummed_and_exact_original_git_revisions_verified": True,
        "installed_native_identity_matches_compiler_reports": True,
        "independent_license_compatibility_review_complete": False,
        "full_retained_binary_dependency_audit_complete": False,
        "retail_game_and_endurance_testing_all_18_consoles_complete": False,
        "public_binary_distribution_approved": False,
        "original_verified_build_run": 42686588072,
        "original_source_archive_run": 42668367694,
        "important": "Evidence of exact original-source/installed native correspondence only; no implied third-party rights approval or full-device QA.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit_original_tia(args.reports, args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("VERIFIED 44 exact source-built native images, 11 corresponding original",
          "Git trees and 37 Dolphin Gitlinks on four real OS installers;",
          "NO public distribution approval inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
