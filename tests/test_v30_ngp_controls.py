"""Beetle NeoPop physical A/B, manual and camera controller regression tests.

The upstream core labels NGP 'A' as RETRO_DEVICE_ID_JOYPAD_B (0)
and NGP 'B' as RETRO_DEVICE_ID_JOYPAD_A (8). These tests check both
the input buffer and the native acceptance probe's button contract.
"""
import unittest
from pathlib import Path

from anything_plays.libretro_input import IDS, InputBuffer, NEO_GEO_POCKET_IDS


class NeoGeoPocketControllerTests(unittest.TestCase):
    def test_physical_a_b_are_reversed_relative_to_general_retropad(self):
        self.assertEqual(NEO_GEO_POCKET_IDS["A"], IDS["B"])
        self.assertEqual(NEO_GEO_POCKET_IDS["B"], IDS["A"])
        self.assertEqual(NEO_GEO_POCKET_IDS["Start"], IDS["Start"])
        for system in ("ngp", "ngpc"):
            with self.subTest(system=system):
                inp = InputBuffer()
                inp.system = system
                self.assertEqual(inp.id_for("A"), IDS["B"])
                self.assertEqual(inp.id_for("B"), IDS["A"])
                self.assertEqual(inp.id_for("Select"), None)
                for arrow in ("Up", "Down", "Left", "Right"):
                    self.assertEqual(inp.id_for(arrow), IDS[arrow])

    def test_manual_a_survives_disarmed_camera_and_releases_cleanly(self):
        for system in ("ngp", "ngpc"):
            with self.subTest(system=system):
                inp = InputBuffer()
                inp.system = system
                inp.set_manual("A", True)
                inp.queue_press("B", 12)
                inp.before_frame(armed=False)
                self.assertEqual(inp.state(0, 1, 0, IDS["B"]), 1)
                self.assertEqual(inp.state(0, 1, 0, IDS["A"]), 0)
                inp.after_frame()
                inp.release_manual()
                inp.before_frame(armed=False)
                self.assertEqual(inp.state(0, 1, 0, IDS["B"]), 0)

    def test_camera_b_pulse_is_finite_and_does_not_hold_a(self):
        for system in ("ngp", "ngpc"):
            with self.subTest(system=system):
                inp = InputBuffer()
                inp.system = system
                inp.queue_press("B", 2)
                for _ in range(2):
                    inp.before_frame(armed=True)
                    self.assertEqual(inp.state(0, 1, 0, IDS["A"]), 1)
                    self.assertEqual(inp.state(0, 1, 0, IDS["B"]), 0)
                    inp.after_frame()
                inp.before_frame(armed=True)
                self.assertEqual(inp.state(0, 1, 0, IDS["A"]), 0)
                self.assertEqual(inp.state(1, 1, 0, IDS["A"]), 0)
                self.assertEqual(inp.state(0, 2, 0, IDS["A"]), 0)

    def test_native_probe_queries_the_reversed_identities(self):
        script = (
            Path(__file__).resolve().parents[1]
            / "tools/probe_ngp_mit_homebrew.py"
        ).read_text("utf-8")
        self.assertIn('identity == IDS["B"]', script)
        self.assertIn('identity == IDS["A"]', script)
        self.assertIn('and video_ok and audio_ok and input_ok', script)


if __name__ == "__main__":
    unittest.main()
