"""An RC2 QA installer must never overwrite RC1, 3.0 or saved preferences."""
from __future__ import annotations

import json
from pathlib import Path
import plistlib
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.build_identity import make_identity, validate_identity
from anything_plays.test_preferences import CANDIDATE_DIR, RC2_DIR, LEGACY_DIR, prepare_test_preferences
from tools.write_v31_identity import choose_channel, write_identity
from tools.verify_v31_rc import RC2_INSTALLERS, RC2_STATUS, verify, validate_staged_identity


ROOT = Path(__file__).resolve().parents[1]
QA_ENV = {
    "AP_V31_RC2": "1", "AP_V31_RC": "0", "AP_V31_PREVIEW": "0",
    "AP_V30_MINIMAL_CORE_BUILD": "1", "AP_RELEASE_BUILD": "0",
    "AP_V30_APPROVED_RELEASE": "0", "AP_V30_STABLE_CANDIDATE": "0",
    "AP_V30_TEST_CORES": "0", "AP_V30_GPL_TRIAL": "0",
    "AP_V30_TIA_TRIAL": "0",
}


class RC2IdentityContracts(unittest.TestCase):
    def test_rc2_has_new_exact_immutable_identity(self):
        rc1, rc2 = make_identity("rc1"), make_identity("rc2")
        self.assertEqual(rc2["channel"], "rc2")
        self.assertEqual(rc2["version"], "3.1.0")
        self.assertIn("Release Candidate 2", rc2["title"])
        self.assertEqual(rc2["settings_namespace"], RC2_DIR.name)
        self.assertNotEqual(rc1["settings_namespace"], rc2["settings_namespace"])
        self.assertFalse(rc2["public_release_approved"])
        self.assertEqual(validate_identity(rc2), rc2)
        for field, value in (("channel", "rc1"),
                             ("settings_namespace", CANDIDATE_DIR.name),
                             ("public_release_approved", True),
                             ("title", "Anything Plays stable")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_identity(dict(rc2, **{field: value}))

    def test_rc2_only_fresh_nonrelease_flags_can_write_identity(self):
        self.assertEqual(choose_channel(QA_ENV), "rc2")
        for key, bad in (
            ("AP_V31_PREVIEW", "1"), ("AP_V31_RC", "1"),
            ("AP_V31_RC2", "0"), ("AP_V30_MINIMAL_CORE_BUILD", "0"),
            ("AP_RELEASE_BUILD", "1"), ("AP_V30_APPROVED_RELEASE", "1"),
            ("AP_V30_STABLE_CANDIDATE", "1"), ("AP_V30_TEST_CORES", "1"),
            ("AP_V30_GPL_TRIAL", "1"), ("AP_V30_TIA_TRIAL", "1")
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                choose_channel(dict(QA_ENV, **{key: bad}))
        with TemporaryDirectory() as tmp:
            marker = Path(tmp) / "assets/v31_build_identity.json"
            embedded = write_identity(marker, QA_ENV)
            self.assertEqual(embedded, make_identity("rc2"))
            self.assertEqual(json.loads(marker.read_text("utf-8")), embedded)
            self.assertEqual(validate_staged_identity(Path(tmp), channel="rc2"),
                             "assets/v31_build_identity.json")
            with self.assertRaises(ValueError):
                validate_staged_identity(Path(tmp), channel="rc1")

    def test_rc2_migrates_a_copy_without_writing_to_rc1_or_legacy(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            rc1 = root / CANDIDATE_DIR
            rc1.mkdir(parents=True)
            orig = rc1 / "preferences.json"
            orig.write_text('{"theme":"Ocean Dark","selected_system":"gba"}')
            legacy = root / LEGACY_DIR
            legacy.mkdir(parents=True)
            (legacy / "preferences.json").write_text('{"theme":"Light"}')
            new = prepare_test_preferences(root, channel="rc2")
            self.assertEqual(new, root / RC2_DIR / "preferences.json")
            self.assertEqual(new.read_text("utf-8"), orig.read_text("utf-8"))
            new.write_text('{"theme":"Plum Dark"}')
            self.assertEqual(orig.read_text("utf-8"),
                             '{"theme":"Ocean Dark","selected_system":"gba"}')
            self.assertEqual((legacy / "preferences.json").read_text("utf-8"),
                             '{"theme":"Light"}')
            self.assertEqual(prepare_test_preferences(root, channel="rc2"), new)
            self.assertEqual(new.read_text("utf-8"), '{"theme":"Plum Dark"}')

    def test_symlinked_rc2_destination_cannot_overwrite_rc1(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            rc1 = root / CANDIDATE_DIR
            rc1.mkdir(parents=True)
            original = rc1 / "preferences.json"
            original.write_text('{"theme":"Original"}', encoding="utf-8")
            rc2 = root / RC2_DIR
            rc2.mkdir(parents=True)
            try:
                (rc2 / "preferences.json").symlink_to(original)
            except (OSError, NotImplementedError):
                self.skipTest("Filesystem cannot create symbolic links")
            with self.assertRaises(ValueError):
                prepare_test_preferences(root, channel="rc2")
            self.assertEqual(original.read_text("utf-8"), '{"theme":"Original"}')

    def test_four_platform_rc2_frozen_receipts_use_unique_names(self):
        self.assertEqual(set(RC2_INSTALLERS), {
            "linux-x64", "windows-x64", "macos-arm64", "macos-x64"
        })
        self.assertEqual(RC2_STATUS, "UNRELEASED_3_1_RC2_APP_STAGE_ONLY")
        self.assertTrue(all("rc2" in name for name in RC2_INSTALLERS.values()))
        with TemporaryDirectory() as temp:
            root = Path(temp)
            app = root / "AnythingPlays31RC2.app"
            app.mkdir(parents=True)
            marker = app / "assets/v31_build_identity.json"
            marker.parent.mkdir()
            marker.write_text(json.dumps(make_identity("rc2")), "utf-8")
            installer = root / RC2_INSTALLERS["macos-arm64"]
            installer.write_bytes(b"x" * (1024 * 1024 + 5))
            info = app / "Contents/Info.plist"
            info.parent.mkdir(exist_ok=True)
            info.write_bytes(plistlib.dumps({
                "CFBundleIdentifier": "com.anythingplays.rc31v2",
                "CFBundleShortVersionString": "3.1.0",
            }))
            receipt = verify(
                "macos-arm64", installer, app, "a" * 40, channel="rc2",
            )
            self.assertEqual(receipt["status"], RC2_STATUS)
            self.assertEqual(receipt["version"], "3.1.0-rc2")
            self.assertEqual(receipt["settings_namespace"], RC2_DIR.name)
            self.assertFalse(receipt["public_release_approved"])
            with self.assertRaises(ValueError):
                verify("macos-arm64", installer, app, "a" * 40, channel="rc1")
            info.write_bytes(plistlib.dumps({
                "CFBundleIdentifier": "com.anythingplays.rc31",
                "CFBundleShortVersionString": "3.1.0",
            }))
            with self.assertRaises(ValueError):
                verify("macos-arm64", installer, app, "a" * 40, channel="rc2")

    def test_platform_specific_installer_identifiers_are_not_rc1(self):
        linux = (ROOT / "packaging/build_linux_deb.sh").read_text("utf-8")
        win = (ROOT / "packaging/build_windows.bat").read_text("utf-8")
        iss = (ROOT / "packaging/installer.iss").read_text("utf-8")
        mac = (ROOT / "packaging/build_macos_dmg.sh").read_text("utf-8")
        self.assertIn('PACKAGE_NAME="anything-plays-31-rc2"', linux)
        self.assertIn('INSTALL_ID="anything-plays-31-rc2"', linux)
        self.assertIn("anything-plays-31-rc2.desktop", linux)
        self.assertIn("V31RC2Build=1", win)
        self.assertIn("779FBB2F-1ACC-456E-A088-75D395CE98A3", iss)
        self.assertIn("A3C2BEE4-4F7E-476F-A514-940FB1E1E071", iss)
        self.assertIn("Anything Plays 3.1 Release Candidate 2", iss)
        self.assertIn('BUNDLE_FILE="AnythingPlays31RC2.app"', mac)
        self.assertIn("com.anythingplays.rc31v2", mac)
        self.assertIn('DMG_NAME="AnythingPlays-3.1.0-rc2-macos-arm64.dmg"', mac)


if __name__ == "__main__":
    unittest.main()
