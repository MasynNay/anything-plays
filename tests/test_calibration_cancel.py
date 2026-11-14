"""Camera calibration cancellation must not overwrite another console."""

import copy
from collections import deque
import unittest

from anything_plays.ui_calibration import CalibrationMixin


class Value:
    def __init__(self, initial=None):
        self.value = initial
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class Window:
    def __init__(self):
        self.destroyed = False
    def destroy(self):
        self.destroyed = True


class Store:
    def __init__(self):
        self.saved = None
    def put(self, system, profile):
        self.saved = (system, copy.deepcopy(profile))


class FakeApp:
    def __init__(self, current="snes"):
        original = {
            "rgb": [8, 25, 90], "tolerance": 20, "min_area": 120,
            "zones": {"A": [0, 0, 1, 1]}, "mapping": {"A": "B"},
        }
        self._calibration_original = {
            "system": "gb", "profile": original,
            "rgb": list(original["rgb"]),
            "tolerance": original["tolerance"],
            "min_area": original["min_area"],
        }
        self.cfg = {
            "rgb": [255, 255, 0], "tolerance": 90,
            "min_area": 9999, "mapping": {"A": "A"},
        }
        self.system_key = Value(current)
        self.tolerance = Value(90)
        self.min_area = Value(9999)
        self.status = Value()
        self.profile_store = Store()
        self._calibration_window = Window()
        self.window = self._calibration_window
        self._calibration_after = None
        self._calibration_history = deque([(1, "A")], maxlen=90)
        self._closing = False
        self.pick_mode = True
        self.stops = 0
        self.color_refreshes = 0
        self.setting_refreshes = 0

    def stop_controls(self):
        self.stops += 1

    def refresh_color(self):
        self.color_refreshes += 1

    def refresh_settings(self):
        self.setting_refreshes += 1

    def read_settings(self):
        raise AssertionError("Cancelled calibration may not re-read changed UI")

class CalibrationCancelTests(unittest.TestCase):
    def test_switching_console_restores_exact_old_profile(self):
        app = FakeApp(current="snes")
        CalibrationMixin.close_camera_calibration(app, restore=True)
        self.assertEqual(app.profile_store.saved[0], "gb")
        self.assertEqual(app.profile_store.saved[1]["mapping"], {"A": "B"})
        self.assertEqual(app.cfg["rgb"], [8, 25, 90])
        self.assertEqual(app.cfg["min_area"], 120)
        self.assertFalse(app.pick_mode)
        self.assertEqual(app.stops, 1)
        self.assertEqual(app.setting_refreshes, 0)
        self.assertEqual(app.color_refreshes, 1)
        self.assertTrue(app.window.destroyed)
        self.assertEqual(len(app._calibration_history), 0)

    def test_cancel_on_same_console_refreshes_visible_settings(self):
        app = FakeApp(current="gb")
        CalibrationMixin.close_camera_calibration(app, restore=True)
        self.assertEqual(app.setting_refreshes, 1)
        self.assertEqual(app.profile_store.saved[0], "gb")
        self.assertEqual(app.cfg["mapping"]["A"], "B")


if __name__ == "__main__":
    unittest.main()
