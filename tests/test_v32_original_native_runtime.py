"""3.2 original-homebrew native runtime gate is truthful and privacy-safe."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import v32_original_native_runtime as qa


def success(system):
    return qa.safe_summary(
        system,
        {"passed": True,
         "console_tail": "/Users/private/ROMs/my-file.nes",
         "details": {
             "native_video_frames": 160,
             "distinct_rgb_frames": 4,
             "native_nonzero_pcm_values": 550,
             "local_rom_path": "/home/private/roms/secret.sfc",
             "error": "/home/private/secret.txt",
         }},
        0, False,
    )


class V32OriginalHomebrewNativeTests(unittest.TestCase):
    def test_four_required_origins_do_not_rely_on_legacy_core_names(self):
        self.assertEqual(qa.REQUIRED, ("gb", "gbc", "gba", "nes"))
        self.assertEqual(qa.CASES["snes"][0], "mednafen_supafaust")
        self.assertEqual(qa.CASES["genesis"][0], "blastem")
        self.assertEqual(qa.CASES["nes"][0], "fceumm")
        self.assertEqual(qa.CASES["gbc"][0], "mgba")
        self.assertEqual(set(qa.CASES), set(qa.REQUIRED) | set(qa.EXPLORATORY))

    def test_strict_success_is_not_misrepresented_as_18_compatible_games(self):
        systems = tuple(qa.CASES)
        reports = [success(system) for system in systems]
        result = qa.analyze_results(reports, systems)
        self.assertTrue(result["passed"])
        self.assertEqual(result["required_profiles_passed"], 4)
        self.assertEqual(result["exploratory_profiles_passed"], 2)
        self.assertEqual(result["profiles_in_native_inventory"], 18)
        for key in ("all_18_consoles_gameplay_verified",
                    "commercial_game_compatibility_verified",
                    "physical_camera_verified",
                    "physical_controller_verified",
                    "physical_speaker_verified",
                    "public_release_approved"):
            self.assertIs(result[key], False, key)

    def test_exploratory_native_failure_is_not_reported_as_success(self):
        systems = tuple(qa.CASES)
        reports = [success(system) for system in systems]
        reports[-1] = qa.safe_summary(
            "genesis", {"passed": False, "error": "sensitive local ROM path"},
            -11, False,
        )
        result = qa.analyze_results(reports, systems)
        self.assertTrue(result["passed"])
        self.assertEqual(result["exploratory_profiles_passed"], 1)
        self.assertFalse(result["probes"][-1]["probe_passed"])

    def test_any_required_native_crash_fails_the_gate(self):
        systems = tuple(qa.CASES)
        reports = [success(system) for system in systems]
        reports[2] = qa.safe_summary("gba", {}, -11, False)
        result = qa.analyze_results(reports, systems)
        self.assertFalse(result["passed"])
        self.assertEqual(result["required_profiles_passed"], 3)

    def test_no_sensitive_console_tail_or_core_path_is_in_output(self):
        report = success("gb")
        self.assertEqual(report["native_video_frames"], 160)
        self.assertEqual(report["native_nonzero_pcm_values"], 550)
        self.assertTrue(report["probe_passed"])
        data = json.dumps(report)
        self.assertNotIn("private", data)
        self.assertNotIn("/home/", data)
        self.assertNotIn("ROMs", data)
        self.assertNotIn("local_rom_path", data)
        self.assertNotIn("error", data)

    def test_no_success_if_process_exits_nonzero_or_times_out(self):
        self.assertFalse(qa.safe_summary("gb", {"passed": True}, 99, False)["probe_passed"])
        self.assertFalse(qa.safe_summary("gb", {}, -1, True)["probe_passed"])
        self.assertTrue(qa.safe_summary("gb", {}, -1, True)["timed_out"])

    def test_unapproved_or_bad_source_revision_fails_before_any_native_core(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fake = root/"test"
            fake.mkdir()
            receipt = root/"receipt.json"
            receipt.write_text("{}", "utf-8")
            with patch.dict("os.environ", {"AP_RELEASE_BUILD": "1",
                                            "AP_V32_PREVIEW_BUILD": "1"}):
                with self.assertRaisesRegex(ValueError, "unreleased"):
                    qa.check_preflight(fake, receipt, "f" * 40, qa.REQUIRED)
            with patch.dict("os.environ", {"AP_V32_PREVIEW_BUILD": "1",
                                            "AP_RELEASE_BUILD": "0",
                                            "AP_V30_APPROVED_RELEASE": "0"}):
                with self.assertRaisesRegex(ValueError, "Exact source"):
                    qa.check_preflight(fake, receipt, "not-a-commit", qa.REQUIRED)
                with self.assertRaisesRegex(ValueError, "Unknown"):
                    qa.check_preflight(fake, receipt, "f" * 40, ("gb", "gb"))
                with patch.object(qa, "validate_staged_identity", return_value=None):
                    with self.assertRaisesRegex(ValueError, "source receipt"):
                        qa.check_preflight(fake, receipt, "f" * 40, qa.REQUIRED)

    def test_result_includes_only_approved_counts_and_no_unrelated_tests(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output = root/"v32-native-original.json"
            systems = tuple(qa.CASES)
            with patch.object(qa, "check_preflight", return_value=root), \
                 patch.object(qa, "run_case", side_effect=lambda cores, system, seconds, home: success(system)):
                self.assertEqual(qa.execute(root, root/"unused", "f" * 40,
                                            output, systems, 3), 0)
            result = json.loads(output.read_text("utf-8"))
            self.assertTrue(result["passed"])
            self.assertTrue(result["original_source_generated_homebrew_only"])
            self.assertEqual(result["source_revision"], "f" * 40)
            self.assertEqual(len(result["probes"]), 6)
            self.assertNotIn("commercial_gameplay_verified", result)
            with patch.object(qa, "check_preflight", return_value=root):
                with self.assertRaisesRegex(ValueError, "overwrite"):
                    qa.execute(root, root/"unused", "f" * 40,
                               output, systems, 3)

    def test_required_system_cannot_be_omitted(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "Required"):
                qa.execute(Path(td), Path(td)/"unused", "f" * 40,
                           Path(td)/"out", ("gb", "gba"), 4)


if __name__ == "__main__":
    unittest.main()
