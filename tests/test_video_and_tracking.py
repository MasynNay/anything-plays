"""Pixel format, color tracking, and preview overlay regression tests."""

import ctypes as C
import unittest

import cv2
import numpy as np

from anything_plays.libretro_video import RGB1555, RGB565, XRGB8888, decode_frame
from anything_plays.tracking import locate_target, zone_at
from anything_plays.zone_rendering import render_zone_overlay


class VideoDecoderTests(unittest.TestCase):
    def test_rgb565_and_padded_row(self):
        raw = C.create_string_buffer(bytes.fromhex("00f8e0070000"))
        frame = decode_frame(raw, 2, 1, 6, RGB565)
        self.assertEqual(frame.tolist(), [[[255, 0, 0], [0, 255, 0]]])

    def test_rgb1555(self):
        raw = C.create_string_buffer(bytes.fromhex("1f00"))
        self.assertEqual(decode_frame(raw, 1, 1, 2, RGB1555)[0, 0].tolist(),
                         [0, 0, 255])

    def test_xrgb8888(self):
        raw = C.create_string_buffer(bytes.fromhex("56341200"))
        self.assertEqual(decode_frame(raw, 1, 1, 4, XRGB8888)[0, 0].tolist(),
                         [18, 52, 86])

    def test_invalid_pitch_rejected(self):
        raw = C.create_string_buffer(6)
        with self.assertRaises(ValueError):
            decode_frame(raw, 2, 1, 2, XRGB8888)
        self.assertIsNone(decode_frame(None, 0, 0, 0, RGB565))


class TrackingTests(unittest.TestCase):
    def test_largest_target_is_detected(self):
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        cv2.rectangle(frame, (30, 20), (70, 70), (0, 0, 255), -1)
        center, contour = locate_target(frame, [255, 0, 0], 20, 60)
        self.assertIsNotNone(contour)
        self.assertLessEqual(abs(center[0] - 50), 1)
        self.assertLessEqual(abs(center[1] - 45), 1)

    def test_disabled_zones_are_not_triggered(self):
        zones = {"A": [0, 0, .5, 1], "Shuffle": [.5, 0, 1, 1]}
        mapping = {"A": "(None)"}
        self.assertIsNone(zone_at((10, 50), (100, 100), zones, mapping, True))
        self.assertIsNone(zone_at((80, 50), (100, 100), zones, mapping, False))
        self.assertEqual(zone_at((80, 50), (100, 100), zones, mapping, True),
                         "Shuffle")

    def test_zone_overlay_does_not_mutate_input(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        original = frame.copy()
        rendered = render_zone_overlay(
            frame, {"A": [.1, .1, .8, .8]}, {"A": "A"}, "A",
            opacity=90, size=18, style="High contrast",
        )
        self.assertEqual(rendered.shape, frame.shape)
        self.assertTrue(np.array_equal(frame, original))
        self.assertTrue(np.any(rendered != frame))


if __name__ == "__main__":
    unittest.main()
