"""Regression for saving the old console while the selector already changed."""

import copy
import unittest

from anything_plays.system_profiles import BUTTONS_BY_SYSTEM
from anything_plays.ui_profiles import ProfilesMixin


class Value:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class FakeSwitchState:
    def __init__(self):
        self.system_key = Value("snes")  # Tk has already moved away from GB.
        self.cfg = {"zones": {}}
        values = {
            "tolerance": 20, "min_area": 120, "hold_frames": 8,
            "cooldown": 450, "mirror": False, "color2_enabled": False,
            "color2_player": "Player 2", "multi_fish_enabled": False,
            "camera_input_mode": "Held while visible",
            "zone_font_size": 44, "zone_opacity": 90,
            "zone_style": "Bold", "zone_border_width": 6,
            "zone_label_position": "Center", "shuffle_enabled": True,
            "zone_image_path": "",
        }
        for name, value in values.items():
            setattr(self, name, Value(value))
        names = set(BUTTONS_BY_SYSTEM["snes"]) | set(BUTTONS_BY_SYSTEM["gb"])
        self.mapping_vars = {name: Value(name) for name in names}
        self.mapping_vars["A"] = Value("B")
        self.mapping_vars["X"] = Value("Y")

    def read_settings(self, system=None):
        # Exercise the actual mixin method through the duck-typed fake app.
        return ProfilesMixin.read_settings(self, system)


