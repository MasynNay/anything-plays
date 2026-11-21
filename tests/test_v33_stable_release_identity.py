"""3.3 final-version stable upgrade has an explicit, nonpublic source stage."""
import unittest
from pathlib import Path

from anything_plays.build_identity import make_identity, validate_identity
from tools.write_v31_identity import choose_channel

ROOT = Path(__file__).resolve().parents[1]


class StableV33IdentityTests(unittest.TestCase):
    def test_same_stable_settings_namespace_and_exact_3_3_version(self):
        old = make_identity("v32_stable_candidate")
        new = make_identity("v33_stable_candidate")
        self.assertEqual(new["version"], "3.3.0")
        self.assertEqual(new["settings_namespace"], old["settings_namespace"])
        self.assertEqual(new["channel"], "v33_stable_candidate")
        self.assertFalse(new["public_release_approved"])
        self.assertEqual(validate_identity(new), new)

    def test_only_exclusive_nonrelease_build_channel_is_accepted(self):
        env = {"AP_V33_STABLE_CANDIDATE": "1",
               "AP_V30_MINIMAL_CORE_BUILD": "1",
               "AP_RELEASE_BUILD": "0"}
        self.assertEqual(choose_channel(env), "v33_stable_candidate")
        for additional in ("AP_V33_CANDIDATE", "AP_V32_STABLE_CANDIDATE",
                           "AP_V31_FINAL_CANDIDATE"):
            with self.subTest(flag=additional):
                with self.assertRaises(ValueError):
                    choose_channel({**env, additional: "1"})
        for forbidden in ("AP_RELEASE_BUILD", "AP_V30_APPROVED_RELEASE",
                          "AP_V30_STABLE_CANDIDATE"):
            with self.subTest(flag=forbidden):
                with self.assertRaises(ValueError):
                    choose_channel({**env, forbidden: "1"})
        with self.assertRaises(ValueError):
            choose_channel({"AP_V33_STABLE_CANDIDATE": "1"})

    def test_both_platforms_keep_original_installer_identity(self):
        win = (ROOT / "packaging" / "installer.iss").read_text("utf-8")
        self.assertIn("defined(V33StableFinalBuild)", win)
        self.assertIn("AppId={{753B9C90-2D6A-43E4-90E4-49393B3AE025}", win)
        self.assertIn("defined(V33StableQABuild) || defined(V33StableFinalBuild)", win)
        self.assertIn("AnythingPlaysSetup-{#AppVersion}-PRIVATE-UPGRADE-QA", win)
        mac = (ROOT / "packaging" / "build_macos_dmg.sh").read_text("utf-8")
        self.assertIn('BUNDLE_FILE="AnythingPlays31.app"', mac)
        self.assertIn("com.anythingplays.release31", mac)
        self.assertIn('DMG_NAME="AnythingPlays-3.3.0-UPGRADE-QA-macos-arm64.dmg"', mac)
        linux = (ROOT / "packaging" / "build_linux_deb.sh").read_text("utf-8")
        self.assertIn('VERSION="3.3.0~upgradeqa1"', linux)
        self.assertIn('PACKAGE_NAME="anything-plays-31"', linux)
        self.assertIn('INSTALL_ID="anything-plays-31"', linux)

    def test_qa_packaging_remains_nonpublic_and_separate_from_3_3_private(self):
        for path in ("packaging/build_linux_deb.sh",
                     "packaging/build_macos_dmg.sh",
                     "packaging/build_windows.bat"):
            with self.subTest(path=path):
                value = (ROOT / path).read_text("utf-8")
                self.assertIn("AP_V33_STABLE_CANDIDATE", value)
                self.assertIn("AP_V33_CANDIDATE", value)
                self.assertIn("AP_RELEASE_BUILD", value)


if __name__ == "__main__":
    unittest.main()
