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
        # 2.1 copies settings from the stable 2.0 path into a dedicated
        # test directory rather than writing directly into the old location.
        from anything_plays.test_preferences import (
            LEGACY_DIR, TEST_DIR, prepare_test_preferences,
        )
        self.assertEqual(
            LEGACY_DIR / "preferences.json",
            Path(".config/fish-plays-pokemon-studio/preferences.json"),
        )
        self.assertEqual(
            TEST_DIR / "preferences.json",
            Path(".config/anything-plays-30-preview/preferences.json"),
        )
        self.assertNotEqual(LEGACY_DIR, TEST_DIR)
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("self.preferences_path = prepare_test_preferences()", source)
        self.assertTrue(callable(prepare_test_preferences))

    def test_platform_build_scripts_retained(self):
        names = (
            "packaging/build_windows.bat", "packaging/build_macos_dmg.sh", "packaging/build_linux_deb.sh",
            "packaging/build_macos_linux.sh", "packaging/installer.iss", 
        )
        for name in names:
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())

    def test_camera_only_wheel_requires_hash_check_on_all_targets(self):
        for script_name in ("packaging/build_windows.bat", "packaging/build_macos_dmg.sh",
                            "packaging/build_linux_deb.sh"):
            with self.subTest(script=script_name):
                script = (ROOT / script_name).read_text(encoding="utf-8")
                self.assertIn("AP_CUSTOM_OPENCV_WHEEL", script)
                self.assertIn("AP_CUSTOM_OPENCV_SHA256", script)
                self.assertIn("verify_custom_opencv_wheel.py", script)
                self.assertIn("AP_REQUIRE_OPENCV_FFMPEG_OFF", script)

    def test_platform_installers_use_reviewed_dependency_versions(self):
        frozen = (ROOT / "requirements-build.txt").read_text(encoding="utf-8")
        for required in ("opencv-python-headless==4.14.0.94", "numpy==2.5.4",
                         "Pillow==12.3.0", "pyinstaller==6.22.3",
                         "sounddevice==0.5.6"):
            self.assertIn(required, frozen)
        self.assertNotIn("opencv-python==", frozen)
        self.assertIn("opencv-python-headless", (ROOT / "requirements.txt").read_text())
        for path in ("packaging/build_windows.bat", "packaging/build_macos_dmg.sh", "packaging/build_linux_deb.sh"):
            with self.subTest(script=path):
                script = (ROOT / path).read_text(encoding="utf-8")
                self.assertIn("-r requirements-build.txt", script)
                self.assertIn("pip==26.3", script)
                self.assertIn("tools/check_opencv_build.py", script)
                self.assertNotIn("-r requirements.txt pyinstaller", script)

    def test_windows_build_uses_the_selected_python(self):
        """Windows packaging must not silently switch to py's default 3.15."""
        script = (ROOT / "packaging/build_windows.bat").read_text(encoding="utf-8").lower()
        self.assertIn("python -m venv .build-venv", script)
        self.assertIn("python fetch_mgba_core.py", script)
        self.assertIn("python verify_bundle.py", script)
        self.assertIn("sys.version_info", script)
        self.assertNotIn("py -m venv", script)
        self.assertNotIn("py fetch_mgba_core.py", script)
        self.assertNotIn("py verify_bundle.py", script)

    def test_macos_core_hashes_are_checked_after_signing(self):
        """Ad-hoc signing must never change hashed Libretro dylibs unseen."""
        script = (ROOT / "packaging/build_macos_dmg.sh").read_text(encoding="utf-8")
        self.assertNotIn("codesign --force --deep --sign", script)
        signing = script.index("codesign --force --sign -")
        verification = script.index("verify_bundle.py --check-native macos", signing)
        dmg = script.index("hdiutil create")
        self.assertLess(signing, verification)
        self.assertLess(verification, dmg)
        self.assertIn("Contents/Resources/cores", script)
        self.assertNotIn("Contents/MacOS/cores", script)
        self.assertIn("hdiutil attach -readonly", script)
        self.assertIn('verify_bundle.py --check-native macos "$MOUNT_DIR/AnythingPlays30Preview.app"', script)

    def test_linux_verifies_extracted_debian_payload(self):
        script = (ROOT / "packaging/build_linux_deb.sh").read_text(encoding="utf-8")
        self.assertIn('dpkg-deb -x', script)
        self.assertIn('verify_bundle.py --check-native linux "$AUDIT_DIR/opt/anything-plays-30-preview"', script)

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
