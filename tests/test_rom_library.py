"""ROM browsing and cartridge artwork should work without a GUI or network."""

from pathlib import Path
import tempfile
import unittest

from PIL import Image

from anything_plays.cartridge_art import cartridge_image
from anything_plays.rom_library import find_cover_art, scan_rom_directory


class ROMLibraryTests(unittest.TestCase):
    def test_filters_nested_roms_by_selected_console(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "A.gba").write_bytes(b"sample")
            (root / "B.GB").write_bytes(b"sample")
            (root / "inside").mkdir()
            (root / "inside" / "C.gba").write_bytes(b"sample")
            result = scan_rom_directory(root, (".gba",))
            self.assertEqual([p.stem for p in result], ["A", "C"])

    def test_cover_art_prefers_game_named_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rom = root / "The Game.sfc"
            (root / "cover.png").write_bytes(b"cover")
            (root / "The Game.png").write_bytes(b"game")
            self.assertEqual(find_cover_art(rom).name, "The Game.png")

    def test_cartridge_background_is_transparent_for_all_consoles(self):
        for console in ("gb", "gbc", "gba", "snes"):
            with self.subTest(console=console):
                picture = cartridge_image("Sample Title", console)
                self.assertEqual(picture.size, (300, 226))
                self.assertEqual(picture.mode, "RGBA")
                self.assertEqual(picture.getpixel((0, 0))[3], 0)
                self.assertGreater(picture.getpixel((150, 100))[3], 0)

    def test_custom_cover_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            cover = Path(tmp) / "cover.png"
            Image.new("RGB", (80, 60), "orange").save(cover)
            picture = cartridge_image("Demo", "snes", cover)
            self.assertEqual(picture.mode, "RGBA")


if __name__ == "__main__":
    unittest.main()
