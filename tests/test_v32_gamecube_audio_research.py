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
