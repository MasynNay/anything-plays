"""Guard 3.1.1 stable upgrade identity against relabeled private QA builds."""
from pathlib import Path
import unittest
from anything_plays.build_identity import make_identity, validate_identity
from tools.write_v31_identity import choose_channel
ROOT=Path(__file__).resolve().parents[1]
STABLE={"AP_V311_STABLE_CANDIDATE":"1","AP_V30_MINIMAL_CORE_BUILD":"1"}

class StableUpdateTests(unittest.TestCase):
    def test_version_and_preferences_survive_upgrade(self):
        new=make_identity("v311_stable_candidate")
        old=make_identity("final_candidate")
        self.assertEqual(new["version"],"3.1.1")
        self.assertEqual(new["title"],"Anything Plays 3.1.1")
        self.assertEqual(new["settings_namespace"],old["settings_namespace"])
        self.assertEqual(new["settings_namespace"],"anything-plays-31")
        self.assertFalse(new["public_release_approved"])
        self.assertEqual(new,validate_identity(new))
        self.assertNotEqual(new["settings_namespace"],make_identity("v311_candidate")["settings_namespace"])

    def test_never_mix_public_release_or_private_qa_modes(self):
        self.assertEqual(choose_channel(STABLE),"v311_stable_candidate")
        for flag in ("AP_V311_CANDIDATE","AP_V31_FINAL_CANDIDATE",
                     "AP_V31_PREVIEW","AP_V31_RC","AP_V31_RC2",
                     "AP_RELEASE_BUILD","AP_V30_APPROVED_RELEASE",
                     "AP_V30_STABLE_CANDIDATE","AP_V30_TEST_CORES"):
            with self.subTest(flag=flag):
                with self.assertRaises(ValueError):
                    choose_channel({**STABLE,flag:"1"})

    def test_linux_installer_upgrades_existing_stable_package(self):
        s=(ROOT/"packaging/build_linux_deb.sh").read_text("utf-8")
        for line in ('VERSION="3.1.1"','PACKAGE_NAME="anything-plays-31"',
                     'INSTALL_ID="anything-plays-31"',
                     'AP_V311_STABLE_CANDIDATE','Name=Anything Plays 3.1.1'):
            self.assertIn(line,s)

    def test_windows_inno_reuses_stable_appid(self):
        s=(ROOT/"packaging/build_windows.bat").read_text("utf-8")
        iss=(ROOT/"packaging/installer.iss").read_text("utf-8")
        self.assertIn('VERSION=3.1.1',s)
        self.assertIn('/DV31FinalBuild=1',s)
        self.assertIn('753B9C90-2D6A-43E4-90E4-49393B3AE025',iss)
        self.assertIn('D2946CA0-E7F8-4667-B1C5-A7733F570311',iss)

    def test_mac_bundle_id_same_but_new_version(self):
        s=(ROOT/"packaging/build_macos_dmg.sh").read_text("utf-8")
        for token in ('BUNDLE_FILE="AnythingPlays31.app"',
                      'com.anythingplays.release31',
                      'AnythingPlays-3.1.1-macos-arm64.dmg',
                      'AnythingPlays-3.1.1-macos-x64.dmg',
                      'Set :CFBundleVersion 3.1.1'):
            self.assertIn(token,s)

    def test_corrupt_identity_cannot_approve_release(self):
        x=make_identity("v311_stable_candidate")
        x["public_release_approved"]=True
        with self.assertRaises(ValueError): validate_identity(x)
        x=make_identity("v311_stable_candidate")
        x["settings_namespace"]="anything-plays-311-candidate"
        with self.assertRaises(ValueError): validate_identity(x)

if __name__=="__main__":
    unittest.main()
