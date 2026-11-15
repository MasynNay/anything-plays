"""3.2 same-install identity contract; private QA without touching stable.

A frozen 3.2 stable-upgrade identity is intentionally *not* the side-by-side
preview identity. These tests do not install packages or alter real settings.
"""
from pathlib import Path
import unittest

from anything_plays.build_identity import make_identity, validate_identity
from tools.write_v31_identity import choose_channel

ROOT = Path(__file__).resolve().parents[1]
ENV = {"AP_V32_STABLE_CANDIDATE": "1", "AP_V30_MINIMAL_CORE_BUILD": "1"}


class V32UpgradeIdentityTests(unittest.TestCase):
    def test_stable_upgrade_shares_311_namespace_but_not_preview(self):
        old = make_identity("v311_stable_candidate")
        new = make_identity("v32_stable_candidate")
        self.assertEqual(new["version"], "3.2.0")
        self.assertEqual(new["title"], "Anything Plays 3.2")
        self.assertEqual(new["settings_namespace"], old["settings_namespace"])
        self.assertEqual(new["settings_namespace"], "anything-plays-31")
        self.assertNotEqual(new["settings_namespace"],
                            make_identity("v32_preview")["settings_namespace"])
        self.assertIs(new["public_release_approved"], False)
        self.assertEqual(validate_identity(new), new)

    def test_private_upgrade_requires_one_exclusive_nonrelease_flag(self):
        self.assertEqual(choose_channel(ENV), "v32_stable_candidate")
        for name in (
            "AP_V32_PREVIEW_BUILD", "AP_V311_STABLE_CANDIDATE",
            "AP_V311_CANDIDATE", "AP_V31_PREVIEW", "AP_V31_RC",
            "AP_V31_RC2", "AP_V31_FINAL_CANDIDATE",
            "AP_RELEASE_BUILD", "AP_V30_APPROVED_RELEASE",
            "AP_V30_STABLE_CANDIDATE", "AP_V30_TEST_CORES",
            "AP_V30_GPL_TRIAL", "AP_V30_TIA_TRIAL",
        ):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    choose_channel({**ENV, name: "1"})
        with self.assertRaises(ValueError):
            choose_channel({"AP_V32_STABLE_CANDIDATE": "1"})
        with self.assertRaises(ValueError):
            choose_channel({**ENV, "AP_RELEASE_BUILD": "1"})

    def test_linux_uses_real_311_package_and_launcher(self):
        s = (ROOT / "packaging/build_linux_deb.sh").read_text("utf-8")
        self.assertIn('VERSION="3.2.0~upgradeqa1"', s)
        self.assertIn('PACKAGE_NAME="anything-plays-31"', s)
        self.assertIn('INSTALL_ID="anything-plays-31"', s)
        self.assertIn('Name=Anything Plays 3.2', s)
        self.assertIn('AP_V32_STABLE_CANDIDATE', s)
        self.assertIn('AP_V32_PREVIEW_BUILD', s)

    def test_windows_reuses_original_inno_appid_and_private_filename(self):
        batch = (ROOT / "packaging/build_windows.bat").read_text("utf-8")
        iss = (ROOT / "packaging/installer.iss").read_text("utf-8")
        self.assertIn('set "VERSION=3.2.0"', batch)
        self.assertIn('/DV32UpgradeQABuild=1', batch)
        self.assertIn('OutputBaseFilename=AnythingPlaysSetup-{#AppVersion}-PRIVATE-UPGRADE-QA', iss)
        self.assertIn('AppId={{753B9C90-2D6A-43E4-90E4-49393B3AE025}', iss)
        self.assertIn('DefaultDirName={autopf}\\Anything Plays 3.1', iss)
        self.assertIn('AP_V32_STABLE_CANDIDATE', batch)

    def test_macos_preserves_original_bundle_identifier(self):
        s = (ROOT / "packaging/build_macos_dmg.sh").read_text("utf-8")
        self.assertIn('BUNDLE_FILE="AnythingPlays31.app"', s)
        self.assertIn('com.anythingplays.release31', s)
        self.assertIn('AnythingPlays-3.2.0-UPGRADE-QA-macos-arm64.dmg', s)
        self.assertIn('AnythingPlays-3.2.0-UPGRADE-QA-macos-x64.dmg', s)
        self.assertIn('Set :CFBundleVersion 3.2.0', s)
        self.assertIn('AP_V32_STABLE_CANDIDATE', s)

    def test_corrupt_or_rebranded_preview_never_becomes_upgrade(self):
        candidate = make_identity("v32_stable_candidate")
        for field, changed in (
            ("public_release_approved", True),
            ("settings_namespace", "anything-plays-32-preview"),
            ("version", "3.1.1"),
            ("channel", "v32_preview"),
        ):
            with self.subTest(field=field):
                bad = dict(candidate)
                bad[field] = changed
                with self.assertRaises(ValueError):
                    validate_identity(bad)


if __name__ == "__main__":
    unittest.main()
