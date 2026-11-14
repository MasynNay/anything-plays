"""Regression for saving the old console while the selector already changed."""

import unittest

from anything_plays.system_profiles import BUTTONS_BY_SYSTEM
from anything_plays.ui_profiles import ProfilesMixin


class Value:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value


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


class ProfileConsoleSwitchTests(unittest.TestCase):
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
