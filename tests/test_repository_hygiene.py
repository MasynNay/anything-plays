"""Prevent source tree clutter without moving stable application modules."""
import unittest

from tools.check_repository_hygiene import (
    ROOT_FILES, ROOT_DIRECTORIES, scan_tracked_paths,
)


class RepositoryHygieneTests(unittest.TestCase):
    def test_allowlist_matches_source_root_and_not_experimental_outputs(self):
        self.assertIn("app.py", ROOT_FILES)
        self.assertIn("README.md", ROOT_FILES)
        self.assertIn("packaging", ROOT_DIRECTORIES)
        self.assertIn("anything_plays", ROOT_DIRECTORIES)
        self.assertEqual(scan_tracked_paths([
            "README.md",
            "app.py",
            ".github/workflows/v30-full-bundle.yml",
            "docs/ARCHITECTURE.md",
            "anything_plays/zone_rendering.py",
            "tools/probe_gamecube_app.py",
            "tests/test_zone_label_sizing.py",
            "cores/.gitkeep",
            "assets/anything_plays_v21.webp",
            "packaging/installer.iss",
        ]), [])

    def test_reject_unorganized_files_and_directories(self):
        violations = scan_tracked_paths([
            "build-windows.bat", "untitled.txt", "temp/output.py",
            "release/AnythingPlays.exe",
        ])
        self.assertTrue(any("root file" in item for item in violations))
        self.assertTrue(any("root directory" in item for item in violations))

    def test_reject_emulator_binaries_roms_and_generated_builds(self):
        violations = scan_tracked_paths([
            "cores/dolphin_libretro.so",
            "cores/dolphin-emu/Sys/codehandler.bin",
            "tests/fixtures/proprietary-game.ngp",
            "release/AnythingPlaysSetup-3.0.0.exe",
            "tools/__pycache__/bad.pyc",
        ])
        self.assertTrue(any("Downloaded core data" in item for item in violations))
        self.assertTrue(any("binary checked in" in item for item in violations))
        self.assertTrue(any("Generated cache" in item for item in violations))

    def test_does_not_allow_path_traversal_or_backslash_separator(self):
        problems = scan_tracked_paths([
            "docs/../LICENSE",
            "docs\\unexpected.md",
            "/absolute/private-file",
        ])
        self.assertEqual(len(problems), 3)


if __name__ == "__main__":
    unittest.main()
