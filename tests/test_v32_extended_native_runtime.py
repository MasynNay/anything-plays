"""Strict privacy, provenance and failure semantics for final four 3.2 profiles."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from tools import v32_extended_native_runtime as qa


def valid_raw(profile):
    if profile == "ngp":
        return {
            "mono_cartridge_header_value": 0,
            "full_native_audio_video_input_verified": True,
            "changing_monochrome_video_verified_in_native_test": True,
            "audio_verified_in_native_test": True,
            "native_manual_and_camera_input_query_verified": True,
            "native_metrics": {"passed": True, "native_audio_frames": 1024},
        }
    if profile == "ngpc":
        return {
            "probe_passed": True,
            "fixture": {
                "header_matches_test_target": True,
                "header_mode_byte": 0x10,
                "license": "MIT",
                "git_blob_sha1": qa.FIXTURES["ngpc"]["blob_sha1"],
            },
            "details": {
                "passed": True, "video_gate_passed": True,
                "audio_gate_passed": True, "input_gate_passed": True,
                "native_video_frames": 75,
            },
        }
    if profile == "n64":
        return {
            "probe_passed": True,
            "source": {"sha256": qa.ROM_SHA256},
            "details": {
                "playback_probe_passed": True, "frames_valid": True,
                "video_callback_frames": 14,
            },
        }
    if profile == "gamecube":
        return {
            "probe_passed": True,
            "fixture_sha256": "a" * 64,
            "details": {
                "playback_probe_passed": True,
                "static_homebrew_interactive_passed": True,
                "controller_input_exercised": True,
                "video_callback_frames": 42,
            },
        }
    raise KeyError(profile)


class ExtendedNativeProbeTests(unittest.TestCase):
    def test_profiles_have_actual_installed_libretro_names(self):
        self.assertEqual(qa.TARGETS, ("ngp", "ngpc", "n64", "gamecube"))
        self.assertEqual(set(qa.TARGETS), set(qa.CORES))
        self.assertEqual(qa.CORES["ngp"], qa.CORES["ngpc"])
        self.assertEqual(qa.CORES["n64"], "parallel_n64")
        self.assertEqual(qa.CORES["gamecube"], "dolphin")
        self.assertEqual(qa.FIXTURE_ORIGIN["ngp"],
                         "source_generated_original_monochrome")
        for name in qa.TARGETS:
            self.assertGreater(qa.TIMEOUTS[name], qa.SECONDS[name])

    def test_original_and_pinned_provenance_pass_only_exact_real_evidence(self):
        for name in qa.TARGETS:
            with self.subTest(name=name):
                self.assertTrue(qa._verified(name, valid_raw(name), 0))
                self.assertFalse(qa._verified(name, valid_raw(name), -11))
                self.assertFalse(qa._verified(name, {}, 0))
                self.assertTrue(qa.safe_evidence(
                    name, valid_raw(name), 0, False,
                )["native_probe_verified"])
                self.assertFalse(qa.safe_evidence(
                    name, valid_raw(name), 0, True,
                )["native_probe_verified"])

    def test_no_false_mono_header_or_color_header_acceptance(self):
        mono = valid_raw("ngp")
        mono["mono_cartridge_header_value"] = 0x10
        self.assertFalse(qa._verified("ngp", mono, 0))
        color = valid_raw("ngpc")
        color["fixture"]["header_mode_byte"] = 0
        self.assertFalse(qa._verified("ngpc", color, 0))
        color = valid_raw("ngpc")
        color["fixture"]["git_blob_sha1"] = "0" * 40
        self.assertFalse(qa._verified("ngpc", color, 0))

    def test_n64_exact_pinned_binary_and_native_video_are_required(self):
        raw = valid_raw("n64")
        raw["source"]["sha256"] = "0" * 64
        self.assertFalse(qa._verified("n64", raw, 0))
        raw = valid_raw("n64")
        raw["details"]["video_callback_frames"] = 0
        self.assertFalse(qa._verified("n64", raw, 0))

    def test_dolphin_requires_native_input_driven_frame_evidence(self):
        raw = valid_raw("gamecube")
        raw["details"]["controller_input_exercised"] = False
        self.assertFalse(qa._verified("gamecube", raw, 0))
        raw = valid_raw("gamecube")
        raw["details"]["static_homebrew_interactive_passed"] = False
        self.assertFalse(qa._verified("gamecube", raw, 0))

    def test_report_sanitizes_paths_log_tails_and_private_game_names(self):
        for system in qa.TARGETS:
            raw = valid_raw(system)
            raw.update({
                "console_tail": "/Users/private/roms/my-private-file.z64",
                "error": "hidden camera device filename",
                "fixture_url": "https://private.invalid/secret",
            })
            evidence = qa.safe_evidence(system, raw, -1, False)
            encoded = json.dumps(evidence)
            for secret in ("my-private-file", "Users/private",
                           "hidden camera", "private.invalid",
                           "console_tail", "fixture_url"):
                self.assertNotIn(secret, encoded)
            self.assertIs(evidence["public_release_approved"], False)
            self.assertIs(evidence["real_user_gameplay_tested"], False)

    def test_command_lines_use_pinned_original_probes_not_real_roms(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            for system in qa.TARGETS:
                with self.subTest(system=system):
                    cmd, target = qa.command_for(
                        system, folder/"core.so", folder/"out.json",
                        qa.SECONDS[system], folder,
                    )
                    self.assertEqual(cmd[0], __import__("sys").executable)
                    self.assertTrue(cmd[2].startswith("tools.probe_"))
                    self.assertTrue(str(target).startswith(str(folder)))
            cmd, _ = qa.command_for(
                "gamecube", folder/"core.so", folder/"out.json", 12, folder,
            )
            self.assertIn("--single-core", cmd)
            self.assertIn("--exercise-controls", cmd)
            with self.assertRaisesRegex(ValueError, "Unknown"):
                qa.command_for("switch", folder/"core.so", folder/"x", 6, folder)

    def test_exact_installer_cores_must_exist_not_links(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            with patch.object(qa, "check_preflight", return_value=folder):
                with self.assertRaisesRegex(ValueError, "native"):
                    qa.check_sources(folder, folder/"receipt", "b" * 40)
            for native in set(qa.CORES.values()):
                (folder/(native+"_libretro.so")).write_bytes(b"core" * 300)
            with patch.object(qa, "check_preflight", return_value=folder):
                found = qa.check_sources(folder, folder/"receipt", "b" * 40)
            self.assertEqual(set(found), set(qa.TARGETS))
            bad = folder/"dolphin_libretro.so"
            bad.unlink()
            bad.symlink_to(folder/"parallel_n64_libretro.so")
            with patch.object(qa, "check_preflight", return_value=folder):
                with self.assertRaisesRegex(ValueError, "unsafe"):
                    qa.check_sources(folder, folder/"receipt", "b" * 40)

    def test_partial_or_failed_research_not_mislabeled_as_18_supported(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            file = folder/"research.json"
            def run(system, _core, _home):
                if system in ("ngp", "ngpc"):
                    return qa.safe_evidence(system, valid_raw(system), 0, False)
                return qa.safe_evidence(system, {}, -11, False)
            with patch.object(qa, "check_sources",
                              return_value={s:folder for s in qa.TARGETS}):
                record = qa.execute(folder, folder/"receipt", "b" * 40,
                                    file, run=run)
            self.assertEqual(record["profiles_attempted"], 4)
            self.assertEqual(record["exploratory_profiles_verified"], 2)
            self.assertFalse(record["all_four_exploratory_verified"])
            self.assertFalse(record["all_18_consoles_gameplay_verified"])
            self.assertFalse(record["public_release_approved"])
            self.assertFalse(record["physical_controller_tested"])
            self.assertEqual(len(record["probe_results"]), 4)
            self.assertEqual(json.loads(file.read_text())["status"], qa.STATUS)
            with patch.object(qa, "check_sources",
                              return_value={s:folder for s in qa.TARGETS}):
                with self.assertRaisesRegex(ValueError, "overwrite"):
                    qa.execute(folder, folder/"receipt", "b" * 40, file, run=run)

    def test_forged_source_revision_refused_before_native_load(self):
        with self.assertRaisesRegex(ValueError, "Exact"):
            qa.execute("/unused", "/unused", "bad-sha", "/unused")
        self.assertEqual(len(qa.PINNED_SHA256), 64)


if __name__ == "__main__":
    unittest.main()
