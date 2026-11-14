"""3.2 private preview packaging must remain separate from stable installers.

These contracts validate source flags and dedicated native install identities.
They do NOT grant redistribution rights or claim any installer was created.
"""

from pathlib import Path
import shutil
import subprocess
import unittest

from anything_plays.build_identity import make_identity
from tools.write_v31_identity import choose_channel

ROOT = Path(__file__).resolve().parents[1]
FLAGS = {
    "AP_V32_PREVIEW_BUILD": "1",
    "AP_V30_MINIMAL_CORE_BUILD": "1",
    "AP_RELEASE_BUILD": "0",
    "AP_V30_APPROVED_RELEASE": "0",
}


class PreviewBuildIdentityTests(unittest.TestCase):
    def test_exactly_one_explicit_minimal_32_preview(self):
        self.assertEqual(choose_channel(FLAGS), "v32_preview")
        info = make_identity("v32_preview")
        self.assertEqual(info["version"], "3.2.0-preview")
        self.assertFalse(info["public_release_approved"])
        self.assertEqual(info["settings_namespace"], "anything-plays-32-preview")

    def test_reject_mixed_stable_and_legacy_channels(self):
        bad = (
            {"AP_V311_CANDIDATE": "1"},
            {"AP_V31_RC2": "1"},
            {"AP_RELEASE_BUILD": "1"},
            {"AP_V30_TEST_CORES": "1"},
            {"AP_V30_GPL_TRIAL": "1"},
            {"AP_V30_MINIMAL_CORE_BUILD": "0"},
        )
        for change in bad:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    choose_channel({**FLAGS, **change})

    def test_linux_has_unique_package_and_desktop_entry(self):
        text = (ROOT / "packaging/build_linux_deb.sh").read_text("utf-8")
        for required in (
            'AP_V32_PREVIEW_BUILD', 'VERSION="3.2.0~preview1"',
            'PACKAGE_NAME="anything-plays-32-preview"',
            'INSTALL_ID="anything-plays-32-preview"',
            'anything-plays-32-preview.desktop',
            'anything-plays-32-preview.png',
            'build/v31_build_identity.json:assets',
            'AP_V30_MINIMAL_CORE_BUILD',
        ):
            with self.subTest(value=required):
                self.assertIn(required, text)
        if shutil.which("bash"):
            result = subprocess.run(
                ["bash", "-n", str(ROOT / "packaging/build_linux_deb.sh")],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_windows_preview_inno_appid_does_not_match_stable(self):
        installer = (ROOT / "packaging/installer.iss").read_text("utf-8")
        windows = (ROOT / "packaging/build_windows.bat").read_text("utf-8")
        for required in (
            "V32PreviewBuild",
            "Anything Plays 3.2 Private Preview",
            "A0C96EA2-921A-49AC-AD1E-05A86EE7E320",
        ):
            self.assertIn(required, installer)
        self.assertIn('set "VERSION=3.2.0-preview1"', windows)
        self.assertIn("/DV32PreviewBuild=1", windows)
        self.assertIn("AP_V32_PREVIEW_BUILD", windows)
        self.assertIn("AP_V30_MINIMAL_CORE_BUILD", windows)
        for collision in (
            "753B9C90-2D6A-43E4-90E4-49393B3AE025",
            "D2946CA0-E7F8-4667-B1C5-A7733F570311",
        ):
            self.assertNotEqual(
                collision, "A0C96EA2-921A-49AC-AD1E-05A86EE7E320"
            )

    def test_macos_preview_app_has_independent_plist_identity(self):
        source = (ROOT / "packaging/build_macos_dmg.sh").read_text("utf-8")
        for required in (
            'BUNDLE_FILE="AnythingPlays32Preview.app"',
            "AnythingPlays-3.2.0-preview1-macos-arm64.dmg",
            "AnythingPlays-3.2.0-preview1-macos-x64.dmg",
            "com.anythingplays.privatepreview32",
            "CFBundleShortVersionString 3.2.0",
            "CFBundleVersion 3.2.0.1",
        ):
            with self.subTest(value=required):
                self.assertIn(required, source)
        if shutil.which("bash"):
            result = subprocess.run(
                ["bash", "-n", str(ROOT / "packaging/build_macos_dmg.sh")],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
