"""3.2 native acceptance summary: 18 distinct profiles, NO release approval."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools import v32_acceptance_matrix as qa
from tools import v32_original_native_runtime as original
from tools import v32_extended_native_runtime as extended

SHA = "d" * 40


def fixtures():
    first = []
    for system, (core, _, _) in original.CASES.items():
        first.append({
            "system": system,
            "core_name": core,
            "required_gate": system in original.REQUIRED,
            "native_child_exit_zero": True,
            "timed_out": False,
            "probe_passed": True,
        })
    source = {
        "schema_version": 1,
        "status": original.STATUS,
        "source_revision": SHA,
        "binary_tested": "installed full-native 3.2 Linux core payload",
        "profiles_in_native_inventory": 18,
        "native_core_families_in_inventory": 11,
        "original_source_generated_homebrew_only": True,
        "all_18_consoles_gameplay_verified": False,
        "commercial_game_compatibility_verified": False,
        "public_release_approved": False,
        "required_profiles_tested": list(original.REQUIRED),
        "exploratory_profiles_tested": list(original.EXPLORATORY),
        "required_profiles_passed": 6,
        "exploratory_profiles_passed": 8,
        "passed": True,
        "probes": first,
    }
    more = []
    for system in extended.TARGETS:
        row = {
            "profile": system,
            "native_core": extended.CORES[system],
            "is_exploratory": True,
            "native_probe_verified": True,
            "native_process_exit_code": 0,
            "timed_out": False,
        }
        if system == "ngpc":
            row.update({
                "native_parent_probe_passed": True,
                "native_child_report_passed": True,
                "native_inner_exit_code": 0,
                "fixture_blob_matches_pinned_source": True,
                "fixture_color_mode_confirmed": True,
                "video_gate_passed": True,
                "audio_gate_passed": True,
                "input_gate_passed": True,
            })
        if system == "gamecube":
            row.update({
                "headless_20fps_threshold_met": False,
                "real_nonzero_pcm_observed": False,
                "production_gpu_backend_exercised": True,
            })
        more.append(row)
    last = {
        "schema_version": 1,
        "status": extended.STATUS,
        "source_revision": SHA,
        "installed_binary_checked": "exact-source full-native Linux 3.2 QA install",
        "profiles": list(extended.TARGETS),
        "profiles_attempted": 4,
        "remaining_three_fixtures_hash_pinned_in_repo": True,
        "all_18_consoles_gameplay_verified": False,
        "commercial_game_compatibility_verified": False,
        "public_release_approved": False,
        "exploratory_profiles_verified": 4,
        "all_four_exploratory_verified": True,
        "probe_results": more,
    }
    return source, last


class AcceptanceMatrixTests(unittest.TestCase):
    def test_all_18_native_software_test_profiles_distinct_and_private(self):
        original_data, extra_data = fixtures()
        result = qa.consolidate(original_data, extra_data, SHA)
        self.assertEqual(result["native_software_profiles_tested"], 18)
        self.assertEqual(result["native_software_profiles_with_positive_evidence"], 18)
        self.assertTrue(result["all_18_bounded_homebrew_software_smokes_positive"])
        self.assertEqual(len(set(row["console_profile"] for row in
                                 result["per_console_results"])), 18)
        self.assertEqual(result["source_built_native_core_families_in_package"], 11)
        self.assertFalse(result["gamecube_headless_20fps_met"])
        self.assertFalse(result["gamecube_test_homebrew_nonzero_audio_observed"])
        for key in (
            "public_release_approved", "ready_for_public_3_2_release",
            "all_18_consoles_commercial_gameplay_verified",
            "all_18_consoles_sustained_gameplay_verified",
            "all_four_os_real_gameplay_verified",
            "physical_usb_bluetooth_gamepads_verified",
            "physical_camera_input_verified",
            "physical_speaker_playback_verified",
            "game_save_long_session_verified",
            "public_native_core_redistribution_approved",
            "macos_notarization_verified",
        ):
            self.assertIs(result[key], False, key)

    def test_partial_native_result_stays_incomplete(self):
        first, extra = fixtures()
        extra["probe_results"][-1]["native_probe_verified"] = False
        extra["probe_results"][-1]["native_process_exit_code"] = -11
        extra["exploratory_profiles_verified"] = 3
        extra["all_four_exploratory_verified"] = False
        result = qa.consolidate(first, extra, SHA)
        self.assertEqual(result["native_software_profiles_with_positive_evidence"], 17)
        self.assertFalse(result["all_18_bounded_homebrew_software_smokes_positive"])
        self.assertFalse(result["per_console_results"][-1]["native_software_smoke_passed"])

    def test_required_original_crash_is_not_accepted(self):
        first, extra = fixtures()
        first["probes"][0]["probe_passed"] = False
        first["probes"][0]["native_child_exit_zero"] = False
        first["required_profiles_passed"] = 5
        first["passed"] = False
        result = qa.consolidate(first, extra, SHA)
        self.assertFalse(result["original_14_profile_baseline_gate_passed"])
        self.assertEqual(result["native_software_profiles_with_positive_evidence"], 17)
        first["passed"] = True
        with self.assertRaisesRegex(ValueError, "disagree"):
            qa.consolidate(first, extra, SHA)

    def test_prevent_false_positive_timeouts_in_either_native_report(self):
        first, extra = fixtures()
        first["probes"][0]["timed_out"] = True
        with self.assertRaisesRegex(ValueError, "crashed"):
            qa.consolidate(first, extra, SHA)
        first, extra = fixtures()
        extra["probe_results"][0]["native_process_exit_code"] = -11
        with self.assertRaisesRegex(ValueError, "crash"):
            qa.consolidate(first, extra, SHA)

    def test_forged_identity_counts_or_approval_fail_closed(self):
        for key, value in (
            ("source_revision", "a" * 40),
            ("profiles_in_native_inventory", 99),
            ("public_release_approved", True),
            ("original_source_generated_homebrew_only", False),
        ):
            with self.subTest(key=key):
                first, extra = fixtures()
                first[key] = value
                with self.assertRaises(ValueError):
                    qa.consolidate(first, extra, SHA)
        for key, value in (
            ("source_revision", "a" * 40),
            ("public_release_approved", True),
            ("profiles_attempted", 3),
            ("remaining_three_fixtures_hash_pinned_in_repo", False),
        ):
            with self.subTest(key=key):
                first, extra = fixtures()
                extra[key] = value
                with self.assertRaises(ValueError):
                    qa.consolidate(first, extra, SHA)

    def test_ngpc_evidence_requires_true_parent_child_and_pinned_fixture(self):
        for field, bad in (
            ("native_parent_probe_passed", False),
            ("native_child_report_passed", False),
            ("native_inner_exit_code", -11),
            ("fixture_blob_matches_pinned_source", False),
            ("fixture_color_mode_confirmed", False),
            ("input_gate_passed", False),
        ):
            with self.subTest(field=field):
                first, extra = fixtures()
                row = extra["probe_results"][1]
                row[field] = bad
                with self.assertRaisesRegex(ValueError, "NGPC"):
                    qa.consolidate(first, extra, SHA)

    def test_gamecube_requires_actual_production_gpu_backend(self):
        first, extra = fixtures()
        extra["probe_results"][-1]["production_gpu_backend_exercised"] = False
        with self.assertRaisesRegex(ValueError, "GameCube"):
            qa.consolidate(first, extra, SHA)

    def test_wrong_order_duplicate_console_or_forged_core_refused(self):
        first, extra = fixtures()
        first["probes"][0]["system"] = "gba"
        with self.assertRaises(ValueError):
            qa.consolidate(first, extra, SHA)
        first, extra = fixtures()
        extra["probe_results"][-1]["native_core"] = "snes9x"
        with self.assertRaisesRegex(ValueError, "emulator"):
            qa.consolidate(first, extra, SHA)
        first, extra = fixtures()
        extra["profiles"] = ["ngp", "ngpc", "n64", "n64"]
        with self.assertRaises(ValueError):
            qa.consolidate(first, extra, SHA)

    def test_strict_type_guards_disallow_numeric_fake_booleans(self):
        first, extra = fixtures()
        first["probes"][0]["probe_passed"] = 1
        with self.assertRaisesRegex(ValueError, "Boolean"):
            qa.consolidate(first, extra, SHA)
        first, extra = fixtures()
        extra["probe_results"][-1]["native_probe_verified"] = 1
        with self.assertRaisesRegex(ValueError, "Boolean"):
            qa.consolidate(first, extra, SHA)

    def test_no_sensitive_user_input_in_summary(self):
        first, extra = fixtures()
        first["probes"][0]["console_tail"] = "/Users/alice/private/game.gba"
        extra["probe_results"][-1]["crash_log"] = "/home/alice/private"
        extra["probe_results"][-1]["user_camera_device"] = "private cam"
        matrix = qa.consolidate(first, extra, SHA)
        payload = json.dumps(matrix)
        for key in ("Users/alice", "private", "crash_log", "console_tail",
                    "user_camera_device"):
            self.assertNotIn(key, payload)

    def test_write_untrusted_path_refused_and_file_is_not_overwritten(self):
        first, extra = fixtures()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p, q = root/"first.json", root/"extra.json"
            out = root/"matrix.json"
            p.write_text(json.dumps(first), "utf-8")
            q.write_text(json.dumps(extra), "utf-8")
            result = qa.generate(p, q, SHA, out)
            self.assertTrue(result["all_18_bounded_homebrew_software_smokes_positive"])
            self.assertEqual(json.loads(out.read_text())["status"], qa.STATUS)
            with self.assertRaisesRegex(ValueError, "overwrite"):
                qa.generate(p, q, SHA, out)
            out.unlink()
            out.symlink_to(p)
            with self.assertRaisesRegex(ValueError, "overwrite"):
                qa.generate(p, q, SHA, out)

    def test_invalid_sha_fails_before_counting_results(self):
        first, extra = fixtures()
        with self.assertRaisesRegex(ValueError, "Git SHA"):
            qa.consolidate(first, extra, "NOT-A-SHA")


if __name__ == "__main__":
    unittest.main()
