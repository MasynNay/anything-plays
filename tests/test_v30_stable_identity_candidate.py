"""Guard nonpublic true-version candidates against a fake stable publication."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TrueVersionCandidateBuildTests(unittest.TestCase):
    def test_shell_packagers_syntax(self):
        for name in ("build_linux_deb.sh", "build_macos_dmg.sh"):
            with self.subTest(name=name):
                path = ROOT / "packaging" / name
                p = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
                self.assertEqual(p.returncode, 0, p.stderr)

    def test_all_three_packagers_reject_unreviewed_production_bypass(self):
        for name in ("build_linux_deb.sh", "build_macos_dmg.sh", "build_windows.bat"):
            with self.subTest(name=name):
                source = (ROOT / "packaging" / name).read_text(encoding="utf-8")
                self.assertIn("AP_V30_STABLE_CANDIDATE", source)
                self.assertIn("AP_V30_GPL_TRIAL", source)
                self.assertIn("AP_V30_TIA_TRIAL", source)
                self.assertIn("AP_V30_TEST_CORES", source)
                self.assertIn("AP_V30_APPROVED_RELEASE", source)
                self.assertIn("AP_RELEASE_BUILD", source)
                self.assertIn("3.0.0", source)

    def test_app_identity_is_real_in_each_package(self):
        linux = (ROOT / "packaging/build_linux_deb.sh").read_text("utf-8")
        mac = (ROOT / "packaging/build_macos_dmg.sh").read_text("utf-8")
        win = (ROOT / "packaging/build_windows.bat").read_text("utf-8")
        self.assertIn('PACKAGE_NAME="anything-plays"', linux)
        self.assertIn('VERSION="3.0.0"', linux)
        self.assertIn("macos-arm64.dmg", mac)
        self.assertIn("macos-x64.dmg", mac)
        self.assertIn("CFBundleShortVersionString 3.0.0", mac)
        self.assertIn("CFBundleVersion 3.0.0", mac)
        self.assertIn('/DProductionBuild=1 /DAppVersion=%VERSION%', win)
        self.assertIn('set "VERSION=3.0.0"', win)

    def test_stable_candidate_is_explicitly_nonpublic(self):
        workflow = (ROOT / ".github/workflows/v30-retain-four-offline-v3-installers.yml").read_text("utf-8")
        self.assertIn("AnythingPlays-3.0.0-REAL-FOUR-OS-IDENTITY", workflow)
        self.assertIn("UNAPPROVED-OWNER-ONLY-REAL-3.0.0-IDENTITY-CANDIDATE", workflow)
        self.assertIn('"public_binary_distribution_approved":False', workflow)
        self.assertIn('"official_stable_release":False', workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertIn("ACTUAL_INSTALLED_7_CYCLE_SWITCH_UNAPPROVED.json", workflow)


if __name__ == "__main__":
    unittest.main()