class ProfileConsoleSwitchTests(unittest.TestCase):
    def test_failed_switch_reverts_selector_and_keeps_previous_editor(self):
        app = FakeSwitchState()
        app._active_profile_system = "gb"
        app.status = Value("")
        app.view_mode = Value("Game only")
        app._zone_label_save_job = None
        app._calibration_window = None
        app.stopped = 0
        app.stop_controls = lambda: setattr(app, "stopped", app.stopped + 1)
        app.uses_embedded_emulator = lambda _key: False
        app.view_transitions = []
        app.set_view_mode = lambda mode: app.view_transitions.append(mode)

        class FailStore:
            def put(self, system, profile):
                self.attempt = (system, profile.copy())
                raise OSError("full disk")

        app.profile_store = FailStore()
        self.assertFalse(ProfilesMixin.switch_system(app))
        self.assertEqual(app.system_key.get(), "gb")
        self.assertEqual(app._active_profile_system, "gb")
        self.assertEqual(app.cfg["mapping"]["A"], "B")
        self.assertNotIn("X", app.cfg["mapping"])
        self.assertEqual(app.profile_store.attempt[0], "gb")
        self.assertIn("Switch canceled", app.status.get())
        self.assertNotIn("full disk", app.status.get())
        self.assertEqual(app.stopped, 1)
        self.assertEqual(app.view_mode.get(), "Game only")
        self.assertEqual(app.view_transitions, [])

    def test_invalid_editor_input_prevents_switch_without_disk_write(self):
        app = FakeSwitchState()
        app._active_profile_system = "gb"
        app.status = Value("")
        app._zone_label_save_job = None
        app._calibration_window = None
        app.tolerance.set("not a number")
        app.stop_controls = lambda: None

        class NoWriteStore:
            def put(self, *_args):
                raise AssertionError("Invalid editor must not persist anything")

        app.profile_store = NoWriteStore()
        self.assertFalse(ProfilesMixin.switch_system(app))
        self.assertEqual(app.system_key.get(), "gb")
        self.assertEqual(app._active_profile_system, "gb")
        self.assertIn("Switch canceled", app.status.get())

    def test_late_invalid_control_does_not_partially_mutate_cfg(self):
        app = FakeSwitchState()
        initial = copy.deepcopy(app.cfg)
        app.tolerance.set("61")
        app.zone_border_width.set("broken border")
        with self.assertRaises(ValueError):
            ProfilesMixin.read_settings(app, "gb")
        self.assertEqual(app.cfg, initial)
        self.assertEqual(app.tolerance.get(), "61")
        self.assertEqual(app.zone_border_width.get(), "broken border")
        # Fixing the malformed value commits the entire candidate at once.
        app.zone_border_width.set("8")
        ProfilesMixin.read_settings(app, "gb")
        self.assertEqual(app.cfg["tolerance"], 61)
        self.assertEqual(app.cfg["zone_border_width"], 8)
        self.assertEqual(set(app.cfg["mapping"]), set(BUTTONS_BY_SYSTEM["gb"]))

    def test_destination_read_failure_cancels_before_view_or_game_teardown(self):
        app = FakeSwitchState()
        app._active_profile_system = "gb"
        app.status = Value("")
        app.view_mode = Value("Game only")
        app._zone_label_save_job = None
        app._calibration_window = None
        app.stop_controls = lambda: None
        app.uses_embedded_emulator = lambda _key: False
        app.set_view_mode = lambda _mode: self.fail(
            "Failed profile lookup must not change the active overlay"
        )
        class FaultyStore:
            def __init__(self):
                self.writes = []
            def get(self, _system):
                raise OSError("simulated unavailable destination storage")
            def put(self, system, profile):
                self.writes.append(system)
        store = FaultyStore()
        app.profile_store = store
        self.assertFalse(ProfilesMixin.switch_system(app))
        self.assertEqual(store.writes, [])
        self.assertEqual(app.system_key.get(), "gb")
        self.assertEqual(app._active_profile_system, "gb")
        self.assertEqual(app.view_mode.get(), "Game only")
        self.assertIn("Switch canceled", app.status.get())

    def test_destination_tk_refresh_failure_keeps_prior_editor(self):
        app = FakeSwitchState()
        app._active_profile_system = "gb"
        app.status = Value("")
        app.view_mode = Value("Game only")
        app._zone_label_save_job = None
        app._calibration_window = None
        app.stop_controls = lambda: None
        app.uses_embedded_emulator = lambda _key: False
        app.set_view_mode = lambda _mode: self.fail(
            "Failed switch must not change the active overlay"
        )
        class Store:
            def __init__(self):
                self.writes = []
            def get(self, system):
                return {"tolerance": 44} if system == "snes" else {}
            def put(self, system, profile):
                self.writes.append((system, copy.deepcopy(profile)))
        store = Store()
        app.profile_store = store
        calls = []
        def refresh():
            calls.append(app.system_key.get())
            if len(calls) == 1:
                raise RuntimeError("synthetic Tk widget failure")
        app.refresh_settings = refresh
        app.refresh_system_buttons = lambda: None
        old_cfg = copy.deepcopy(app.cfg)
        self.assertFalse(ProfilesMixin.switch_system(app))
        self.assertEqual(app.system_key.get(), "gb")
        self.assertEqual(app._active_profile_system, "gb")
        self.assertEqual(app.view_mode.get(), "Game only")
        self.assertEqual(app.cfg["tolerance"], 20)
        self.assertEqual(len(store.writes), 1)
        self.assertEqual(store.writes[0][0], "gb")
        self.assertEqual(calls, ["snes", "gb"])
        self.assertIn("Switch canceled", app.status.get())

    def test_explicit_previous_console_excludes_hidden_new_console_rows(self):
        app = FakeSwitchState()
        ProfilesMixin.read_settings(app, "gb")
        self.assertEqual(
            set(app.cfg["mapping"]), set(BUTTONS_BY_SYSTEM["gb"])
        )
        self.assertEqual(app.cfg["mapping"]["A"], "B")
        self.assertNotIn("X", app.cfg["mapping"])

    def test_regular_read_uses_current_console(self):
        app = FakeSwitchState()
        ProfilesMixin.read_settings(app)
        self.assertEqual(
            set(app.cfg["mapping"]), set(BUTTONS_BY_SYSTEM["snes"])
        )
        self.assertEqual(app.cfg["mapping"]["X"], "Y")

    def test_explicit_invalid_system_does_not_leak_hidden_rows(self):
        app = FakeSwitchState()
        ProfilesMixin.read_settings(app, "../../../bad")
        self.assertNotIn("bad", app.cfg["mapping"])
        self.assertEqual(
            set(app.cfg["mapping"]), set(BUTTONS_BY_SYSTEM["snes"])
        )


if __name__ == "__main__":
    unittest.main()
