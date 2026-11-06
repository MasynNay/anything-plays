"""Prevent release regressions in entry points and compatibility-sensitive paths."""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourceContracts(unittest.TestCase):
    def test_python_modules_parse(self):
        for file in (*ROOT.glob("*.py"), *ROOT.glob("anything_plays/*.py"), *ROOT.glob("tests/*.py")):
            with self.subTest(file=file.name):
                ast.parse(file.read_text(encoding="utf-8"))

    def test_legacy_preferences_location_preserved(self):
        from app import App
        from anything_plays.settings_defaults import DEFAULT
        from anything_plays.system_profiles import ProfileStore
        from anything_plays.ui_profiles import ProfilesMixin
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

    def test_windows_build_uses_the_selected_python(self):
        """Windows packaging must not silently switch to py's default 3.15."""
        script = (ROOT / "build_windows.bat").read_text(encoding="utf-8").lower()
        self.assertIn("python -m venv .build-venv", script)
        self.assertIn("python fetch_mgba_core.py", script)
        self.assertIn("python verify_bundle.py", script)
        self.assertIn("sys.version_info", script)
        self.assertNotIn("py -m venv", script)
        self.assertNotIn("py fetch_mgba_core.py", script)
        self.assertNotIn("py verify_bundle.py", script)

    def test_macos_core_hashes_are_checked_after_signing(self):
        """Ad-hoc signing must never change hashed Libretro dylibs unseen."""
        script = (ROOT / "build_macos_dmg.sh").read_text(encoding="utf-8")
        self.assertNotIn("codesign --force --deep --sign", script)
        signing = script.index("codesign --force --sign -")
        verification = script.index("verify_bundle.py --check-native macos", signing)
        dmg = script.index("hdiutil create")
        self.assertLess(signing, verification)
        self.assertLess(verification, dmg)
        self.assertIn("Contents/Resources/cores", script)
        self.assertNotIn("Contents/MacOS/cores", script)
        self.assertIn("hdiutil attach -readonly", script)
        self.assertIn('verify_bundle.py --check-native macos "$MOUNT_DIR/AnythingPlays.app"', script)

    def test_linux_verifies_extracted_debian_payload(self):
        script = (ROOT / "build_linux_deb.sh").read_text(encoding="utf-8")
        self.assertIn('dpkg-deb -x', script)
        self.assertIn('verify_bundle.py --check-native linux "$AUDIT_DIR/opt/anything-plays"', script)

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
