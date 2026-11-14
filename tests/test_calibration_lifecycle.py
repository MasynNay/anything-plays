"""Calibration guide lifecycle regression without GUI or webcam hardware."""

import unittest
from collections import deque

from anything_plays.ui_calibration import CalibrationMixin


class FakeStatus:
    def __init__(self):
        self.value = ""
    def set(self, message):
        self.value = message


class StubGuide:
    def __init__(self, *, open_window):
        self._calibration_window = object() if open_window else None
        self._calibration_sampled = True
        self._calibration_history = deque(
            [((4, 5), "A"), ((5, 6), "Up")], maxlen=90,
        )
        self._calibration_step = 3
        self._calibration_diagnostics = FakeStatus()
        self.render_calls = 0

    def _calibration_render_step(self):
        self.render_calls += 1


class CalibrationLifecycleTests(unittest.TestCase):
    def test_camera_stop_discards_stale_metrics_and_resets_sampling(self):
        guide = StubGuide(open_window=True)
        CalibrationMixin.calibration_camera_changed(guide)
        self.assertFalse(guide._calibration_sampled)
        self.assertEqual(list(guide._calibration_history), [])
        self.assertEqual(guide._calibration_step, 1)
        self.assertEqual(guide.render_calls, 1)
        self.assertIn("Pick your target color", guide._calibration_diagnostics.value)

    def test_inactive_guide_does_not_modify_state(self):
        guide = StubGuide(open_window=False)
        CalibrationMixin.calibration_camera_changed(guide)
        self.assertTrue(guide._calibration_sampled)
        self.assertEqual(len(guide._calibration_history), 2)
        self.assertEqual(guide._calibration_step, 3)
        self.assertEqual(guide.render_calls, 0)


if __name__ == "__main__":
    unittest.main()
