"""Prevent release regressions in entry points and compatibility-sensitive paths."""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourceContracts(unittest.TestCase):
    def test_python_modules_parse(self):
        for file in (*ROOT.glob("*.py"), *ROOT.glob("tests/*.py")):
            with self.subTest(file=file.name):
                ast.parse(file.read_text(encoding="utf-8"))

    def test_legacy_preferences_location_preserved(self):
        from app import App
        from settings_defaults import DEFAULT
        from system_profiles import ProfileStore
        from ui_profiles import ProfilesMixin
        self.assertIn(ProfilesMixin, App.__mro__)
        self.assertTrue(callable(App.load_profile))
        self.assertTrue(callable(App.save_profile))
        self.assertTrue(callable(ProfileStore.get))
        self.assertIn("rgb", DEFAULT)
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("'fish-plays-pokemon-studio' / 'preferences.json'", source)

    def test_platform_build_scripts_retained(self):
        names = (
            "build_windows.bat", "build_macos_dmg.sh", "build_linux_deb.sh",
            "build_macos_linux.sh", "installer.iss", "AnythingPlays.spec",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())

    def test_ui_boundary_is_explicit(self):
        from app import App
        self.assertLess(len((ROOT / "app.py").read_text().splitlines()), 250)
        self.assertTrue(callable(App.render_zones))
        self.assertTrue(callable(App.scan_roms))
        self.assertTrue(callable(App.draw_camera))
        self.assertTrue(callable(App.close))
        self.assertTrue(callable(App.apply_dark_theme))
        self.assertTrue(callable(App.cartridge_image))


if __name__ == "__main__":
    unittest.main()
