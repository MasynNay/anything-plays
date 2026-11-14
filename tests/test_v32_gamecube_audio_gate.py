"""Private original GameCube audio evidence must fail closed in Linux QA."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.v32_gamecube_audio_gate import (
    PrivateOriginalAVGateError, _read_bounded, check_original_av_pair,
)
from tools.v32_gamecube_audio_research import STATUS

HEAD = "a" * 40


def fixture(kind, binary, main):
    return {
        "schema_version": 1,
        "status": STATUS,
        "source_revision": HEAD,
        "source_program_kind": kind,
        "original_program_compiled_in_private_ci": True,
        "original_program_identity_verified": True,
        "program_sha256": binary * 64,
        "original_program_source_sha256": {
            "main_c_sha256": main * 64, "makefile_sha256": "f" * 64,
        },
        "original_dol_bootstrap_layout": {
            "structure_verified": True,
            "entry_within_text": True,
            "layout_code": "valid_gamecube_dol_layout",
            "text_section_count": 1,
            "data_section_count": 1,
        },
        "parent_report_received": True,
        "native_child_details_received": True,
        "native_subprocess_timed_out": False,
        "native_child_exit_code": 0,
        "native_startup_phase": "game_loaded",
        "native_boot_failure_category": "none",
        "native_child_exception_class": None,
        "native_hw_context_accepted": True,
        "owned_program_native_video_observed": True,
        "native_gpu_homebrew_rendering_verified": True,
        "native_rgb_callback_frames": 120,
        "core_generated_nonzero_pcm_verified": True,
        "experiment_outcome": "observed_original_tone_pcm",
        "core_generated_pcm_sample_frames": 12000,
        "core_generated_nonzero_pcm_values": 6000,
        "speaker_hardware_tested": False,
        "physical_gamepad_tested": False,
        "physical_camera_tested": False,
        "retail_game_compatibility_verified": False,
        "sustained_gameplay_tested": False,
        "public_release_approved": False,
        "ready_for_release": False,
    }


class PrivateGameCubeAudioGateTests(unittest.TestCase):
    def setUp(self):
        self.gx = fixture("gx3d", "b", "d")
        self.console = fixture("console_av", "c", "e")

    def test_two_distinct_original_native_video_and_pcm_pass(self):
        evidence = check_original_av_pair(self.gx, self.console, HEAD)
        self.assertEqual(evidence["independent_original_programs_verified"], 2)
        self.assertTrue(evidence["native_video_and_nonzero_pcm_in_both"])
        self.assertFalse(evidence["ready_for_release"])
        self.assertFalse(evidence["public_release_approved"])
        self.assertFalse(evidence["physical_speaker_tested"])

    def test_rejects_any_missing_or_forged_native_stage(self):
        changes = (
            ("core_generated_nonzero_pcm_verified", False),
            ("core_generated_nonzero_pcm_values", 0),
            ("core_generated_pcm_sample_frames", 0),
            ("native_gpu_homebrew_rendering_verified", False),
            ("owned_program_native_video_observed", False),
            ("native_rgb_callback_frames", 0),
            ("native_startup_phase", "gpu_context_construct_failed"),
            ("native_boot_failure_category", "gpu_factory_failure"),
            ("native_hw_context_accepted", False),
            ("native_child_exception_class", "RuntimeError"),
            ("native_child_exit_code", 1),
            ("native_subprocess_timed_out", True),
            ("original_program_identity_verified", False),
            ("original_program_compiled_in_private_ci", False),
            ("parent_report_received", False),
            ("source_revision", "b" * 40),
            ("program_sha256", "not-a-digest"),
            ("ready_for_release", True),
            ("speaker_hardware_tested", True),
        )
        for key, value in changes:
            with self.subTest(key=key):
                row = copy.deepcopy(self.gx)
                row[key] = value
                with self.assertRaises(PrivateOriginalAVGateError):
                    check_original_av_pair(row, self.console, HEAD)

    def test_rejects_nonindependent_program_and_wrong_kind(self):
        for kind in ("gx3d", "", "user-file-path"):
            with self.subTest(kind=kind):
                row = copy.deepcopy(self.console)
                row["source_program_kind"] = kind
                with self.assertRaises(PrivateOriginalAVGateError):
                    check_original_av_pair(self.gx, row, HEAD)
        duplicate = copy.deepcopy(self.console)
        duplicate["program_sha256"] = self.gx["program_sha256"]
        with self.assertRaises(PrivateOriginalAVGateError):
            check_original_av_pair(self.gx, duplicate, HEAD)
        duplicate = copy.deepcopy(self.console)
        duplicate["original_program_source_sha256"] = copy.deepcopy(
            self.gx["original_program_source_sha256"]
        )
        with self.assertRaises(PrivateOriginalAVGateError):
            check_original_av_pair(self.gx, duplicate, HEAD)

    def test_invalid_layout_and_boolean_as_count_rejected(self):
        for key, value in (
            ("entry_within_text", False), ("structure_verified", False),
            ("layout_code", "invalid_section_bounds"),
            ("text_section_count", True),
        ):
            row = copy.deepcopy(self.gx)
            row["original_dol_bootstrap_layout"][key] = value
            with self.subTest(key=key), self.assertRaises(PrivateOriginalAVGateError):
                check_original_av_pair(row, self.console, HEAD)
        row = copy.deepcopy(self.gx)
        row["core_generated_pcm_sample_frames"] = True
        with self.assertRaises(PrivateOriginalAVGateError):
            check_original_av_pair(row, self.console, HEAD)

    def test_bounded_receipts_reject_links_and_paths_are_redacted(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            missing = root / "user-home-private.json"
            with self.assertRaises(PrivateOriginalAVGateError) as ctx:
                _read_bounded(missing)
            self.assertNotIn("user-home-private", str(ctx.exception))
            content = root / "receipt.json"
            content.write_text(json.dumps(self.gx), "utf-8")
            self.assertEqual(_read_bounded(content)["source_revision"], HEAD)
            link = root / "link.json"
            link.symlink_to(content)
            with self.assertRaises(PrivateOriginalAVGateError):
                _read_bounded(link)
            content.write_bytes(b"!" * (64 * 1024 + 1))
            with self.assertRaises(PrivateOriginalAVGateError):
                _read_bounded(content)

    def test_workflow_requires_original_audio_pair_before_artifact_upload(self):
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github/workflows/v32-private-preview-installers.yml"
        ).read_text("utf-8")
        calls = workflow.split(
            ".build-venv/bin/python -m tools.v32_gamecube_audio_gate"
        )
        self.assertEqual(len(calls), 2)
        self.assertIn("--gx-report", calls[1])
        self.assertIn("--console-report", calls[1])
        self.assertIn("--source-sha", calls[1])
        self.assertLess(
            workflow.index(".build-venv/bin/python -m tools.v32_gamecube_audio_gate"),
            workflow.index(
                "- name: Retain Linux full-native-core research QA separately"
            ),
        )


if __name__ == "__main__":
    unittest.main()
