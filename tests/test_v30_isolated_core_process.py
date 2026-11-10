"""Regression contracts for opt-in, non-public 2D subprocess Libretro research."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from anything_plays.n64_process import (
    INPUT_COUNT, MAX_VIDEO_BYTES, MAX_VIDEO_HEIGHT, MAX_VIDEO_WIDTH,
    PORT_STRIDE, ChildEmulator, ExperimentalSoftwareCoreProcessSession,
    MacN64ProcessSession, SharedN64Inputs,
)
from tools import probe_v30_isolated_sega_process as experiment


class ExperimentalCoreProcessContracts(TestCase):
    def test_parent_preserves_existing_n64_runtime_identity(self):
        existing = MacN64ProcessSession(object(), "test.z64", "original.so")
        self.assertEqual(existing.system, "n64")
        self.assertEqual(MAX_VIDEO_BYTES, MAX_VIDEO_WIDTH * MAX_VIDEO_HEIGHT * 3)
        self.assertEqual(INPUT_COUNT, PORT_STRIDE * 2)

    def test_only_existing_2d_libretro_profiles_can_opt_in(self):
        emu = object()
        for system in ("mastersystem", "gamegear", "sg1000", "genesis", "snes", "gb"):
            bridge = ExperimentalSoftwareCoreProcessSession(
                emu, system, "temporary.rom", "experimental.so")
            self.assertEqual(bridge.system, system)
        for system in ("gamecube", "n64", "", "unregistered", None):
            with self.subTest(system=system), self.assertRaises(ValueError):
                ExperimentalSoftwareCoreProcessSession(
                    emu, system, "temporary.rom", "experimental.so")

    def test_shared_inputs_do_not_cross_ports_or_read_invalid_devices(self):
        values = [0] * INPUT_COUNT
        values[8] = 1
        values[PORT_STRIDE + 0] = 1
        values[PORT_STRIDE + 16] = 12345
        inputs = SharedN64Inputs(values, "mastersystem")
        self.assertEqual(inputs.system, "mastersystem")
        self.assertEqual(inputs.state(0, 1, 0, 8), 1)
        self.assertEqual(inputs.state(0, 1, 0, 0), 0)
        self.assertEqual(inputs.state(1, 1, 0, 0), 1)
        self.assertEqual(inputs.state(1, 5, 0, 0), 12345)
        self.assertEqual(inputs.state(2, 1, 0, 8), 0)
        self.assertEqual(inputs.state(0, 6, 0, 8), 0)

    def test_child_facade_tracks_chosen_console_without_core_loading(self):
        class Box:
            value = 0.25
        child = ChildEmulator([0] * INPUT_COUNT, None, Box(), Box(), "snes")
        self.assertTrue(child.isolated_process)
        self.assertEqual(child.inputs.system, "snes")
        self.assertEqual(child.volume, 0.25)

    def test_probe_rejects_missing_native_and_invalid_duration(self):
        with TemporaryDirectory() as tmp:
            suffix = experiment.EXT.get(__import__("sys").platform, ".so")
            path = Path(tmp) / ("dummy" + suffix)
            with self.assertRaises(ValueError):
                experiment.probe(path)
            path.write_bytes(b"synthetic-test-not-a-real-core")
            for seconds in (0, 4, 16, 100):
                with self.assertRaises(ValueError):
                    experiment.probe(path, seconds)

    def test_research_manifest_never_claims_legal_or_hardware_acceptance(self):
        with TemporaryDirectory() as tmp:
            suffix = experiment.EXT.get(__import__("sys").platform, ".so")
            path = Path(tmp) / ("synthetic" + suffix)
            path.write_bytes(b"not-a-native-library")
            example = {
                "worker_terminated": True, "gameplay_started": True,
                "captured_rgb_frames": 50, "nonblank_rgb_frames": 30,
                "distinct_rgb_frames": 4, "worker_errors": [],
                "passed": True, "physical_audio_verified": False,
                "retail_controller_compatibility_verified": False,
            }
            with mock.patch.object(experiment, "one_playback", return_value=example) as play:
                result = experiment.probe(path, 5)
            self.assertEqual(play.call_count, 2)
            self.assertEqual(result["process_cycles"], 2)
            self.assertTrue(result["passed"])
            self.assertEqual(result["status"], experiment.STATUS)
            for key in ("physical_camera_controls_verified",
                        "physical_speaker_audio_verified", "save_reload_verified",
                        "legal_separation_or_aggregation_approved",
                        "combined_license_review_complete",
                        "public_binary_distribution_approved"):
                self.assertIs(result[key], False, key)

    def test_opt_in_research_does_not_change_default_emulator_selection(self):
        root = Path(__file__).resolve().parents[1]
        facade = (root / "anything_plays/gba_emulator.py").read_text("utf-8")
        self.assertIn("MacN64ProcessSession(self, self.rom, self.core_path).run()", facade)
        self.assertNotIn("ExperimentalSoftwareCoreProcessSession", facade)
        workflow = (root / "docs/history/workflows/v30-gpl-four-os-source-build.yml").read_text("utf-8")
        self.assertIn("tools/probe_v30_isolated_sega_process.py", workflow)
        self.assertIn("matrix.candidate == 'blastem'", workflow)
        self.assertIn("ISOLATED_SEGA_PROCESS_UNAPPROVED.json", workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("continue-on-error: true", workflow)


if __name__ == "__main__":
    import unittest
    unittest.main()
