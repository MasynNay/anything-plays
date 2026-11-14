"""Private 3.2 GameCube original stereo generator: no commercial ROMs."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import v32_gamecube_audio_research as qa


def fixture(sha="a"*64):
    return {
        "passed": True,
        "native_exit_code": 0,
        "fixture_sha256": sha,
        "original_av_dol_sha256": sha,
        "details": {
            "passed": True,
            "backend": "production GameCubeHardwareSession + platform GPU host",
            "passes_in_app_frame_queue": True,
            "gamecube_rgb_callback_frames": 120,
            "sampled_nonblank_frames": 60,
            "distinct_rgb_frame_hashes": 25,
            "native_controller_polls": 900,
            "nonzero_controller_polls": 70,
            "error": None,
            "native_startup_phase": "game_loaded",
            "native_boot_failure_category": "none",
            "native_hw_context_request_count": 1,
            "native_hw_context_accepted": True,
            "native_pcm_frame_samples": 180000,
            "native_pcm_nonzero_values": 39000,
            "native_pcm_sample_rate": 48000.0,
            "native_nonzero_pcm_requirement_met": True,
            "continuous_render_fps": 6.2,
        },
    }


class OriginalGameCubeAVResearchTests(unittest.TestCase):
    def test_current_source_is_original_gx_with_real_generated_stereo_tone(self):
        contents = qa.check_source_program()
        self.assertEqual(set(contents), {"main_c_sha256", "makefile_sha256"})
        self.assertTrue(all(len(s) == 64 for s in contents.values()))
        self.assertEqual(qa.DOL_NAME, "anythingplays-gc-gx-gamecube.dol")

    def test_original_simple_console_av_generator_has_stereo_source(self):
        file_hashes = qa.check_source_program("console_av")
        self.assertEqual(set(file_hashes), {"main_c_sha256", "makefile_sha256"})
        self.assertEqual(
            qa.FIXTURE_PROGRAMS["console_av"][1],
            "anythingplays-gc-av-gamecube.dol",
        )
        with self.assertRaisesRegex(ValueError, "Unrecognized"):
            qa.check_source_program("commercial_game")

    def test_simple_console_av_probe_remains_independent_of_gx3d(self):
        report = qa.evaluate_evidence(
            fixture(), 0, "a"*64, "b"*40, True,
            source_kind="console_av",
        )
        self.assertEqual(report["source_program_kind"], "console_av")
        self.assertIn("console_video", report["fixture"])
        self.assertTrue(report["core_generated_nonzero_pcm_verified"])
        self.assertFalse(report["speaker_hardware_tested"])
        with self.assertRaisesRegex(ValueError, "kind"):
            qa.evaluate_evidence({}, -1, None, "b"*40, False,
                                 source_kind="unknown")

    def test_failure_carries_only_exception_class_never_error_paths(self):
        raw = fixture()
        raw["details"]["error"] = "RuntimeError: /home/secret/roms/child.dol"
        report = qa.evaluate_evidence(raw, 0, "a"*64, "b"*40, True)
        self.assertEqual(report["native_child_exception_class"], "RuntimeError")
        self.assertNotIn("/home/secret", json.dumps(report))
        raw["details"]["error"] = "/Users/secret: contains private text"
        report = qa.evaluate_evidence(raw, -1, "a"*64, "b"*40, True)
        self.assertEqual(report["native_child_exception_class"],
                         "other_native_exception")
        self.assertNotIn("/Users/secret", json.dumps(report))

    def test_actual_native_pcm_only_counts_when_source_digest_and_child_valid(self):
        full = qa.evaluate_evidence(fixture(), 0, "a"*64, "b"*40, True)
        self.assertTrue(full["native_gpu_homebrew_rendering_verified"])
        self.assertTrue(full["core_generated_nonzero_pcm_verified"])
        self.assertEqual(full["core_generated_nonzero_pcm_values"], 39000)
        self.assertFalse(full["headless_20fps_threshold_met"])
        for field in ("speaker_hardware_tested", "physical_gamepad_tested",
                      "physical_camera_tested", "retail_game_compatibility_verified",
                      "public_release_approved", "ready_for_release"):
            self.assertFalse(full[field])

    def test_silent_controller_dol_does_not_pass_a_tone_sound_requirement(self):
        raw = fixture()
        raw["details"]["native_pcm_nonzero_values"] = 0
        raw["details"]["native_nonzero_pcm_requirement_met"] = False
        report = qa.evaluate_evidence(raw, 0, "a"*64, "b"*40, True)
        self.assertTrue(report["native_gpu_homebrew_rendering_verified"])
        self.assertFalse(report["core_generated_nonzero_pcm_verified"])

    def test_failed_audio_reports_stage_without_exposing_native_logs(self):
        raw = fixture()
        raw["native_exit_code"] = -11
        raw["error"] = "/Users/private/ROMs/secret-game.dol"
        raw["details"] = None
        report = qa.evaluate_evidence(raw, 1, "a"*64, "b"*40, True)
        self.assertEqual(report["experiment_outcome"],
                         "native_child_details_absent")
        self.assertEqual(report["native_child_exit_code"], -11)
        self.assertTrue(report["parent_report_received"])
        self.assertFalse(report["native_child_details_received"])
        self.assertNotIn("Users/private", str(report))

    def test_crash_bad_fixture_or_missing_parent_cannot_claim_sound(self):
        for wrong in ("bad-parent", "bad-child", "wrong-rom", "no-audio", "no-frames"):
            with self.subTest(wrong=wrong):
                raw = fixture()
                exit_code = 0
                if wrong == "bad-parent":
                    exit_code = -11
                elif wrong == "bad-child":
                    raw["native_exit_code"] = -11
                elif wrong == "wrong-rom":
                    raw["fixture_sha256"] = "c"*64
                elif wrong == "no-audio":
                    raw["details"]["native_pcm_frame_samples"] = 0
                else:
                    raw["details"]["gamecube_rgb_callback_frames"] = 0
                report = qa.evaluate_evidence(raw, exit_code, "a"*64, "b"*40, True)
                self.assertFalse(report["core_generated_nonzero_pcm_verified"])
                self.assertFalse(report["public_release_approved"])

    def test_failed_audio_preserves_authenticated_video_evidence(self):
        raw = fixture()
        raw["passed"] = False
        raw["native_exit_code"] = 1
        raw["details"]["passed"] = False
        raw["details"]["native_pcm_nonzero_values"] = 0
        raw["details"]["native_nonzero_pcm_requirement_met"] = False
        report = qa.evaluate_evidence(raw, 1, "a"*64, "b"*40, True)
        self.assertTrue(report["original_program_identity_verified"])
        self.assertTrue(report["owned_program_native_video_observed"])
        self.assertFalse(report["native_gpu_homebrew_rendering_verified"])
        self.assertFalse(report["core_generated_nonzero_pcm_verified"])
        self.assertEqual(report["experiment_outcome"],
                         "native_video_observed_without_nonzero_pcm")
        self.assertFalse(report["ready_for_release"])

    def test_native_exception_is_not_an_audio_only_failure(self):
        raw = fixture()
        raw["passed"] = False
        raw["native_exit_code"] = 1
        raw["details"]["passed"] = False
        raw["details"]["error"] = "RuntimeError: /home/private/game.dol"
        report = qa.evaluate_evidence(raw, 1, "a"*64, "b"*40, True)
        self.assertFalse(report["owned_program_native_video_observed"])
        self.assertEqual(report["native_child_exception_class"], "RuntimeError")
        self.assertEqual(report["experiment_outcome"], "native_child_exception")
        self.assertNotIn("/home/private", json.dumps(report))

    def test_crash_and_source_mismatch_never_claim_native_video(self):
        for mode in ("source", "crash", "missing-frames", "bool-counter"):
            with self.subTest(mode=mode):
                raw = fixture()
                if mode == "source":
                    raw["fixture_sha256"] = "d" * 64
                elif mode == "crash":
                    raw["native_exit_code"] = -11
                elif mode == "missing-frames":
                    raw["details"]["distinct_rgb_frame_hashes"] = 0
                else:
                    raw["details"]["native_controller_polls"] = True
                report = qa.evaluate_evidence(raw, 0, "a"*64, "b"*40, True)
                self.assertFalse(report["owned_program_native_video_observed"])
                self.assertFalse(report["native_gpu_homebrew_rendering_verified"])
                self.assertFalse(report["core_generated_nonzero_pcm_verified"])

    def test_startup_diagnostics_use_fixed_safe_categories(self):
        from tools.probe_gamecube_app import classify_gamecube_boot_failure
        self.assertEqual(classify_gamecube_boot_failure(
            "GameCube core (Dolphin) rejected /private/owned.dol "
            "(need_fullpath=True)", "libretro_load_rejected",
        ), "retro_load_game_rejected")
        self.assertEqual(classify_gamecube_boot_failure(
            "Dolphin did not register a supported accelerated render context",
            "game_loaded_postload_failure",
        ), "unsupported_hw_render_context")
        self.assertEqual(classify_gamecube_boot_failure(
            "RuntimeError: /Users/secret/mygame.dol", "libretro_loading_game",
        ), "game_load_failure")
        self.assertEqual(
            classify_gamecube_boot_failure(None, "game_loaded"), "none",
        )

    def test_original_research_receipt_redacts_unknown_boot_stage(self):
        raw = fixture()
        raw["details"]["native_startup_phase"] = "/Users/private/mygame.dol"
        raw["details"]["native_boot_failure_category"] = "something private"
        raw["details"]["native_hw_context_request_count"] = True
        out = qa.evaluate_evidence(raw, 0, "a"*64, "b"*40, True)
        self.assertEqual(out["native_startup_phase"], "unavailable")
        self.assertEqual(out["native_boot_failure_category"], "unavailable")
        self.assertEqual(out["native_hw_context_request_count"], 0)
        self.assertNotIn("Users/private", json.dumps(out))

    def test_authenticated_boot_stage_survives_audio_only_failure(self):
        raw = fixture()
        raw["passed"] = False
        raw["native_exit_code"] = 1
        raw["details"]["passed"] = False
        raw["details"]["native_pcm_nonzero_values"] = 0
        raw["details"]["native_nonzero_pcm_requirement_met"] = False
        out = qa.evaluate_evidence(raw, 1, "a"*64, "b"*40, True)
        self.assertEqual(out["native_startup_phase"], "game_loaded")
        self.assertEqual(out["native_boot_failure_category"], "none")
        self.assertTrue(out["native_hw_context_accepted"])
        self.assertFalse(out["core_generated_nonzero_pcm_verified"])
        self.assertFalse(out["public_release_approved"])

    def test_original_dol_header_preflight_accepts_bounded_bootstrap(self):
        import struct
        with TemporaryDirectory() as td:
            dol = Path(td) / "owned-fixture.dol"
            data = bytearray(0x160)
            struct.pack_into(">I", data, 0x00, 0x100)
            struct.pack_into(">I", data, 0x48, 0x80003100)
            struct.pack_into(">I", data, 0x90, 0x40)
            struct.pack_into(">I", data, 0xE0, 0x80003100)
            dol.write_bytes(data)
            parsed = qa.inspect_original_dol(dol)
            self.assertTrue(parsed["structure_verified"])
            self.assertEqual(parsed["layout_code"], "valid_gamecube_dol_layout")
            self.assertEqual(parsed["text_section_count"], 1)
            self.assertTrue(parsed["entry_within_text"])
            self.assertNotIn(str(dol), json.dumps(parsed))

    def test_original_dol_preflight_rejects_invalid_entry_and_range(self):
        import struct
        with TemporaryDirectory() as td:
            dol = Path(td) / "owned-fixture.dol"
            data = bytearray(0x140)
            struct.pack_into(">I", data, 0x00, 0x100)
            struct.pack_into(">I", data, 0x48, 0x80003100)
            struct.pack_into(">I", data, 0x90, 0x40)
            struct.pack_into(">I", data, 0xE0, 0x80004200)
            dol.write_bytes(data)
            self.assertEqual(
                qa.inspect_original_dol(dol)["layout_code"],
                "entry_not_in_text",
            )
            struct.pack_into(">I", data, 0x90, 0x80)
            dol.write_bytes(data)
            self.assertEqual(
                qa.inspect_original_dol(dol)["layout_code"],
                "invalid_section_bounds",
            )
            dol.write_bytes(b"x" * 20)
            self.assertEqual(
                qa.inspect_original_dol(dol)["layout_code"],
                "truncated_header",
            )

    def test_original_dol_preflight_missing_file_is_redacted(self):
        with TemporaryDirectory() as td:
            missing = Path(td) / "private-contents.dol"
            result = qa.inspect_original_dol(missing)
            self.assertFalse(result["structure_verified"])
            self.assertEqual(result["layout_code"], "header_unreadable")
            self.assertNotIn("private-contents", json.dumps(result))

    def test_missing_docker_is_documented_not_hidden_as_sound_success(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            with patch.object(qa, "check_sources",
                              return_value={"gamecube": root/"core.so"}), \
                 patch("tools.v32_gamecube_audio_research.subprocess.run",
                       side_effect=FileNotFoundError("docker unavailable")):
                report = qa.execute(root, root/"receipt", "b"*40, root/"result.json")
            self.assertFalse(report["core_generated_nonzero_pcm_verified"])
            self.assertEqual(report["experiment_outcome"],
                             "source_compiler_not_installed")
            self.assertFalse(report["ready_for_release"])
            from_file = json.loads((root/"result.json").read_text("utf-8"))
            self.assertNotIn("docker unavailable", json.dumps(from_file))
            self.assertNotIn("rom_path", from_file)
            with patch.object(qa, "check_sources",
                              return_value={"gamecube": root/"core.so"}):
                with self.assertRaisesRegex(ValueError, "overwrite"):
                    qa.execute(root, root/"receipt", "b"*40, root/"result.json")

    def test_unvalidated_git_revision_cannot_launch_compiler(self):
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "Git SHA"):
                qa.execute(td, td, "bad-sha", Path(td)/"new.json")


if __name__ == "__main__":
    unittest.main()
