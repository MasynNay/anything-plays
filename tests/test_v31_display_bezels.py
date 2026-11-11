"""The 3.1 camera/game bezels must be theme-safe and purely decorative."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

from anything_plays.ui_bezel import DisplayBezel, bezel_colors
from anything_plays.ui_theme import ThemeMixin


ROOT = Path(__file__).resolve().parents[1]


class DisplayBezelTests(unittest.TestCase):
    def source(self, file):
        content = (ROOT / "anything_plays" / file).read_text("utf-8")
        ast.parse(content, filename=file)
        return content

    def test_bezel_palette_uses_every_existing_theme(self):
        for name, palette in ThemeMixin.THEMES.items():
            with self.subTest(theme=name):
                colors = bezel_colors(palette)
                self.assertEqual(colors["housing"], palette[4])
                self.assertEqual(colors["header"], palette[5])
                self.assertEqual(colors["label"], palette[2])
                self.assertEqual(colors["accent"], palette[3])
                self.assertEqual(colors["well"], palette[0])
                self.assertEqual(colors["lip"], palette[1])
                self.assertEqual(len(colors), 6)
                self.assertTrue(all(isinstance(value, str) and
                                    value.startswith("#") and len(value) == 7
                                    for value in colors.values()))
                game = bezel_colors(palette, kind="game")
                self.assertEqual(game["housing"], palette[5])
                self.assertEqual(game["header"], palette[4])
                self.assertEqual(game["well"], colors["well"])
                self.assertEqual(game["accent"], colors["accent"])
                self.assertEqual(game["label"], colors["label"])
                self.assertNotEqual(game["housing"], colors["housing"])

    def test_invalid_palette_and_unknown_frame_kind_are_not_accepted(self):
        for bad in (None, "bad", {}, [], ("#123456",)):
            with self.subTest(palette=bad), self.assertRaises(ValueError):
                bezel_colors(bad)
        self.assertEqual(set(DisplayBezel.TITLES), {"camera", "game"})
        self.assertNotIn("LIVE", DisplayBezel.TITLES["camera"])
        with self.assertRaises(ValueError):
            bezel_colors(ThemeMixin.THEMES["Dark"], kind="not-a-display")

    def test_original_canvases_remain_full_size_inset_children(self):
        camera = self.source("ui_panels.py")
        game = self.source("ui_layout.py")
        self.assertIn("self.camera_bezel = DisplayBezel(left", camera)
        self.assertIn("self.canvas = tk.Canvas(", camera)
        self.assertIn("self.camera_bezel.screen", camera)
        self.assertIn("self.canvas.pack(fill='both', expand=True)", camera)
        self.assertIn("self.game_bezel = DisplayBezel(game", game)
        self.assertIn("self.game_canvas = tk.Canvas(", game)
        self.assertIn("self.game_bezel.screen", game)
        self.assertIn("self.game_canvas.pack(fill='both', expand=True)", game)
        for handler in ("self.on_click", "self.on_release"):
            self.assertIn(handler, camera)
        for handler in ("self.activate_manual", "self.manual_key_down",
                        "self.manual_key_up", "self.deactivate_manual"):
            self.assertIn(handler, game)
        self.assertIn("takefocus=1", game)
        self.assertIn("highlightthickness=2", game)

    def test_theme_updates_both_rims_and_game_focus_without_rebuilding_video(self):
        source = self.source("ui_theme.py")
        self.assertIn("('camera_bezel', 'game_bezel')", source)
        self.assertIn("bezel.apply_palette(", source)
        self.assertIn("game.configure(highlightbackground=button", source)
        chrome = self.source("ui_bezel.py")
        self.assertNotIn("Canvas(", chrome)
        self.assertNotIn(".bind(", chrome)
        self.assertNotIn(".after(", chrome)
        self.assertNotIn("pygame", chrome)
        self.assertNotIn("cv2", chrome)

    def test_game_only_view_does_not_move_original_bezel_camera_or_game(self):
        view = self.source("ui_view.py")
        self.assertIn("_game_only_canvas", view)
        self.assertNotIn("camera_bezel", view)
        self.assertNotIn("game_bezel", view)
        self.assertNotIn("DisplayBezel(", view)
        camera = self.source("ui_camera.py")
        game = self.source("ui_gameplay.py")
        self.assertNotIn("DisplayBezel(", camera)
        self.assertNotIn("DisplayBezel(", game)


if __name__ == "__main__":
    unittest.main()
