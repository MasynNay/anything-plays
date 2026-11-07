"""3.0 user-facing volume, independent colors and local multiplayer regressions.

The multi-fish option is OFF by default. Older saved profiles inherit this
safe single-object behavior unless the user explicitly opts in.
"""
import ctypes as C
from pathlib import Path
import unittest

import cv2
import numpy as np

from anything_plays.libretro_audio import AudioSink
from anything_plays.libretro_input import (
    IDS, InputBuffer, TWO_PLAYER_SYSTEMS,
)
from anything_plays.settings_defaults import DEFAULT
from anything_plays.system_profiles import normalize, default_for
from anything_plays.tracking import locate_targets, locate_target, zone_at


ROOT = Path(__file__).resolve().parents[1]


class MultiFishTrackingTests(unittest.TestCase):
    def test_multi_fish_is_opt_in_and_color_two_starts_off(self):
        self.assertIs(DEFAULT["multi_fish_enabled"], False)
        self.assertIs(DEFAULT["color2_enabled"], False)
        old = default_for("nes", DEFAULT)
        old.pop("multi_fish_enabled", None)
        old.pop("color2_enabled", None)
        updated = normalize("nes", old, DEFAULT)
        self.assertIs(updated["multi_fish_enabled"], False)
        self.assertIs(updated["color2_enabled"], False)
        self.assertEqual(updated["color2_player"], "Player 2")
        self.assertEqual(updated["camera_input_mode"], "Held while visible")
        updated["multi_fish_enabled"] = True
        self.assertTrue(normalize("nes", updated, DEFAULT)["multi_fish_enabled"])

    def test_single_pink_color_can_drive_two_separate_zones_when_enabled(self):
        frame = np.zeros((110, 200, 3), dtype=np.uint8)
        # OpenCV BGR for bright magenta/pink (RGB 255,30,180).
        pink_bgr = (180, 30, 255)
        cv2.rectangle(frame, (10, 25), (49, 75), pink_bgr, -1)
        cv2.rectangle(frame, (141, 25), (190, 75), pink_bgr, -1)
        original = frame.copy()
        multi = locate_targets(frame, [255, 30, 180], 20, 60)
        single = locate_targets(frame, [255, 30, 180], 20, 60,
                                max_targets=1)
        self.assertEqual(len(multi), 2)
        self.assertEqual(len(single), 1)
        self.assertEqual(locate_target(frame, [255, 30, 180], 20, 60)[0],
                         single[0][0])
        zones = {"A": (0, 0, .35, 1), "B": (.65, 0, 1, 1)}
        selected = {
            zone_at(center, (200, 110), zones, {}, True)
            for center, _ in multi
        }
        self.assertEqual(selected, {"A", "B"})
        self.assertTrue(np.array_equal(frame, original))

    def test_multiple_objects_have_strict_bounded_per_color_cap(self):
        image = np.zeros((320, 320, 3), dtype=np.uint8)
        for row in range(5):
            for col in range(5):
                x, y = 8 + col * 62, 8 + row * 62
                cv2.rectangle(image, (x, y), (x + 20, y + 20),
                              (180, 30, 255), -1)
        self.assertEqual(len(locate_targets(
            image, [255, 30, 180], 20, 25,
        )), 16)
        self.assertEqual(len(locate_targets(
            image, [255, 30, 180], 20, 25, max_targets=1,
        )), 1)


