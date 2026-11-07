"""Keep alpha installers and CI artifact names independent of stable v2.0."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PackagingContractTests(unittest.TestCase):
    def source(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def test_windows_alpha_appid_and_install_dir_are_distinct(self):
        installer = self.source("packaging/installer.iss")
        self.assertIn('#define AppName "Anything Plays 3.0 Preview"', installer)
        self.assertIn('DefaultDirName={autopf}\\Anything Plays 3.0 Preview', installer)
        self.assertIn('1DCC721E-A1D2-4A91-8B49-C7A453EEDB21', installer)
        self.assertNotIn('D5C81347-28B4-4F0D-BA82-1D441A83C0F5', installer)

    def test_macos_alpha_has_separate_app_and_dmg(self):
        script = self.source("packaging/build_macos_dmg.sh")
        ci = self.source(".github/workflows/v30-preview-build.yml")
        self.assertIn('AnythingPlays21Test.app', script)
        self.assertIn('com.anythingplays.test21', script)
        self.assertIn('release/AnythingPlays-3.0.0-alpha.1.dmg', script)
        self.assertIn('dist/AnythingPlays21Test.app', ci)
        self.assertIn('release/AnythingPlays-3.0.0-alpha.1.dmg', ci)

    def test_linux_alpha_package_is_unique_and_launchable(self):
        script = self.source("packaging/build_linux_deb.sh")
        ci = self.source(".github/workflows/v30-preview-build.yml")
        self.assertIn('Package: anything-plays-preview', script)
        self.assertIn('Name=Anything Plays 3.0 Preview', script)
        self.assertIn('Exec=anything-plays-30-preview', script)
        self.assertIn('Icon=anything-plays-preview', script)
        self.assertIn('/opt/anything-plays-30-preview', script)
        self.assertIn('release/anything-plays-preview_3.0.0~alpha1_amd64.deb', ci)


if __name__ == "__main__":
    unittest.main()
