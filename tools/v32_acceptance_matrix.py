"""Combine BOTH exact-head Linux 3.2 homebrew receipts without release overclaims.

No real user's ROMs, keys, camera IDs, screenshots, error traces or paths
are copied to this receipt. These are original or immutable license-pinned
CI SOFTWARE TESTS, not a demonstration of commercial-game compatibility.
All four installer architectures have separate packaging checks; this
matrix describes only the Linux native software-runtime tests.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from tools.v32_original_native_runtime import (
    CASES, REQUIRED, EXPLORATORY, STATUS as SOURCE_STATUS,
)
from tools.v32_extended_native_runtime import (
    TARGETS, CORES, STATUS as EXTENDED_STATUS,
)

STATUS = "PRIVATE_V32_18_PROFILE_LINUX_HOMEBREW_EVIDENCE_NOT_RELEASE"
PROFILE_NAMES = tuple(CASES) + TARGETS
EXPECTED_CORES = {
    **{system: spec[0] for system, spec in CASES.items()},
    **CORES,
}
if len(PROFILE_NAMES) != 18 or len(set(PROFILE_NAMES)) != 18:
    raise RuntimeError("18 different console profiles required")


def _read_receipt(file):
    path = Path(file)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 512 * 1024:
        raise ValueError("Missing/unsafe bounded 3.2 native research receipt")
    data = json.loads(path.read_text("utf-8"))
    if type(data) is not dict:
        raise ValueError("3.2 native evidence must be an object")
    return data


def _flag(value, description):
    if type(value) is not bool:
        raise ValueError("Malformed native evidence Boolean: " + description)
    return value


def _validate_source(data, sha):
    must = {
        "status": SOURCE_STATUS,
        "source_revision": sha,
        "binary_tested": "installed full-native 3.2 Linux core payload",
        "schema_version": 1,
        "profiles_in_native_inventory": 18,
        "native_core_families_in_inventory": 11,
        "original_source_generated_homebrew_only": True,
        "all_18_consoles_gameplay_verified": False,
        "commercial_game_compatibility_verified": False,
        "public_release_approved": False,
        "required_profiles_tested": list(REQUIRED),
        "exploratory_profiles_tested": list(EXPLORATORY),
    }
    for key, value in must.items():
        if type(data.get(key)) is not type(value) or data[key] != value:
            raise ValueError("Original homebrew source receipt mismatch: " + key)
    probes = data.get("probes")
    if type(probes) is not list or len(probes) != len(CASES):
        raise ValueError("Missing original 14 native probes")
    if [row.get("system") for row in probes if type(row) is dict] != list(CASES):
        raise ValueError("Unexpected/duplicate original native systems or order")
    for row in probes:
        system = row["system"]
        if (row.get("core_name") != EXPECTED_CORES[system]
                or _flag(row.get("required_gate"), "required_gate")
                != (system in REQUIRED)):
            raise ValueError("Incorrect original native source core identity")
        passed = _flag(row.get("probe_passed"), "source probe pass")
        zero = _flag(row.get("native_child_exit_zero"), "child process exit")
        timed_out = _flag(row.get("timed_out"), "child process timeout")
        if passed and (not zero or timed_out):
            raise ValueError("An original native crashed/timed-out probe claimed success")
    required_passed = sum(row["probe_passed"] for row in probes
                          if row["system"] in REQUIRED)
    exploratory_passed = sum(row["probe_passed"] for row in probes
                             if row["system"] in EXPLORATORY)
    if (type(data.get("required_profiles_passed")) is not int
            or data["required_profiles_passed"] != required_passed
            or type(data.get("exploratory_profiles_passed")) is not int
            or data["exploratory_profiles_passed"] != exploratory_passed
            or _flag(data.get("passed"), "original gate")
            != (required_passed == len(REQUIRED))):
        raise ValueError("Original native A/V pass counts disagree with individual results")
    return probes


def _validate_extended(data, sha):
    must = {
        "status": EXTENDED_STATUS,
        "source_revision": sha,
        "installed_binary_checked": "exact-source full-native Linux 3.2 QA install",
        "schema_version": 1,
        "profiles": list(TARGETS),
        "profiles_attempted": 4,
        "remaining_three_fixtures_hash_pinned_in_repo": True,
        "all_18_consoles_gameplay_verified": False,
        "commercial_game_compatibility_verified": False,
        "public_release_approved": False,
    }
    for key, value in must.items():
        if type(data.get(key)) is not type(value) or data[key] != value:
            raise ValueError("Four-profile source receipt mismatch: " + key)
    probes = data.get("probe_results")
    if type(probes) is not list or len(probes) != len(TARGETS):
        raise ValueError("Four last original/pinned native probe results missing")
    if [r.get("profile") for r in probes if type(r) is dict] != list(TARGETS):
        raise ValueError("Incorrect final native profile set, order or duplicates")
    for row in probes:
        profile = row["profile"]
        if (row.get("native_core") != EXPECTED_CORES[profile]
                or row.get("is_exploratory") is not True):
            raise ValueError("Untrusted last-four native emulator identity")
        passed = _flag(row.get("native_probe_verified"), "last-four native result")
        timed_out = _flag(row.get("timed_out"), "last-four native timeout")
        code = row.get("native_process_exit_code")
        if passed and (timed_out or type(code) is not int or code != 0):
            raise ValueError("Last-four native crash/timeout claimed success")
        if profile == "ngpc" and passed:
            if (row.get("native_parent_probe_passed") is not True
                    or row.get("native_child_report_passed") is not True
                    or type(row.get("native_inner_exit_code")) is not int
                    or row["native_inner_exit_code"] != 0
                    or row.get("fixture_blob_matches_pinned_source") is not True
                    or row.get("fixture_color_mode_confirmed") is not True
                    or row.get("video_gate_passed") is not True
                    or row.get("audio_gate_passed") is not True
                    or row.get("input_gate_passed") is not True):
                raise ValueError("NGPC native original fixture/child A/V/input unverified")
        if profile == "gamecube" and passed:
            if row.get("production_gpu_backend_exercised") is not True:
                raise ValueError("GameCube native success requires actual GPU backend")
    amount = sum(r["native_probe_verified"] for r in probes)
    if (type(data.get("exploratory_profiles_verified")) is not int
            or data["exploratory_profiles_verified"] != amount
            or _flag(data.get("all_four_exploratory_verified"), "all four")
            != (amount == 4)):
        raise ValueError("Last-four native pass counts inconsistent with per-console probes")
    return probes


def consolidate(original, extended, sha):
    """Fail closed on inconsistent schema, provenance or success counts."""
    if type(sha) is not str or re.fullmatch("[0-9a-f]{40}", sha) is None:
        raise ValueError("Exact 3.2 source Git SHA required")
    first = _validate_source(original, sha)
    last = _validate_extended(extended, sha)
    rows = []
    for row in first:
        rows.append({
            "console_profile": row["system"],
            "source_built_native_core": EXPECTED_CORES[row["system"]],
            "test_type": "source_generated_original_libretro_audio_video",
            "native_software_smoke_passed": row["probe_passed"],
            "required_gate": row["required_gate"],
        })
    for row in last:
        name = row["profile"]
        output = {
            "console_profile": name,
            "source_built_native_core": EXPECTED_CORES[name],
            "test_type": (
                "original_monochrome_audio_video_input" if name == "ngp"
                else "hash_pinned_mit_color_audio_video_input" if name == "ngpc"
                else "hash_pinned_public_domain_software_video" if name == "n64"
                else "hash_pinned_zlib_offscreen_gpu_video_input"
            ),
            "native_software_smoke_passed": row["native_probe_verified"],
            "required_gate": False,
        }
        if name == "gamecube":
            output.update({
                "headless_20fps_threshold_met": _flag(
                    row.get("headless_20fps_threshold_met"), "GameCube Mesa speed"
                ),
                "nonzero_native_pcm_observed": _flag(
                    row.get("real_nonzero_pcm_observed"), "GameCube sound"
                ),
                "offscreen_production_gpu_exercised": _flag(
                    row.get("production_gpu_backend_exercised"), "GameCube backend"
                ),
            })
        rows.append(output)
    if len(rows) != 18 or {x["console_profile"] for x in rows} != set(PROFILE_NAMES):
        raise ValueError("Native software report must have exactly 18 unique profiles")
    passed = sum(x["native_software_smoke_passed"] for x in rows)
    gc = rows[-1]
    # No original test, regardless of performance, is an authorization to
    # claim physical camera/USB testing, retail titles, saves or licensing.
    return {
        "schema_version": 1,
        "status": STATUS,
        "source_revision": sha,
        "test_scope": "linux_x64_original_or_hash_pinned_native_homebrew",
        "console_profiles_in_native_package": 18,
        "source_built_native_core_families_in_package": 11,
        "native_software_profiles_tested": 18,
        "native_software_profiles_with_positive_evidence": passed,
        "original_14_profile_baseline_gate_passed": original["passed"],
        "remaining_4_profile_research_positive": extended["exploratory_profiles_verified"],
        "per_console_results": rows,
        "all_18_bounded_homebrew_software_smokes_positive": passed == 18,
        "gamecube_headless_20fps_met": gc["headless_20fps_threshold_met"],
        "gamecube_test_homebrew_nonzero_audio_observed": gc["nonzero_native_pcm_observed"],
        "all_18_consoles_commercial_gameplay_verified": False,
        "all_18_consoles_sustained_gameplay_verified": False,
        "all_four_os_real_gameplay_verified": False,
        "physical_usb_bluetooth_gamepads_verified": False,
        "physical_camera_input_verified": False,
        "physical_speaker_playback_verified": False,
        "game_save_long_session_verified": False,
        "public_native_core_redistribution_approved": False,
        "macos_notarization_verified": False,
        "public_release_approved": False,
        "ready_for_public_3_2_release": False,
    }


def generate(original_path, extended_path, sha, output):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Never overwrite existing research acceptance evidence")
    report = consolidate(_read_receipt(original_path),
                         _read_receipt(extended_path), sha)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", "utf-8")
    print(json.dumps({
        "status": report["status"],
        "source_revision": sha,
        "software_profiles_with_positive_evidence":
            report["native_software_profiles_with_positive_evidence"],
        "gamecube_headless_20fps_met": report["gamecube_headless_20fps_met"],
        "ready_for_public_3_2_release": False,
    }, indent=2, sort_keys=True))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-receipt", type=Path, required=True)
    p.add_argument("--extended-receipt", type=Path, required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    generate(a.original_receipt, a.extended_receipt,
             a.source_sha, a.output)


if __name__ == "__main__":
    main()
