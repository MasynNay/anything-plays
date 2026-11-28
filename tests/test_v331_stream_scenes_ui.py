"""Actual Tk creator scene workflow, without capture devices or an emulator."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
from tkinter import ttk
from unittest.mock import Mock, patch
import unittest

from anything_plays.stream_scenes import SceneStore
from anything_plays.ui_stream import StreamMixin, DEFAULT_STREAM
from anything_plays.ui_theme import ThemeMixin


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


@unittest.skipUnless(os.environ.get("DISPLAY"), "Needs graphical Tk display")
class SceneWindowTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        self.root.withdraw()
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        class App(StreamMixin):
            THEMES = ThemeMixin.THEMES
        self.app = App()
        self.app.root = self.root
        self.app.theme_name = tk.StringVar(self.root, "Dark")
        self.app.preferences_path = Path(directory.name) / "preferences.json"
        self.app.initialize_stream_mode({})
        self.app._stream_options_updated = Mock()
        self.app._open_stream_controls()
        self.window = self.app._open_stream_scenes()
        self.root.update_idletasks()
        self.store = SceneStore(self.app.preferences_path.with_name("stream-scenes.json"),
                                self.app.THEMES)

    def button(self, name):
        return next(w for w in descendants(self.window)
                    if isinstance(w, ttk.Button) and w.cget("text") == name)

    def select(self, name):
        tree = next(w for w in descendants(self.window) if isinstance(w, ttk.Treeview))
        row = next(row for row in tree.get_children()
                   if tree.item(row, "values")[0] == name)
        tree.selection_set(row)
        tree.event_generate("<<TreeviewSelect>>")
        self.root.update_idletasks()

    def test_preview_save_apply_and_undo(self):
        self.select("Landscape stream")
        self.app._stream_options_updated.assert_not_called()
        with patch("anything_plays.ui_stream_scenes.simpledialog.askstring",
                   return_value="Landscape"):
            self.button("Save selected").invoke()
        self.assertEqual(self.store.entries()["Landscape"]["layout"], "Side by side")
        self.assertEqual(self.app._stream_options, DEFAULT_STREAM)
        with patch("anything_plays.ui_stream_scenes.messagebox.askyesno",
                   return_value=True):
            self.button("Apply scene").invoke()
        self.assertEqual(self.app._stream_options["layout"], "Side by side")
        self.assertEqual(self.app._stream_vars["layout"].get(), "Side by side")
        self.app._stream_options_updated.assert_called_once_with(force_camera_snapshot=True)
        self.button("Undo scene").invoke()
        self.assertEqual(self.app._stream_options, DEFAULT_STREAM)
        self.assertEqual(self.app._stream_options_updated.call_count, 2)

    def test_cancel_and_export_import_do_not_change_live_output(self):
        self.select("Low overhead")
        with patch("anything_plays.ui_stream_scenes.messagebox.askyesno",
                   return_value=False):
            self.button("Apply scene").invoke()
        path = self.app.preferences_path.with_name("shared.json")
        with patch("anything_plays.ui_stream_scenes.filedialog.asksaveasfilename",
                   return_value=str(path)):
            self.button("Export scene").invoke()
        self.assertTrue(path.is_file())
        with (
            patch("anything_plays.ui_stream_scenes.filedialog.askopenfilename",
                  return_value=str(path)),
            patch("anything_plays.ui_stream_scenes.simpledialog.askstring",
                  return_value="Imported"),
        ):
            self.button("Import scene").invoke()
        self.assertEqual(self.store.entries()["Imported"]["frame_rate"], "15 FPS")
        self.assertEqual(self.app._stream_options, DEFAULT_STREAM)
        self.app._stream_options_updated.assert_not_called()

    def test_closing_controls_destroys_scene_window(self):
        self.app._close_stream_controls()
        self.assertFalse(self.window.winfo_exists())
        self.assertIsNone(self.app._stream_controls_window)


if __name__ == "__main__":
    unittest.main()
