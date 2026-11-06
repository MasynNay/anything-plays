"""2.1 GUI refactor contracts without requiring a display or camera."""
import ast
from pathlib import Path
import unittest

from anything_plays.ui_panels import AuxiliaryPanelsMixin
from anything_plays.ui_layout import LayoutMixin


class StructureTests(unittest.TestCase):
    def test_each_ui_section_has_one_clear_owner(self):
        self.assertTrue(callable(LayoutMixin.build))
        self.assertTrue(callable(LayoutMixin._build_game_panel))
        self.assertTrue(callable(AuxiliaryPanelsMixin._build_camera_panel))
        self.assertTrue(callable(AuxiliaryPanelsMixin._build_tracking_panel))
        self.assertTrue(callable(AuxiliaryPanelsMixin._build_safety_panel))
        for name in ("_build_camera_panel", "_build_tracking_panel",
                     "_build_safety_panel"):
            self.assertNotIn(name, LayoutMixin.__dict__)

    def test_both_modules_parse_without_circular_imports(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("ui_layout.py", "ui_panels.py"):
            source = (root / "anything_plays" / name).read_text(encoding="utf-8")
            ast.parse(source)
            self.assertNotIn("from anything_plays.ui_layout import", source)


if __name__ == "__main__":
    unittest.main()
