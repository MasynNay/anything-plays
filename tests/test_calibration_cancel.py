"""Camera calibration cancellation keeps pre-guide edits and restores disk.

All tests use synthetic profiles, windows and controls: no real Tk window,
webcam, game or user preferences are accessed.
"""

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
    def __init__(self, initial):
        self.saved = {"gb": copy.deepcopy(initial)}
        self.writes = []
    def get(self, system):
        return copy.deepcopy(self.saved[system])
    def put(self, system, profile):
        self.saved[system] = copy.deepcopy(profile)
        self.writes.append((system, copy.deepcopy(profile)))


class FakeApp:
    def __init__(self, current="snes"):
        original = {
            "rgb": [8, 25, 90], "tolerance": 20, "min_area": 120,
            "zones": {"A": [0, 0, 1, 1]}, "mapping": {"A": "B"},
        }
        self.profile_store = Store(original)
        self._calibration_original = {
            "system": "gb", "profile": copy.deepcopy(original),
            "stored_profile": copy.deepcopy(original),
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
        raise AssertionError("Cancel must never re-read in-guide UI changes")


class CalibrationCancelTests(unittest.TestCase):
    def test_switching_console_restores_old_editor_and_prior_disk(self):
        app = FakeApp(current="snes")
        # Simulate an advanced widget that auto-saved while the guide was open.
        during = copy.deepcopy(app.profile_store.get("gb"))
        during["tolerance"] = 75
        app.profile_store.put("gb", during)
        app.profile_store.writes.clear()
        CalibrationMixin.close_camera_calibration(app, restore=True)
        self.assertEqual(len(app.profile_store.writes), 1)
        self.assertEqual(app.profile_store.writes[0][0], "gb")
        self.assertEqual(app.profile_store.get("gb")["mapping"], {"A": "B"})
        self.assertEqual(app.profile_store.get("gb")["tolerance"], 20)
        self.assertEqual(app.cfg["rgb"], [8, 25, 90])
        self.assertEqual(app.cfg["min_area"], 120)
        self.assertFalse(app.pick_mode)
        self.assertEqual(app.stops, 1)
        self.assertEqual(app.setting_refreshes, 0)
        self.assertEqual(app.color_refreshes, 1)
        self.assertTrue(app.window.destroyed)
        self.assertEqual(len(app._calibration_history), 0)

    def test_cancel_on_same_console_does_not_write_if_disk_unchanged(self):
        app = FakeApp(current="gb")
        CalibrationMixin.close_camera_calibration(app, restore=True)
        self.assertEqual(app.setting_refreshes, 1)
        self.assertEqual(app.profile_store.writes, [])
        self.assertEqual(app.cfg["mapping"]["A"], "B")
        self.assertIn("Pre-guide controls restored", app.status.get())

    def test_snapshot_preserves_preexisting_unsaved_editor_values(self):
        app = FakeApp(current="gb")
        old_disk = app.profile_store.get("gb")
        app.cfg = copy.deepcopy(old_disk)
        app.tolerance.set(63)

        def read_unsaved():
            app.cfg["tolerance"] = app.tolerance.get()
        app.read_settings = read_unsaved
        CalibrationMixin._calibration_capture_original(app)
        self.assertEqual(app._calibration_original["profile"]["tolerance"], 63)
        self.assertEqual(app._calibration_original["stored_profile"], old_disk)
        self.assertEqual(app.profile_store.writes, [])

        # Canceling sampling restores the edits present *before* the guide;
        # it must not turn them into a disk write or lose them.
        app.cfg["tolerance"] = 88
        app.tolerance.set(88)
        CalibrationMixin.close_camera_calibration(app, restore=True)
        self.assertEqual(app.cfg["tolerance"], 63)
        self.assertEqual(app.profile_store.get("gb"), old_disk)
        self.assertEqual(app.profile_store.writes, [])

    def test_cancel_reports_when_temporary_disk_edit_cannot_be_reverted(self):
        app = FakeApp(current="gb")
        changed = app.profile_store.get("gb")
        changed["tolerance"] = 88
        app.profile_store.put("gb", changed)
        app.profile_store.put = lambda *_args: (_ for _ in ()).throw(
            OSError("synthetic full disk")
        )
        CalibrationMixin.close_camera_calibration(app, restore=True)
        self.assertEqual(app.profile_store.get("gb")["tolerance"], 88)
        self.assertIn("could not be rolled back", app.status.get())
        self.assertTrue(app.window.destroyed)


if __name__ == "__main__":
    unittest.main()
