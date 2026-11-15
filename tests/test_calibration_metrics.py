"""Pure calibration feedback tests; no cameras, GUI or private frame data."""

import unittest

from anything_plays.calibration_metrics import calibration_summary


class CalibrationMetricsTests(unittest.TestCase):
    def test_empty_window_is_safe(self):
        report = calibration_summary([])
        self.assertEqual(report["frames"], 0)
        self.assertEqual(report["detection_percent"], 0)
        self.assertEqual(report["zone_hits"], {})
        self.assertIsNone(report["average_motion_px"])

    def test_tracks_visibility_and_zone_activity(self):
        observations = [
            ((0, 0), "Up"),
            ((3, 4), "Up"),
            (None, None),
            ((5, 5), "A"),
        ]
        report = calibration_summary(observations)
        self.assertEqual(report["frames"], 4)
        self.assertEqual(report["seen"], 3)
        self.assertEqual(report["lost"], 1)
        self.assertEqual(report["detection_percent"], 75)
        self.assertEqual(report["zone_hits"], {"A": 1, "Up": 2})
        self.assertEqual(report["average_motion_px"], 5)

    def test_loss_breaks_motion_span(self):
        report = calibration_summary([
            ((0, 0), None), (None, None), ((50, 50), None),
            ((53, 54), "Right"),
        ])
        self.assertEqual(report["average_motion_px"], 5)
        self.assertEqual(report["zone_hits"]["Right"], 1)

    def test_all_lost_frames_do_not_divide_by_zero(self):
        report = calibration_summary([(None, None)] * 6)
        self.assertEqual(report["seen"], 0)
        self.assertEqual(report["lost"], 6)
        self.assertIsNone(report["average_motion_px"])

    def test_output_does_not_contain_pixels_or_camera_identifiers(self):
        report = calibration_summary([((10, 12), "B")])
        self.assertEqual(
            set(report),
            {"frames", "seen", "lost", "detection_percent",
             "zone_hits", "average_motion_px"},
        )
        self.assertEqual(report["zone_hits"], {"B": 1})


if __name__ == "__main__":
    unittest.main()
