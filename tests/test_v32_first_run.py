"""3.2 first-run entry stays navigational and requires explicit clicks."""

import ast
from pathlib import Path
import unittest

from app import App
from anything_plays.ui_layout import LayoutMixin


ROOT = Path(__file__).resolve().parents[1]


class FirstRunNavigationTests(unittest.TestCase):
    def test_app_exposes_one_getting_started_entry(self):
        self.assertTrue(callable(getattr(App, "open_getting_started", None)))
        self.assertIn(LayoutMixin, App.__mro__)
        layout = (ROOT / "anything_plays/ui_layout.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("text='Get started'", layout)
        self.assertIn("command=self.open_getting_started", layout)

    def test_getting_started_is_navigation_only_not_device_startup(self):
        source = (ROOT / "anything_plays/ui_quickstart.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        calls = {
            node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        self.assertNotIn("VideoCapture", calls)
        self.assertNotIn("start_camera", calls)
        self.assertNotIn("start_game", calls)
        self.assertNotIn("toggle_gamepad", calls)
        self.assertNotIn("stop_controls", calls)
        self.assertIn("open_calibration_wizard", source)
        self.assertIn("open_controller_setup_guide", source)
        self.assertIn("open_setup_diagnostics", source)
        self.assertIn("Open a game", source)

    def test_preview_clearly_discloses_minimal_bundled_core_support(self):
        guide = (ROOT / "anything_plays/ui_quickstart.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('current_identity()["channel"] == "v32_preview"', guide)
        self.assertIn("Only GB, GBC and GBA are bundled", guide)
        self.assertIn("settings stay separate", guide)

    def test_main_app_stays_inside_source_boundary(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertLess(len(source.splitlines()), 250)


if __name__ == "__main__":
    unittest.main()
