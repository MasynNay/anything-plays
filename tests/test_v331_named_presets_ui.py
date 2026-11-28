"""Real Tk integration for the named control preset workflow (no ROM or camera)."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
from tkinter import ttk
from unittest.mock import Mock, patch
import unittest

from anything_plays.named_presets import NamedPresetStore
from anything_plays.settings_defaults import DEFAULT
from anything_plays.system_profiles import ProfileStore, default_for
from anything_plays.ui_profiles import ProfilesMixin
from anything_plays.ui_theme import ThemeMixin


class Harness(ProfilesMixin):
    THEMES = ThemeMixin.THEMES

    def __init__(self, root, directory):
        self.root = root
        self.preferences_path = directory / "preferences.json"
        self.profile_store = ProfileStore(directory / "profiles.json", DEFAULT)
        self.system_key = tk.StringVar(root, "gba")
        self.theme_name = tk.StringVar(root, "Dark")
        self.status = tk.StringVar(root, "")
        self.cfg = default_for("gba", DEFAULT)
        self.cfg["zone_image"] = "/local-only/art.png"
        self.profile_store.put("gba", self.cfg)
        self.read_settings = Mock()
        self.refresh_settings = Mock()
        self.stop_controls = Mock()
        self.apply_theme = Mock()
        self.save_preferences = Mock(return_value=True)


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


@unittest.skipUnless(os.environ.get("DISPLAY"),
                     "Real Tk preset window needs a graphical display")
class NamedPresetWindowTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        self.root.withdraw()
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.app = Harness(self.root, Path(temp.name))
        self.window = self.app.open_named_presets()
        self.root.update_idletasks()
        self.store = NamedPresetStore(
            self.app.preferences_path.with_name("named-control-presets.json"),
            self.app.THEMES,
        )

    def button(self, label):
        return next(w for w in descendants(self.window)
                    if isinstance(w, ttk.Button) and w.cget("text") == label)

    def test_save_apply_undo_and_delete_numeric_label(self):
        self.app.cfg["tolerance"] = 14
        with patch("anything_plays.ui_named_presets.simpledialog.askstring",
                   return_value="001"):
            self.button("Save current").invoke()
        self.assertEqual(self.store.list("gba"), ("001",))
        self.app.cfg["tolerance"] = 33
        self.app.profile_store.put("gba", self.app.cfg)
        with patch("anything_plays.ui_profiles.messagebox.askyesno", return_value=True):
            self.button("Apply selected").invoke()
        self.assertEqual(self.app.cfg["tolerance"], 14)
        self.assertEqual(self.app.cfg["zone_image"], "/local-only/art.png")
        self.app.stop_controls.assert_called_once()
        self.app.undo_profile_import()
        self.assertEqual(self.app.cfg["tolerance"], 33)
        with patch("anything_plays.ui_named_presets.messagebox.askyesno",
                   return_value=True):
            self.button("Delete selected").invoke()
        self.assertEqual(self.store.list("gba"), ())
        self.assertEqual(self.app.cfg["tolerance"], 33)

    def test_cancel_apply_and_console_switch_do_not_stop_controls(self):
        with patch("anything_plays.ui_named_presets.simpledialog.askstring",
                   return_value="Layout"):
            self.button("Save current").invoke()
        with patch("anything_plays.ui_profiles.messagebox.askyesno", return_value=False):
            self.button("Apply selected").invoke()
        self.app.stop_controls.assert_not_called()
        self.app.system_key.set("gb")
        self.button("Apply selected").invoke()
        self.app.stop_controls.assert_not_called()
        self.assertEqual(self.store.list("gba"), ("Layout",))

    def test_export_and_import_are_read_only_on_active_profile(self):
        with patch("anything_plays.ui_named_presets.simpledialog.askstring",
                   return_value="Layout"):
            self.button("Save current").invoke()
        path = self.app.preferences_path.with_name("export.json")
        with patch("anything_plays.ui_named_presets.filedialog.asksaveasfilename",
                   return_value=str(path)):
            self.button("Export selected").invoke()
        self.assertTrue(path.is_file())
        self.assertNotIn("Layout", path.read_text(encoding="utf-8"))
        with (
            patch("anything_plays.ui_named_presets.filedialog.askopenfilename",
                  return_value=str(path)),
            patch("anything_plays.ui_named_presets.simpledialog.askstring",
                  return_value="Imported"),
        ):
            self.button("Import to library").invoke()
        self.assertEqual(self.store.list("gba"), ("Imported", "Layout"))
        self.app.stop_controls.assert_not_called()
        self.app.save_preferences.assert_not_called()

    def test_reopening_raises_existing_window_and_close_releases_it(self):
        self.assertIsNone(self.app.open_named_presets())
        self.assertIs(self.app._named_presets_window, self.window)
        self.button("Close").invoke()
        self.assertIsNone(self.app._named_presets_window)


if __name__ == "__main__":
    unittest.main()
