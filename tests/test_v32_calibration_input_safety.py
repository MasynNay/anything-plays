"""Safety: guided calibration never arms camera-controlled gameplay."""

import unittest

from anything_plays.ui_gameplay import GameplayMixin


class Status:
    def __init__(self):
        self.message = ""
    def set(self, value):
        self.message = value


class FakeApp:
    def __init__(self, *, guide_open, armed):
        self._calibration_window = object() if guide_open else None
        self.armed = armed
        self.action = Status()
        self.stops = 0

    def stop_controls(self):
        self.armed = False
        self.stops += 1

    def uses_embedded_emulator(self):
        raise AssertionError("Calibration must not evaluate or arm a backend")


class CalibrationInputSafetyTests(unittest.TestCase):
    def test_nonmodal_guide_prevents_camera_arm(self):
        app = FakeApp(guide_open=True, armed=False)
        GameplayMixin.toggle(app)
        self.assertFalse(app.armed)
        self.assertEqual(app.stops, 0)
        self.assertIn("Finish or cancel calibration", app.action.message)

    def test_stop_is_always_available_even_during_calibration(self):
        app = FakeApp(guide_open=True, armed=True)
        GameplayMixin.toggle(app)
        self.assertFalse(app.armed)
        self.assertEqual(app.stops, 1)


if __name__ == "__main__":
    unittest.main()