class LocalMultiplayerInputTests(unittest.TestCase):
    def test_one_color_many_fish_presses_multiple_p1_buttons_same_frame(self):
        inputs = InputBuffer()
        inputs.system = "snes"
        inputs.set_camera_buttons(("A", "B"), ())
        inputs.before_frame(True)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(inputs.state(0, 1, 0, IDS["B"]), 1)
        self.assertEqual(inputs.state(1, 1, 0, IDS["A"]), 0)
        inputs.after_frame()
        inputs.set_camera_buttons((), ())
        inputs.before_frame(True)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 0)
        self.assertEqual(inputs.state(0, 1, 0, IDS["B"]), 0)

    def test_two_colors_press_independent_p1_and_p2_same_native_frame(self):
        inputs = InputBuffer()
        inputs.system = "snes"
        inputs.set_camera_buttons(("A", "X"), ("B", "Y"))
        inputs.before_frame(True)
        for button in ("A", "X"):
            self.assertEqual(inputs.state(0, 1, 0, IDS[button]), 1)
            self.assertEqual(inputs.state(1, 1, 0, IDS[button]), 0)
        for button in ("B", "Y"):
            self.assertEqual(inputs.state(1, 1, 0, IDS[button]), 1)
            self.assertEqual(inputs.state(0, 1, 0, IDS[button]), 0)
        inputs.set_camera_buttons(("A",), ())
        inputs.before_frame(True)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 0)
        self.assertEqual(inputs.state(1, 1, 0, IDS["Y"]), 0)
        inputs.disarm()
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 0)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 0)

    def test_n64_and_gamecube_handle_two_separate_analog_controller_ports(self):
        for system in ("n64", "gamecube"):
            with self.subTest(system=system):
                self.assertIn(system, TWO_PLAYER_SYSTEMS)
                inputs = InputBuffer()
                inputs.system = system
                inputs.set_camera_buttons(("A", "Left"), ("B", "Right"))
                inputs.before_frame(True)
                self.assertEqual(inputs.state(0, 1, 0, 8), 1)
                self.assertEqual(inputs.state(1, 1, 0, 0), 1)
                self.assertLess(inputs.state(0, 5, 0, 0), 0)
                self.assertGreater(inputs.state(1, 5, 0, 0), 0)
                inputs.set_camera_buttons((), ())
                inputs.before_frame(True)
                self.assertEqual(inputs.state(1, 1, 0, 0), 0)
                self.assertEqual(inputs.state(1, 5, 0, 0), 0)

    def test_classic_p2_pulses_are_bounded_and_release(self):
        inputs = InputBuffer()
        inputs.system = "nes"
        inputs.queue_press("B", 2, port=1)
        for _ in range(2):
            inputs.before_frame(True)
            self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 1)
            self.assertEqual(inputs.state(0, 1, 0, IDS["B"]), 0)
            inputs.after_frame()
        inputs.before_frame(True)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 0)

    def test_disarmed_camera_never_disarms_manual_p1(self):
        inputs = InputBuffer()
        inputs.system = "gba"
        inputs.set_manual("A", True)
        inputs.set_camera_buttons(("B",), ("A",))
        inputs.before_frame(False)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(inputs.state(0, 1, 0, IDS["B"]), 0)
        self.assertEqual(inputs.state(1, 1, 0, IDS["A"]), 0)


class AppVolumeTests(unittest.TestCase):
    def test_volume_scales_only_output_without_rewriting_native_pcm(self):
        sink = AudioSink()
        sink.set_volume(0.35)
        source = np.array([[1000, -1000], [32767, -32768]], dtype=np.int16)
        sink.push(source)
        actual = np.zeros((2, 2), dtype=np.int16)
        sink.callback(actual, 2, None, None)
        expected = np.rint(source.astype(np.float32) * .35).astype(np.int16)
        np.testing.assert_array_equal(actual, expected)
        np.testing.assert_array_equal(
            source, np.array([[1000, -1000], [32767, -32768]],
                             dtype=np.int16),
        )

    def test_mute_drains_audio_and_unmute_uses_fresh_samples_only(self):
        sink = AudioSink()
        sink.push(np.array([[6000, -6000]], dtype=np.int16))
        sink.set_volume(0)
        silence = np.ones((2, 2), dtype=np.int16)
        sink.callback(silence, 2, None, None)
        self.assertEqual(silence.tolist(), [[0, 0], [0, 0]])
        sink.set_volume(1)
        sink.push(np.array([[300, -300]], dtype=np.int16))
        playing = np.zeros((2, 2), dtype=np.int16)
        sink.callback(playing, 2, None, None)
        self.assertEqual(playing.tolist(), [[300, -300], [0, 0]])

    def test_gain_is_finite_and_clamped(self):
        sink = AudioSink()
        for bad in (None, "", float("nan"), float("inf")):
            sink.set_volume(bad)
            self.assertEqual(sink._volume, 0.35)
        sink.set_volume(900)
        self.assertEqual(sink._volume, 1.0)
        sink.set_volume(-50)
        self.assertEqual(sink._volume, 0.0)

    def test_interface_has_visible_opt_in_and_slider(self):
        panel = (ROOT / "anything_plays/ui_panels.py").read_text("utf-8")
        camera = (ROOT / "anything_plays/ui_camera.py").read_text("utf-8")
        layout = (ROOT / "anything_plays/ui_layout.py").read_text("utf-8")
        assert "Enable multiple fish per color (multi-input)" in panel
        assert "variable=self.multi_fish_enabled" in panel
        assert "limit = 16 if self.multi_fish_enabled.get() else 1" in camera
        assert "variable=self.volume_percent" in layout
        assert "command=self.toggle_game_mute" in layout


if __name__ == "__main__":
    unittest.main()
