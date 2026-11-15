"""3.2 safe theme preferences, with no Tk display or user files."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.ui_theme import ThemeMixin


class Variable:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class FakeThemeApp(ThemeMixin):
    def __init__(self, path):
        self.preferences_path = path
        self.theme_name = Variable("Light")
        self.status = Variable("")
        self.applied = []
    def apply_theme(self, name):
        # The actual theme engine updates a large native Tk widget tree;
        # only persistence is under test here.
        self.applied.append(name)


class ThemeAtomicTests(unittest.TestCase):
    def test_theme_uses_atomic_save_and_preserves_other_preferences(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "private-preview" / "preferences.json"
            path.parent.mkdir(parents=True)
            previous = {"theme": "Dark", "volume": 72,
                        "rom_directories": {"gba": "/private/library"}}
            path.write_text(json.dumps(previous), encoding="utf-8")
            app = FakeThemeApp(path)
            app.select_theme()
            result = json.loads(path.read_text("utf-8"))
            self.assertEqual(result["theme"], "Light")
            self.assertEqual(result["volume"], 72)
            self.assertEqual(result["rom_directories"], previous["rom_directories"])
            self.assertEqual(app.applied, ["Light"])
            self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_failed_theme_replace_does_not_truncate_existing_preferences(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "private-preview" / "preferences.json"
            path.parent.mkdir(parents=True)
            path.write_text('{"theme":"Dark","volume":99}\n', encoding="utf-8")
            before = path.read_bytes()
            app = FakeThemeApp(path)
            with patch("anything_plays.atomic_storage.os.replace",
                       side_effect=OSError("private simulated disk full")):
                app.select_theme()
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(app.applied, ["Light"])
            self.assertIn("could not save", app.status.get())
            self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_corrupt_existing_preferences_are_not_overwritten(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "preferences.json"
            data = b"invalid-json that must remain available for recovery"
            path.write_bytes(data)
            app = FakeThemeApp(path)
            app.select_theme()
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(app.applied, ["Light"])
            self.assertIn("could not save", app.status.get())

    def test_unknown_theme_does_not_modify_preference_file(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "preferences.json"
            path.write_bytes(b'{"theme":"Dark"}')
            app = FakeThemeApp(path)
            app.theme_name.set("not-an-allowed-theme")
            app.select_theme()
            self.assertEqual(path.read_bytes(), b'{"theme":"Dark"}')
            self.assertEqual(app.applied, [])


if __name__ == "__main__":
    unittest.main()
