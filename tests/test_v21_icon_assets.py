"""Ensure the corrected 2.1 fish icon ships consistently on every OS.

The approved icon shows the back of the handheld without front-face
buttons. These tests cover asset presence, native format generation,
isolated build output and packaging contracts; visual review remains
the authority for the illustration itself.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import sys
import unittest

from PIL import Image
from verify_bundle import verify_v21_artwork

from tools.render_v21_icon import render, SOURCE, ROOT


class CorrectedIconTests(unittest.TestCase):
    def test_reviewed_source_is_square_and_has_sufficient_resolution(self):
        self.assertTrue(SOURCE.is_file(), "Missing 2.1 fish artwork")
        with Image.open(SOURCE) as source:
            self.assertEqual(source.format, "WEBP")
            self.assertEqual(source.size[0], source.size[1])
            self.assertGreaterEqual(source.size[0], 256)

    def test_generates_all_native_icons_without_editing_stable_assets(self):
        stable_png = ROOT / "assets" / "anything_plays.png"
        stable_ico = ROOT / "assets" / "anything_plays.ico"
        original_png = stable_png.stat().st_size
        original_ico = stable_ico.stat().st_size
        with TemporaryDirectory() as temp:
            # Generate icons in an isolated process. Some native Linux
            # image/codec stacks can fault when an ICO resize runs after
            # OpenCV/libretro integration tests have initialized drivers.
            # This still fails the test if the renderer itself crashes.
            result = subprocess.run(
                [sys.executable, "-c",
                 "from pathlib import Path; import sys; "
                 "from tools.render_v21_icon import render; "
                 "render(output=Path(sys.argv[1]))",
                 temp],
                cwd=ROOT, capture_output=True, text=True, timeout=35,
            )
            self.assertEqual(
                result.returncode, 0,
                f"Native icon generation failed: {result.stderr}",
            )
            png = Path(temp) / "anything_plays.png"
            small = Path(temp) / "anything_plays_small.png"
            ico = Path(temp) / "anything_plays.ico"
            with Image.open(png) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (1024, 1024))
            with Image.open(small) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (256, 256))
            with Image.open(ico) as image:
                self.assertEqual(image.format, "ICO")
                self.assertIn((256, 256), image.info["sizes"])
        self.assertEqual(stable_png.stat().st_size, original_png)
        self.assertEqual(stable_ico.stat().st_size, original_ico)

    def test_bundle_icon_checksum_is_enforced(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            assets = root / "assets"
            assets.mkdir()
            destination = assets / SOURCE.name
            destination.write_bytes(SOURCE.read_bytes())
            verify_v21_artwork(root)
            destination.write_bytes(b"corrupted icon")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                verify_v21_artwork(root)
            destination.unlink()
            with self.assertRaisesRegex(ValueError, "Missing corrected"):
                verify_v21_artwork(root)

    def test_all_alpha_installers_use_corrected_asset(self):
        windows = (ROOT / "build_windows.bat").read_text()
        mac = (ROOT / "build_macos_dmg.sh").read_text()
        linux = (ROOT / "build_linux_deb.sh").read_text()
        inno = (ROOT / "installer.iss").read_text()
        spec = (ROOT / "AnythingPlays.spec").read_text()
        for name, script in (
            ("Windows", windows), ("macOS", mac), ("Linux", linux)
        ):
            with self.subTest(platform=name):
                self.assertIn("render_v21_icon.py", script)
                self.assertIn("anything_plays_v21.webp", script)
        self.assertIn("build\\v21-icon\\anything_plays.ico", windows)
        self.assertIn("build/v21-icon/anything_plays.png", mac)
        self.assertIn("build/v21-icon/anything_plays_small.png", linux)
        self.assertIn("build\\v21-icon\\anything_plays.ico", inno)
        self.assertIn("anything_plays_v21.webp", spec)


if __name__ == "__main__":
    unittest.main()
