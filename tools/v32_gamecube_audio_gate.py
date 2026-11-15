"""Fail-closed, PRIVATE Linux 3.2 GameCube original-homebrew A/V gate.

This evaluates only redacted native receipts produced by the exact installed
3.2 source-built GX+ASND and console+ASND programs. Neither this gate nor a
pass means the app plays retail GameCube games, real speaker audio, or has
cleared public distribution/licensing/hardware acceptance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from tools.v32_gamecube_audio_research import STATUS

SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
MAX_RECEIPT_BYTES = 64 * 1024


class PrivateOriginalAVGateError(ValueError):
    """Fixed-category failure, with no raw receipt values or file paths."""


def _require(condition, code):
    if not condition:
        raise PrivateOriginalAVGateError(
            "Private GameCube native A/V evidence gate failed: " + code
        )


def _sha64(value):
    return type(value) is str and SHA64.fullmatch(value) is not None


def _verified_report(row, kind, exact_sha):
    _require(type(row) is dict, "missing_report")
    _require(row.get("schema_version") == 1, "schema_mismatch")
    _require(row.get("status") == STATUS, "research_status_mismatch")
    _require(row.get("source_revision") == exact_sha, "source_revision_mismatch")
    _require(row.get("source_program_kind") == kind, "program_kind_mismatch")
    _require(row.get("original_program_compiled_in_private_ci") is True,
             "source_build_unverified")
    _require(row.get("original_program_identity_verified") is True,
             "program_identity_unverified")
    _require(_sha64(row.get("program_sha256")), "program_sha_missing")
    originals = row.get("original_program_source_sha256")
    _require(type(originals) is dict
             and _sha64(originals.get("main_c_sha256"))
             and _sha64(originals.get("makefile_sha256")),
             "original_source_digest_missing")
    layout = row.get("original_dol_bootstrap_layout")
    _require(type(layout) is dict
             and layout.get("structure_verified") is True
             and layout.get("entry_within_text") is True
             and layout.get("layout_code") == "valid_gamecube_dol_layout"
             and type(layout.get("text_section_count")) is int
             and layout["text_section_count"] >= 1,
             "gamecube_dol_layout_unverified")
    _require(row.get("parent_report_received") is True
             and row.get("native_child_details_received") is True
             and row.get("native_subprocess_timed_out") is False
             and type(row.get("native_child_exit_code")) is int
             and row["native_child_exit_code"] == 0,
             "native_execution_unverified")
    _require(row.get("native_startup_phase") == "game_loaded"
             and row.get("native_boot_failure_category") == "none"
             and row.get("native_child_exception_class") is None
             and row.get("native_hw_context_accepted") is True,
             "native_gpu_startup_unverified")
    _require(row.get("owned_program_native_video_observed") is True
             and row.get("native_gpu_homebrew_rendering_verified") is True
             and type(row.get("native_rgb_callback_frames")) is int
             and row["native_rgb_callback_frames"] >= 12,
             "native_video_unverified")
    _require(row.get("core_generated_nonzero_pcm_verified") is True
             and row.get("experiment_outcome") == "observed_original_tone_pcm"
             and type(row.get("core_generated_pcm_sample_frames")) is int
             and row["core_generated_pcm_sample_frames"] >= 1000
             and type(row.get("core_generated_nonzero_pcm_values")) is int
             and row["core_generated_nonzero_pcm_values"] >= 200,
             "native_pcm_unverified")
    for marker in (
        "speaker_hardware_tested", "physical_gamepad_tested",
        "physical_camera_tested", "retail_game_compatibility_verified",
        "sustained_gameplay_tested", "public_release_approved",
        "ready_for_release",
    ):
        _require(row.get(marker) is False, "nonrelease_boundary_unverified")
    return row


def check_original_av_pair(gx, console, exact_sha):
    """Verify two distinct authentic private original GameCube A/V receipts."""
    _require(type(exact_sha) is str
             and SHA40.fullmatch(exact_sha) is not None,
             "invalid_exact_source_revision")
    a = _verified_report(gx, "gx3d", exact_sha)
    b = _verified_report(console, "console_av", exact_sha)
    _require(
        a["program_sha256"] != b["program_sha256"]
        and a["original_program_source_sha256"]["main_c_sha256"]
        != b["original_program_source_sha256"]["main_c_sha256"],
        "original_programs_not_independent",
    )
    return {
        "status": "PRIVATE_V32_ORIGINAL_GAMECUBE_LINUX_AUDIO_GATE_PASSED_NOT_RELEASE",
        "source_revision": exact_sha,
        "independent_original_programs_verified": 2,
        "native_video_and_nonzero_pcm_in_both": True,
        "physical_speaker_tested": False,
        "commercial_game_compatibility_verified": False,
        "public_release_approved": False,
        "ready_for_release": False,
    }


def _read_bounded(path):
    file = Path(path)
    try:
        if file.is_symlink():
            raise OSError("link")
        with file.open("rb") as stream:
            raw = stream.read(MAX_RECEIPT_BYTES + 1)
    except OSError as exc:
        raise PrivateOriginalAVGateError(
            "Private GameCube native A/V evidence gate failed: receipt_unreadable"
        ) from exc
    _require(len(raw) <= MAX_RECEIPT_BYTES, "receipt_too_large")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise PrivateOriginalAVGateError(
            "Private GameCube native A/V evidence gate failed: receipt_invalid_json"
        ) from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gx-report", type=Path, required=True)
    parser.add_argument("--console-report", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    try:
        result = check_original_av_pair(
            _read_bounded(args.gx_report),
            _read_bounded(args.console_report),
            args.source_sha,
        )
    except PrivateOriginalAVGateError as exc:
        # Error classes here are fixed literals, never paths, device names,
        # native traces, or untrusted JSON values.
        parser.exit(1, str(exc) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
