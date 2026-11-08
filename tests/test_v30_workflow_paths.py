"""Ensure 3.0 release CI calls the moved builders and always rebuilds UI fixes.

These static contract tests prevent the former 127 'build_linux_deb.sh:
No such file or directory' and corresponding Windows/macOS failures after
packaging scripts were reorganized into packaging/.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class V30WorkflowPathTests(unittest.TestCase):
    def test_release_ci_uses_existing_builders(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        for call, path in (
            ("call packaging\\build_windows.bat", "packaging/build_windows.bat"),
            ("bash packaging/build_macos_dmg.sh", "packaging/build_macos_dmg.sh"),
            ("bash packaging/build_linux_deb.sh", "packaging/build_linux_deb.sh"),
        ):
            with self.subTest(path=path):
                self.assertIn(call, workflow)
                self.assertTrue((ROOT / path).is_file())
        self.assertNotIn("run: call build_windows.bat", workflow)
        self.assertNotIn("run: bash build_macos_dmg.sh", workflow)
        self.assertNotIn("run: bash build_linux_deb.sh", workflow)
        self.assertIn("dist/AnythingPlays30Preview.app", workflow)

    def test_full_installer_rebuilds_on_camera_label_changes(self):
        workflow = (ROOT / ".github/workflows/v30-full-bundle.yml").read_text(encoding="utf-8")
        for path in (
            "anything_plays/ui_panels.py",
            "anything_plays/ui_zones.py",
            "anything_plays/zone_rendering.py",
            "tests/test_zone_label_sizing.py",
        ):
            with self.subTest(path=path):
                self.assertIn(f"'{path}'", workflow)
                self.assertTrue((ROOT / path).is_file())


if __name__ == "__main__":
    unittest.main()
