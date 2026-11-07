"""Regression coverage for the camera-side label sizing control."""
import unittest

import numpy as np

from anything_plays.zone_rendering import render_zone_overlay


class ControlLabelSizingTests(unittest.TestCase):
    def test_large_label_does_not_cover_neighboring_zones(self):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        zones = {"C Right": (0.25, 0.25, 0.50, 0.50)}
        for size in (8, 28, 50, 160):
            with self.subTest(size=size):
                output = render_zone_overlay(
                    frame, zones, {"C Right": "C Right"}, None,
                    opacity=85, size=size, style="Bold",
                )
                self.assertEqual(output.shape, frame.shape)
                # Text and its backdrop must stay within the marked zone.
                self.assertFalse(np.any(output[:55, :, :]))
                self.assertFalse(np.any(output[125:, :, :]))
                self.assertFalse(np.any(output[:, :75, :]))
                self.assertFalse(np.any(output[:, 165:, :]))
                self.assertTrue(np.any(output[60:120, 80:160, :]))


if __name__ == "__main__":
    unittest.main()
