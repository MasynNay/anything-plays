"""Frozen desktop installers must include the native in-panel GameCube GPU bridge."""
from pathlib import Path
import unittest


class PackagedGameCubeGPUHostTests(unittest.TestCase):
    def test_all_platform_builds_collect_native_glcontext_extensions(self):
        root = Path(__file__).resolve().parents[1] / "packaging"
        for name in ("build_windows.bat", "build_macos_dmg.sh",
                     "build_linux_deb.sh"):
            with self.subTest(platform_build=name):
                script = (root / name).read_text(encoding="utf-8")
                self.assertIn("--collect-all glcontext", script)
                self.assertIn("PyInstaller", script)

    def test_starter_builds_are_not_suddenly_forced_to_bundle_dolphin(self):
        # GameCube is a user-chosen paired-core download, not a forced
        # multi-hundred-MB addition to the starter installer.
        root = Path(__file__).resolve().parents[1]
        build = (root / ".github/workflows/v30-app.yml").read_text(
            encoding="utf-8")
        self.assertIn("AP_V30_MINIMAL_CORE_BUILD: '1'", build)
        for platform in ("Windows", "macOS", "Linux"):
            self.assertIn("mGBA starter core", build)
