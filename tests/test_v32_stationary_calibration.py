"""3.2 still-target jitter checks: observed positions, never accuracy claims.

Only synthetic center coordinates enter these tests. No webcam, actual
color-tracker frames, private images, input devices, or ROM are involved.
"""

from collections import deque
import math
import unittest
from unittest.mock import patch

from anything_plays.calibration_metrics import stationary_tracking_summary

# Native installer PREflight intentionally runs before full OpenCV packaging
# dependencies are installed. Pure math must run on all four OSes, while the
# Tk lifecycle is tested in source CI (with OpenCV) and the actual frozen GUI.
try:
    from anything_plays.ui_calibration import (
        CalibrationMixin, STATIONARY_SAMPLE_FRAMES,
    )
except ModuleNotFoundError as exc:
    if exc.name != "cv2":
        raise
    CalibrationMixin = object
    STATIONARY_SAMPLE_FRAMES = 45
    UI_AVAILABLE = False
else:
    UI_AVAILABLE = True


class Value:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeWizard(CalibrationMixin):
    def __init__(self):
        self._calibration_window = object()
        self._calibration_sampled = True
        self._calibration_step = 2
        self.cap = object()  # synthetic sentinel, not a video capture
        self.cfg = {"zones": {}}
        self.shuffle_enabled = Value(False)
        self._calibration_history = deque(maxlen=90)
        self._calibration_stability_history = deque(
            maxlen=STATIONARY_SAMPLE_FRAMES,
        )
        self._calibration_stability_running = False
        self._calibration_stability_result = None
        self._calibration_stability_status = Value()
        self._calibration_diagnostics = Value()
        self.render_calls = 0

    def _calibration_render_step(self):
        self.render_calls += 1


class StillTargetMetricsTests(unittest.TestCase):
    def test_still_target_has_zero_observed_position_variation(self):
        report = stationary_tracking_summary([(150, 210)] * 45)
        self.assertEqual(
            report,
            {"frames": 45, "seen": 45, "lost": 0,
             "median_deviation_px": 0.0, "p95_deviation_px": 0.0},
        )

    def test_wandering_target_is_not_mislabeled_as_accuracy(self):
        report = stationary_tracking_summary(
            [(0, 0)] * 40 + [(20, 0)] * 5,
        )
        self.assertEqual(report["median_deviation_px"], 0.0)
        self.assertEqual(report["p95_deviation_px"], 20.0)
        self.assertNotIn("accuracy", " ".join(report.keys()))
        self.assertEqual(set(report), {
            "frames", "seen", "lost", "median_deviation_px", "p95_deviation_px",
        })

    def test_too_few_valid_matches_do_not_report_zero_jitter(self):
        report = stationary_tracking_summary(
            [(5, 5)] * 7 + [None] * 38,
        )
        self.assertEqual(report["seen"], 7)
        self.assertEqual(report["lost"], 38)
        self.assertIsNone(report["median_deviation_px"])
        self.assertIsNone(report["p95_deviation_px"])

    def test_nonfinite_and_invalid_points_are_treated_as_missed(self):
        samples = [
            (math.inf, 1), (math.nan, 3), ("bad", 1),
            (1,), None,
        ] + [(3, 4)] * 8
        report = stationary_tracking_summary(samples)
        self.assertEqual(report["seen"], 8)
        self.assertEqual(report["lost"], 5)
        self.assertEqual(report["median_deviation_px"], 0)
        self.assertEqual(report["p95_deviation_px"], 0)

    @unittest.skipUnless(
        UI_AVAILABLE, "OpenCV is not installed during native preflight",
    )
    def test_user_must_explicitly_start_after_sampling_and_camera_start(self):
        guide = FakeWizard()
        guide.cap = None
        guide._calibration_begin_stability()
        self.assertFalse(guide._calibration_stability_running)
        self.assertIn("Start the webcam", guide._calibration_stability_status.get())
        guide.cap = object()
        guide._calibration_sampled = False
        guide._calibration_begin_stability()
        self.assertFalse(guide._calibration_stability_running)
        self.assertIn("Sample", guide._calibration_stability_status.get())

    @unittest.skipUnless(
        UI_AVAILABLE, "OpenCV is not installed during native preflight",
    )
    def test_collects_exactly_45_live_centers_then_stops(self):
        guide = FakeWizard()
        guide._calibration_begin_stability()
        self.assertTrue(guide._calibration_stability_running)
        with patch("anything_plays.ui_calibration.zone_at", return_value="A"):
            for i in range(STATIONARY_SAMPLE_FRAMES + 12):
                guide.calibration_note_frame(
                    [((10, 11), None)], {"A": "A"}, (640, 480),
                )
        self.assertFalse(guide._calibration_stability_running)
        self.assertEqual(len(guide._calibration_stability_history), 45)
        self.assertEqual(guide._calibration_stability_result["seen"], 45)
        self.assertEqual(guide._calibration_stability_result[
            "median_deviation_px"
        ], 0)
        self.assertIn("not a tracking accuracy score",
                      guide._calibration_stability_status.get())

    @unittest.skipUnless(
        UI_AVAILABLE, "OpenCV is not installed during native preflight",
    )
    def test_camera_disconnect_and_color_resample_discards_old_jitter(self):
        guide = FakeWizard()
        guide._calibration_begin_stability()
        with patch("anything_plays.ui_calibration.zone_at", return_value="A"):
            guide.calibration_note_frame(
                [((4, 5), None)], {"A": "A"}, (640, 480),
            )
        guide.calibration_camera_changed()
        self.assertFalse(guide._calibration_stability_running)
        self.assertEqual(len(guide._calibration_stability_history), 0)
        self.assertIsNone(guide._calibration_stability_result)
        self.assertFalse(guide._calibration_sampled)
        guide.cap = object()
        guide.calibration_color_sampled()
        self.assertTrue(guide._calibration_sampled)
        self.assertIn("Check stationary jitter",
                      guide._calibration_stability_status.get())
        self.assertEqual(guide._calibration_stability_history.maxlen, 45)


if __name__ == "__main__":
    unittest.main()
