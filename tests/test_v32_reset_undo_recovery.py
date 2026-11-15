"""3.2 Undo reset failure recovery and required frozen-GUI acceptance.

Only synthetic Tk variables and disposable private profile stores are used.
No webcam, controller, core, ROM or user preferences are opened.
"""

import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.settings_defaults import DEFAULT
from anything_plays.system_profiles import ProfileStore, default_for
from anything_plays.ui_profiles import ProfilesMixin
from tools.verify_v32_installed_gui import REQUIRED_TRUE


class Variable:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class Button:
    def __init__(self):
        self.state = "normal"
    def configure(self, **kwargs):
        self.state = kwargs["state"]


class UndoApp:
    def __init__(self, store):
        self.profile_store = store
        self.system_key = Variable("gba")
        self.status = Variable("")
        self._calibration_window = None
        self._undo_profile_reset_button = Button()
        self.cfg = store.get("gba")
        self.tolerance = Variable(self.cfg["tolerance"])
        self.zone_image_path = Variable(self.cfg.get("zone_image", ""))
        self.stops = 0
        self.refresh_calls = 0
        self.refresh_failure = False
        self._last_profile_reset = (
            "gba",
            {**copy.deepcopy(self.cfg), "tolerance": 71},
            copy.deepcopy(self.cfg),
        )
    def read_settings(self):
        self.cfg["tolerance"] = self.tolerance.get()
        self.cfg["zone_image"] = self.zone_image_path.get()
    def stop_controls(self):
        self.stops += 1
    def refresh_settings(self):
        self.refresh_calls += 1
        if self.refresh_failure and self.refresh_calls == 1:
            raise RuntimeError("simulated Tk renderer failure")
        self.tolerance.set(self.cfg["tolerance"])
        self.zone_image_path.set(self.cfg.get("zone_image", ""))


class ResetUndoRecoveryTests(unittest.TestCase):
    def test_private_installer_requires_reset_undo(self):
        self.assertIn("v32_reset_undo_verified", REQUIRED_TRUE)

    def test_disk_failure_keeps_undo_ready_and_preserves_editor(self):
        with TemporaryDirectory() as td:
            store = ProfileStore(Path(td) / "profiles.json", DEFAULT)
            profile = default_for("gba", DEFAULT)
            profile["zone_image"] = "/private/zone.png"
            store.put("gba", profile)
            app = UndoApp(store)
            original = store.get("gba")
            with patch.object(
                store, "put", side_effect=OSError("simulated disk full")
            ), patch(
                "anything_plays.ui_profiles.messagebox.showerror"
            ) as error:
                self.assertFalse(ProfilesMixin.undo_profile_reset(app))
            error.assert_called_once()
            self.assertEqual(store.get("gba"), original)
            self.assertEqual(app.cfg, original)
            self.assertEqual(app.tolerance.get(), original["tolerance"])
            self.assertIsNotNone(app._last_profile_reset)
            self.assertEqual(app._undo_profile_reset_button.state, "normal")
            self.assertEqual(app.stops, 1)
            self.assertIn("did not finish", app.status.get())

            # A second attempt after storage recovers should succeed.
            with patch("anything_plays.ui_profiles.messagebox.showerror") as error:
                self.assertTrue(ProfilesMixin.undo_profile_reset(app))
            error.assert_not_called()
            self.assertEqual(store.get("gba")["tolerance"], 71)
            self.assertEqual(store.get("gba")["zone_image"], "/private/zone.png")
            self.assertIsNone(app._last_profile_reset)
            self.assertEqual(app._undo_profile_reset_button.state, "disabled")

    def test_failed_ui_refresh_rolls_disk_back_and_allows_retry(self):
        with TemporaryDirectory() as td:
            store = ProfileStore(Path(td) / "profiles.json", DEFAULT)
            profile = default_for("gba", DEFAULT)
            profile["zone_image"] = "/private/preserve.png"
            store.put("gba", profile)
            app = UndoApp(store)
            before = store.get("gba")
            app.refresh_failure = True
            with patch(
                "anything_plays.ui_profiles.messagebox.showerror"
            ) as error:
                self.assertFalse(ProfilesMixin.undo_profile_reset(app))
            error.assert_called_once()
            self.assertEqual(store.get("gba"), before)
            self.assertEqual(app.cfg, before)
            self.assertEqual(app.refresh_calls, 2)
            self.assertIsNotNone(app._last_profile_reset)
            self.assertEqual(app._undo_profile_reset_button.state, "normal")

    def test_wrong_console_and_active_calibration_block_undo(self):
        with TemporaryDirectory() as td:
            store = ProfileStore(Path(td) / "profiles.json", DEFAULT)
            app = UndoApp(store)
            app.system_key.set("snes")
            with patch(
                "anything_plays.ui_profiles.messagebox.showinfo"
            ) as notice:
                self.assertFalse(ProfilesMixin.undo_profile_reset(app))
            notice.assert_called_once()
            self.assertEqual(store.get("gba")["tolerance"],
                             default_for("gba", DEFAULT)["tolerance"])
            app.system_key.set("gba")
            app._calibration_window = object()
            with patch(
                "anything_plays.ui_profiles.messagebox.showinfo"
            ) as notice:
                self.assertFalse(ProfilesMixin.undo_profile_reset(app))
            notice.assert_called_once()
            self.assertIsNotNone(app._last_profile_reset)


if __name__ == "__main__":
    unittest.main()
