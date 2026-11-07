"""An internal four-platform lab must build fully offline-ready installers."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OfflineInstallerLabContractTests(unittest.TestCase):
    def test_full_lab_is_separate_from_starter_artifacts(self):
        text = (ROOT / ".github/workflows/v30-full-bundle.yml").read_text("utf-8")
        self.assertIn("AP_V30_TEST_CORES: '1'", text)
        for runner in ("windows-2025", "macos-15", "macos-15-intel", "ubuntu-24.04"):
            self.assertIn(runner, text)
        for script in ("build_windows.bat", "build_macos_dmg.sh", "build_linux_deb.sh"):
            self.assertIn(script, text)
        self.assertIn("dolphin-emu/Sys/codehandler.bin", text)
        self.assertIn("len(SYSTEMS) == 18", text)
        self.assertIn("len(expected) == 11", text)
        self.assertNotIn("uses: actions/upload-artifact", text)
        self.assertNotIn("AP_V30_MINIMAL_CORE_BUILD", text)


if __name__ == "__main__":
    unittest.main()
