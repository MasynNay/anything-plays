"""3.1 visual controller GUI: responsive right-panel entry and themed artwork."""
import ast
from pathlib import Path
import unittest

from anything_plays.ui_controller_art import draw_gamepad
from anything_plays.ui_theme import ThemeMixin


ROOT = Path(__file__).resolve().parents[1]


class MockCanvas:
    def __init__(self):
        self.config = {}
        self.shapes = []
        self.deletes = []

    def configure(self, **settings):
        self.config.update(settings)

    def delete(self, name):
        self.deletes.append(name)

    def create_oval(self, *coords, **opts):
        self.shapes.append(("oval", coords, opts))

    def create_polygon(self, *coords, **opts):
        self.shapes.append(("polygon", coords, opts))

    def create_rectangle(self, *coords, **opts):
        self.shapes.append(("rectangle", coords, opts))

    def create_text(self, *coords, **opts):
        self.shapes.append(("text", coords, opts))


class ControllerArtworkTests(unittest.TestCase):
    def test_compact_icon_draws_in_every_application_theme(self):
        for theme, palette in ThemeMixin.THEMES.items():
            with self.subTest(theme=theme):
                canvas = MockCanvas()
                draw_gamepad(canvas, palette)
                self.assertEqual(canvas.config["width"], 105)
                self.assertEqual(canvas.config["height"], 68)
                self.assertEqual(canvas.config["bg"], palette[1])
                self.assertEqual(canvas.deletes, ["all"])
                self.assertGreater(len(canvas.shapes), 10)
                self.assertTrue(any(shape[0] == "polygon" for shape in canvas.shapes))
                for kind, coords, options in canvas.shapes:
                    self.assertTrue(all(isinstance(v, (float, int)) for v in coords))

    def test_large_icon_includes_face_button_letters(self):
        canvas = MockCanvas()
        draw_gamepad(canvas, ThemeMixin.THEMES["Ocean Dark"], expanded=True)
        self.assertEqual(canvas.config["width"], 278)
        self.assertEqual(canvas.config["height"], 150)
        self.assertEqual({options["text"] for kind, _coords, options in canvas.shapes
                          if kind == "text"}, {"A", "B", "X", "Y"})

    def test_redraw_clears_old_shapes(self):
        canvas = MockCanvas()
        palette = ThemeMixin.THEMES["Ocean Dark"]
        draw_gamepad(canvas, palette, connected=False)
        shapes = len(canvas.shapes)
        draw_gamepad(canvas, palette, connected=True)
        self.assertEqual(canvas.deletes, ["all", "all"])
        self.assertEqual(len(canvas.shapes), shapes * 2)


class ControllerPlacementContracts(unittest.TestCase):
    def _load(self, path):
        source = (ROOT / path).read_text("utf-8")
        ast.parse(source, filename=path)
        return source

    def test_card_follows_sound_and_precedes_maintenance_and_game(self):
        layout = self._load("anything_plays/ui_layout.py")
        self.assertLess(layout.index("display_settings = ttk.LabelFrame("),
                        layout.index("self.build_gamepad_quick_panel(game)"))
        self.assertLess(layout.index("self.build_gamepad_quick_panel(game)"),
                        layout.index("self.maintenance_expanded"))
        self.assertLess(layout.index("self.build_gamepad_quick_panel(game)"),
                        layout.index("self.game_canvas ="))

    def test_gamepad_card_has_explicit_accessible_controls(self):
        ui = self._load("anything_plays/ui_gamepad.py")
        for expected in ('text="CONTROLLER · MANUAL PLAY"',
                         'text="Enable gamepad"',
                         'text="Configure…"',
                         'text="Rescan"',
                         "command=self.open_controller_settings",
                         "command=self.toggle_gamepad",
                         "command=self.refresh_gamepad",
                         "textvariable=self.gamepad_status"):
            with self.subTest(expected=expected):
                self.assertIn(expected, ui)

    def test_controller_modal_has_art_and_grouped_remapping(self):
        ui = self._load("anything_plays/ui_gamepad.py")
        self.assertIn("def open_controller_settings(", ui)
        self.assertIn('text="YOUR CONTROLLER"', ui)
        self.assertIn('text="BUTTON MAPPING · "', ui)
        for group in ("D-PAD", "FACE BUTTONS", "MENU BUTTONS",
                      "ANALOG STICKS", "SHOULDERS & TRIGGERS"):
            with self.subTest(group=group):
                self.assertIn(group, ui)
        self.assertIn("command=close", ui)
        self.assertIn("self._save_gamepad_binding(system, source, v.get())", ui)

    def test_keyboard_modal_links_to_right_card_not_duplicate_toggle(self):
        ui = self._load("anything_plays/ui_shortcuts.py")
        self.assertIn('text="Controller setup…"', ui)
        self.assertIn("command=self.open_controller_settings", ui)
        self.assertNotIn("controller_frame = ttk.LabelFrame", ui)
        self.assertIn('text="Keyboard shortcuts"', ui)

    def test_artwork_repaints_when_theme_changes(self):
        theme = self._load("anything_plays/ui_theme.py")
        self.assertIn("self.refresh_controller_artwork()", theme)
        ui = self._load("anything_plays/ui_gamepad.py")
        self.assertIn("def refresh_controller_artwork(self):", ui)


if __name__ == "__main__":
    unittest.main()
