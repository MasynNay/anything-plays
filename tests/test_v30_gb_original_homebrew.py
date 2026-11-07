"""Generated Game Boy test images contain only original LR35902 instructions."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from tools.gb_homebrew_fixture import ENTRY, SIZE, build_gb_probe_rom, write_gb_probe

class GameBoyOriginalCartridgeTests(unittest.TestCase):
    def test_deterministic_header_and_cgb_flags(self):
        a=build_gb_probe_rom("gb")
        b=build_gb_probe_rom("gbc")
        self.assertEqual(len(a), SIZE)
        self.assertEqual(len(b), SIZE)
        self.assertEqual(a[0x100:0x103], b"\xc3\x50\x01")
        self.assertEqual(a[ENTRY], 0xf3)
        self.assertEqual(a[0x143], 0)
        self.assertEqual(b[0x143], 0x80)
        self.assertNotEqual(a, b)
        for rom in (a,b):
            self.assertEqual((sum(rom[0x134:0x14d])+rom[0x14d]+25)&255,0)

    def test_original_software_operates_lcd_and_square_channel(self):
        code=build_gb_probe_rom()[ENTRY:ENTRY+150]
        for data in (b"\xe0\x26",b"\xe0\x24",b"\xe0\x25",
                     b"\xe0\x14",b"\xe0\x40",b"\xe0\x43"):
            self.assertIn(data, code)

    def test_writer_does_not_accept_a_different_console(self):
        with TemporaryDirectory() as folder:
            one=Path(folder)/"one.gb"
            two=Path(folder)/"two.gb"
            self.assertEqual(write_gb_probe(one),{**write_gb_probe(two)})
            self.assertEqual(one.read_bytes(), two.read_bytes())
            with self.assertRaises(ValueError):
                write_gb_probe(Path(folder)/"wrong.gbc","gb")
            with self.assertRaises(ValueError):
                build_gb_probe_rom("gba")

if __name__ == "__main__":
    unittest.main()
