"""Prevent the unreleased 3.1 preview from overwriting the 3.0 installer."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from anything_plays.test_preferences import (
    TEST_DIR, PREVIOUS_PREVIEW_DIR, LEGACY_DIR, prepare_test_preferences,
)
from tools.verify_v31_preview import FILENAMES, STATUS, verify

ROOT = Path(__file__).resolve().parents[1]


class PreviewOneContracts(unittest.TestCase):
    def test_settings_copy_only_once_into_distinct_3_1_location(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            previous = root / PREVIOUS_PREVIEW_DIR
            previous.mkdir(parents=True)
            (previous / "preferences.json").write_text('{"theme":"Plum Dark"}', encoding="utf-8")
            current = prepare_test_preferences(root)
            self.assertEqual(current, root / TEST_DIR / "preferences.json")
            self.assertNotEqual(TEST_DIR, LEGACY_DIR)
            self.assertNotEqual(TEST_DIR, PREVIOUS_PREVIEW_DIR)
            self.assertEqual(current.read_text(), '{"theme":"Plum Dark"}')
            current.write_text('{"theme":"Ocean Dark"}', encoding="utf-8")
            self.assertEqual(prepare_test_preferences(root), current)
            self.assertEqual((previous / "preferences.json").read_text(), '{"theme":"Plum Dark"}')

    def test_linux_preview_has_distinct_package_and_install_location(self):
        text = (ROOT / "packaging/build_linux_deb.sh").read_text("utf-8")
        for value in ('PACKAGE_NAME="anything-plays-31-preview"',
                      'INSTALL_ID="anything-plays-31-preview"',
                      'VERSION="3.1.0~preview1"', '"$PKG/opt/$INSTALL_ID"'):
            self.assertIn(value, text)
        self.assertIn(".github/CODE_OF_CONDUCT.md", text)

    def test_mac_preview_has_distinct_identifier_and_disk_image(self):
        text = (ROOT / "packaging/build_macos_dmg.sh").read_text("utf-8")
        self.assertIn('BUNDLE_FILE="AnythingPlays31Preview.app"', text)
        self.assertIn("com.anythingplays.preview31", text)
        self.assertIn("3.1.0-preview1-macos-arm64.dmg", text)
        self.assertIn("3.1.0-preview1-macos-x64.dmg", text)
        self.assertIn(".github/CODE_OF_CONDUCT.md", text)

    def test_windows_preview_has_distinct_inno_appid(self):
        iss = (ROOT / "packaging/installer.iss").read_text("utf-8")
        bat = (ROOT / "packaging/build_windows.bat").read_text("utf-8")
        self.assertIn("C9B0B32A-78D9-47DA-B991-41AC320D10F1", iss)
        self.assertIn("Anything Plays 3.1 Preview 1", iss)
        self.assertIn('set "VERSION=3.1.0-preview1"', bat)
        self.assertIn("/DV31PreviewBuild=1", bat)
        self.assertIn(".github\\CODE_OF_CONDUCT.md", bat)

    def test_workflow_uploads_qa_artifacts_only(self):
        text = (ROOT / ".github/workflows/v31-preview1-test-installers.yml").read_text("utf-8")
        self.assertIn("feature/v3.1-controls-usability", text)
        self.assertIn("AP_V31_PREVIEW: '1'", text)
        self.assertIn("AP_V30_MINIMAL_CORE_BUILD: '1'", text)
        self.assertIn("actions/upload-artifact@v4", text)
        self.assertIn("retention-days: 7", text)
        self.assertIn("GB, GBC and GBA", text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("gh release create", text)
        self.assertNotIn("softprops/action-gh-release", text)
        self.assertEqual(set(FILENAMES), {"windows-x64", "linux-x64", "macos-arm64", "macos-x64"})
        self.assertEqual(STATUS, "UNRELEASED_QA_ARTIFACT")

    def test_receipt_rejects_wrong_file_or_missing_binary(self):
        with TemporaryDirectory() as temp:
            wrong = Path(temp) / "AnythingPlaysSetup-3.0.0.exe"
            wrong.write_bytes(b"MZ" + (b"0" * 1048577))
            with self.assertRaises(ValueError):
                verify("windows-x64", wrong, "a" * 40)
            right = Path(temp) / FILENAMES["windows-x64"]
            with self.assertRaises(ValueError):
                verify("windows-x64", right, "a" * 40)
            right.write_bytes(b"MZ" + (b"0" * 1048577))
            record = verify("windows-x64", right, "a" * 40)
            self.assertEqual(record["public_release_approved"], False)
            self.assertEqual(record["bundled_console_profiles"], ["gb", "gbc", "gba"])
            self.assertRegex(record["sha256"], "^[0-9a-f]{64}$")

    def test_application_title_is_loaded_from_embedded_build_identity(self):
        title = (ROOT / "app.py").read_text("utf-8")
        self.assertIn("root.title(app_title())", title)
        from anything_plays.build_identity import app_title, make_identity
        self.assertEqual(make_identity("preview1")["title"],
                         "Anything Plays 3.1 · Preview 1")
        self.assertEqual(app_title(), "Anything Plays 3.1 · Preview 1")


if __name__ == "__main__":
    unittest.main()
