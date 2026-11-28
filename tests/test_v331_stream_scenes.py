"""Reusable creator scenes and single-commit Stream Mode application."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from anything_plays.stream_scenes import (
    SceneStore, STARTERS, strict_scene, starter_scene, import_scene,
    export_scene, MAX_BYTES, MAX_SCENES,
)
from anything_plays.ui_stream import DEFAULT_STREAM, StreamMixin
from anything_plays.ui_theme import ThemeMixin


THEMES = ThemeMixin.THEMES


class SceneStorageTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.store = SceneStore(self.root / "scenes.json", THEMES)

    def test_every_starter_preserves_selected_theme_and_border(self):
        current = dict(DEFAULT_STREAM, theme="Ocean Dark", border_color="#123456",
                       border_width=9)
        for name in STARTERS:
            scene = starter_scene(name, current, THEMES)
            self.assertEqual(scene["theme"], "Ocean Dark")
            self.assertEqual(scene["border_color"], "#123456")
            self.assertEqual(scene["border_width"], 9)
            self.assertEqual(scene, strict_scene(scene, THEMES))
        self.assertEqual(current["frame_rate"], "24 FPS")

    def test_save_and_reopen(self):
        self.store.save("Portrait", dict(DEFAULT_STREAM))
        self.store.save("Landscape", starter_scene("Landscape stream", DEFAULT_STREAM, THEMES))
        entries = SceneStore(self.store.path, THEMES).entries()
        self.assertEqual(entries["Portrait"], DEFAULT_STREAM)
        self.assertEqual(entries["Landscape"]["layout"], "Side by side")
        entries["Portrait"]["game_size"] = 30
        self.assertEqual(self.store.entries()["Portrait"]["game_size"], 53)

    def test_duplicate_requires_explicit_replace(self):
        self.store.save("Scene", DEFAULT_STREAM)
        prior = self.store.path.read_bytes()
        with self.assertRaises(ValueError):
            self.store.save("scene", dict(DEFAULT_STREAM, game_size=70))
        self.assertEqual(self.store.path.read_bytes(), prior)
        self.store.save("scene", dict(DEFAULT_STREAM, game_size=70), replace=True)
        self.assertEqual(self.store.entries(), {"scene": dict(DEFAULT_STREAM, game_size=70)})

    def test_capacity_and_atomic_failure(self):
        for index in range(MAX_SCENES):
            self.store.save(str(index), DEFAULT_STREAM)
        prior = self.store.path.read_bytes()
        with self.assertRaises(ValueError):
            self.store.save("Overflow", DEFAULT_STREAM)
        with patch("anything_plays.stream_scenes.write_json_atomically",
                   side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.store.delete("0")
        self.assertEqual(self.store.path.read_bytes(), prior)

    def test_export_has_no_name_or_private_fields(self):
        path = self.root / "scene.json"
        self.store.save("Private room name", DEFAULT_STREAM)
        export_scene(path, self.store.entries()["Private room name"], THEMES)
        self.assertNotIn("Private room name", path.read_text())
        self.assertEqual(import_scene(path, THEMES), DEFAULT_STREAM)
        for key in ("camera_frame", "rom_path", "obs_token"):
            with self.assertRaises(ValueError):
                export_scene(path, dict(DEFAULT_STREAM, **{key:"private"}), THEMES)
        self.assertEqual(import_scene(path, THEMES), DEFAULT_STREAM)

    def test_strict_types_ranges_and_missing_fields(self):
        for key, value in (("game_size", True), ("game_size", 71),
                           ("border_width", 2.0), ("show_labels", 0),
                           ("border_color", "red"), ("theme", "Unknown"),
                           ("frame_rate", "60 FPS"), ("layout", [])):
            with self.subTest(key=key), self.assertRaises(ValueError):
                strict_scene(dict(DEFAULT_STREAM, **{key:value}), THEMES)
        missing = dict(DEFAULT_STREAM)
        del missing["theme"]
        with self.assertRaises(ValueError):
            strict_scene(missing, THEMES)

    def test_malformed_library_never_replaced(self):
        for payload in (b"{broken", b"x" * (MAX_BYTES+1),
                        b'{"format":"anything-plays-stream-scene-library","version":1,"version":1,"scenes":{}}'):
            self.store.path.write_bytes(payload)
            with self.assertRaises(ValueError):
                self.store.save("New", DEFAULT_STREAM)
            self.assertEqual(self.store.path.read_bytes(), payload)

    def test_delete_only_saved_scene(self):
        self.store.save("A", DEFAULT_STREAM)
        self.store.save("B", DEFAULT_STREAM)
        self.store.delete("A")
        self.assertEqual(set(self.store.entries()), {"B"})


class SceneApplicationTests(unittest.TestCase):
    def setUp(self):
        class App(StreamMixin):
            THEMES = THEMES
        self.app = App()
        self.app.theme_name = SimpleNamespace(get=lambda:"Dark")
        self.app.initialize_stream_mode({})
        self.app._stream_controls_window = object()
        self.app._stream_options_updated = Mock()
        self.app._stream_output_window = Mock()
        self.app._stream_output_window.winfo_screenwidth.return_value = 1920
        self.app._stream_output_window.winfo_screenheight.return_value = 1080
        self.app._stream_vars = {}
        for key, value in self.app._stream_options.items():
            if key == "border_color":
                continue
            var = Mock()
            var.get.return_value = value
            def assign(new, variable=var):
                variable.get.return_value = new
                self.app._stream_controls_changed()
            var.set.side_effect = assign
            self.app._stream_vars[key] = var

    def test_apply_calls_one_invalidation_and_one_geometry_update(self):
        target = dict(DEFAULT_STREAM, layout="Side by side", frame_rate="30 FPS",
                      theme="Light", game_size=70, border_color="#123456")
        self.assertTrue(self.app.apply_stream_scene(target))
        self.assertEqual(self.app._stream_options, target)
        self.app._stream_options_updated.assert_called_once_with(force_camera_snapshot=True)
        self.app._stream_output_window.geometry.assert_called_once_with("1180x720")

    def test_style_only_scene_does_not_force_camera_snapshot(self):
        self.assertTrue(self.app.apply_stream_scene(dict(DEFAULT_STREAM, theme="Light")))
        self.app._stream_options_updated.assert_called_once_with(force_camera_snapshot=False)
        self.app._stream_output_window.geometry.assert_not_called()

    def test_invalid_or_closed_scene_never_updates(self):
        with self.assertRaises(ValueError):
            self.app.apply_stream_scene(dict(DEFAULT_STREAM, game_size=100))
        self.app._stream_controls_window = None
        self.assertFalse(self.app.apply_stream_scene(dict(DEFAULT_STREAM, theme="Light")))
        self.app._stream_options_updated.assert_not_called()
        self.assertEqual(self.app._stream_options, DEFAULT_STREAM)

    def test_widget_failure_rolls_back_without_publishing_partial_settings(self):
        self.app._stream_vars["theme"].set.side_effect = RuntimeError("widget destroyed")
        target = dict(DEFAULT_STREAM, layout="Side by side", theme="Light")
        self.assertFalse(self.app.apply_stream_scene(target))
        self.assertEqual(self.app._stream_options, DEFAULT_STREAM)
        self.assertEqual(self.app._stream_vars["layout"].get(), DEFAULT_STREAM["layout"])
        self.assertFalse(self.app._stream_controls_syncing)
        self.app._stream_options_updated.assert_not_called()


if __name__ == "__main__":
    unittest.main()
