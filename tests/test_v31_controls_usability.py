"""Regression checks for the first, unreleased 3.1 controls UI cleanup."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "anything_plays"


class ControlsUsabilityTests(unittest.TestCase):
    def _source(self, filename):
        source = (ROOT / filename).read_text(encoding="utf-8")
        ast.parse(source, filename=filename)
        return source

    def test_game_controls_label_and_action(self):
        layout = self._source("ui_layout.py")
        self.assertIn("text='Game Controls'", layout)
        self.assertIn("command=self.configure_shortcuts", layout)
        self.assertNotIn("text='Keyboard shortcuts'", layout)

    def test_keyboard_shortcuts_available_in_step_eight(self):
        panels = self._source("ui_panels.py")
        self.assertIn("08   SAFETY & PROFILES", panels)
        self.assertIn("text='Keyboard Shortcuts', command=self.configure_shortcuts", panels)
        self.assertIn("STOP ALL OBJECT CONTROLS", panels)

    def test_single_label_size_control_on_left(self):
        panels = self._source("ui_panels.py")
        advanced = self._source("ui_tracking_panel.py")
        self.assertIn("self.quick_label_size = ttk.Scale(", panels)
        self.assertNotIn('text="Label size (8–160 px)"', advanced)
        self.assertNotIn("variable=app.zone_font_size", advanced)
        self.assertIn("Overlay tint strength", advanced)

    def test_manual_focus_prompt_refers_to_game_controls(self):
        gameplay = self._source("ui_gameplay.py")
        self.assertIn("MANUAL PLAY ACTIVE · Open Game Controls", gameplay)


if __name__ == "__main__":
    unittest.main()
