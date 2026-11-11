"""3.1.0 final-identity QA never changes an existing 3.0 or RC2 install.

These are package SOURCE contracts. Passing them does not approve public
redistribution, native LGPL obligations or physical-gameplay acceptance.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from anything_plays.build_identity import make_identity, validate_identity
from anything_plays.test_preferences import FINAL_DIR, RC2_DIR, LEGACY_DIR, prepare_test_preferences
from tools.write_v31_identity import choose_channel, write_identity


ROOT = Path(__file__).resolve().parents[1]
ENV = {
    "AP_V31_FINAL_CANDIDATE": "1",
    "AP_V31_PREVIEW": "0", "AP_V31_RC": "0", "AP_V31_RC2": "0",
    "AP_V30_MINIMAL_CORE_BUILD": "1",
    "AP_RELEASE_BUILD": "0", "AP_V30_APPROVED_RELEASE": "0",
    "AP_V30_STABLE_CANDIDATE": "0", "AP_V30_TEST_CORES": "0",
    "AP_V30_GPL_TRIAL": "0", "AP_V30_TIA_TRIAL": "0",
}


class FinalIdentityContracts(unittest.TestCase):
    def test_exact_real_310_version_without_pretending_rights_approval(self):
        value = make_identity("final_candidate")
        self.assertEqual(value["version"], "3.1.0")
        self.assertEqual(value["title"], "Anything Plays 3.1")
        self.assertEqual(value["channel"], "final_candidate")
        self.assertEqual(value["settings_namespace"], FINAL_DIR.name)
        self.assertFalse(value["public_release_approved"])
        self.assertEqual(validate_identity(value), value)
        self.assertNotEqual(value["settings_namespace"], make_identity("rc2")["settings_namespace"])
        for field, bad in (("channel", "rc2"), ("public_release_approved", True),
                           ("settings_namespace", RC2_DIR.name), ("version", "3.1.0-rc2")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_identity(dict(value, **{field: bad}))

    def test_exactly_one_channel_and_private_build_flags(self):
        self.assertEqual(choose_channel(ENV), "final_candidate")
        for flag, bad in (
            ("AP_V31_FINAL_CANDIDATE", "0"), ("AP_V31_PREVIEW", "1"),
            ("AP_V31_RC", "1"), ("AP_V31_RC2", "1"),
            ("AP_V30_MINIMAL_CORE_BUILD", "0"), ("AP_RELEASE_BUILD", "1"),
            ("AP_V30_APPROVED_RELEASE", "1"),
            ("AP_V30_STABLE_CANDIDATE", "1"),
            ("AP_V30_TEST_CORES", "1"), ("AP_V30_GPL_TRIAL", "1"),
            ("AP_V30_TIA_TRIAL", "1"),
        ):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                choose_channel(dict(ENV, **{flag: bad}))
        with TemporaryDirectory() as temp:
            file = Path(temp) / "assets/v31_build_identity.json"
            made = write_identity(file, ENV)
            self.assertEqual(json.loads(file.read_text("utf-8")), made)
            self.assertEqual(made["channel"], "final_candidate")

    def test_atomic_migration_from_rc2_and_no_rewrite_or_symlink_of_old_settings(self):
        with TemporaryDirectory() as temp:
            home = Path(temp)
            rc2 = home / RC2_DIR
            rc2.mkdir(parents=True)
            original = rc2 / "preferences.json"
            original.write_text('{"theme":"Ocean Dark","stream_mode":{"layout":"DS stacked"}}',
                                encoding="utf-8")
            (rc2 / "system_profiles.json").write_text('{"gba":{"rgb":[1,2,3]}}',
                                                       encoding="utf-8")
            legacy = home / LEGACY_DIR
            legacy.mkdir(parents=True)
            (legacy / "preferences.json").write_text('{"theme":"Light"}', encoding="utf-8")
            target = prepare_test_preferences(home, channel="final_candidate")
            self.assertEqual(target, home / FINAL_DIR / "preferences.json")
            self.assertEqual(target.read_bytes(), original.read_bytes())
            self.assertEqual((home / FINAL_DIR / "system_profiles.json").read_text("utf-8"),
                             '{"gba":{"rgb":[1,2,3]}}')
            target.write_text('{"theme":"Plum Dark"}', encoding="utf-8")
            self.assertEqual(prepare_test_preferences(home, channel="final_candidate"), target)
            self.assertIn("Ocean Dark", original.read_text("utf-8"))
            self.assertEqual((legacy / "preferences.json").read_text("utf-8"),
                             '{"theme":"Light"}')
            self.assertNotIn("Plum Dark", original.read_text("utf-8"))

    def test_no_stable_30_or_rc2_installer_id_overlap(self):
        linux = (ROOT / "packaging/build_linux_deb.sh").read_text("utf-8")
        windows = (ROOT / "packaging/build_windows.bat").read_text("utf-8")
        iss = (ROOT / "packaging/installer.iss").read_text("utf-8")
        mac = (ROOT / "packaging/build_macos_dmg.sh").read_text("utf-8")
        self.assertIn('PACKAGE_NAME="anything-plays-31"', linux)
        self.assertIn('VERSION="3.1.0"', linux)
        self.assertIn("anything-plays-31.desktop", linux)
        self.assertIn('set "VERSION=3.1.0"', windows)
        self.assertIn("V31FinalBuild=1", windows)
        self.assertIn("753B9C90-2D6A-43E4-90E4-49393B3AE025", iss)
        self.assertIn("779FBB2F-1ACC-456E-A088-75D395CE98A3", iss)
        self.assertIn("AnythingPlays31.app", mac)
        self.assertIn("com.anythingplays.release31", mac)
        self.assertIn("AnythingPlays-3.1.0-macos-arm64.dmg", mac)
        self.assertIn("AnythingPlays-3.1.0-macos-x64.dmg", mac)


if __name__ == "__main__":
    unittest.main()
