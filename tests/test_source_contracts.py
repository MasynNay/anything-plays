"""Dependency-free regression checks for compatibility-sensitive source contracts."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourceContracts(unittest.TestCase):
    def test_python_modules_parse(self):
        for filename in ("app.py", "cameras.py", "gba_emulator.py", "fetch_mgba_core.py"):
            with self.subTest(filename=filename):
                ast.parse((ROOT / filename).read_text(encoding="utf-8"))

    def test_legacy_preferences_location_preserved(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("'fish-plays-pokemon-studio' / 'preferences.json'", source)

    def test_profile_migration_preserved(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("cfg['zones'].setdefault('Select'", source)
        self.assertIn("cfg['zones'].setdefault('Shuffle'", source)

    def test_platform_build_scripts_retained(self):
        for filename in ("build_windows.bat", "build_macos_dmg.sh", "build_linux_deb.sh", "build_macos_linux.sh", "installer.iss", "AnythingPlays.spec"):
            with self.subTest(filename=filename):
                self.assertTrue((ROOT / filename).is_file())


if __name__ == "__main__":
    unittest.main()
