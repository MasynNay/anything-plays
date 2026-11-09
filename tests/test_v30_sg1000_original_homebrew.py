"""Original SG-1000 fixture exercises real TMS9918, not SMS mode-4 video."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from tools.sg1000_homebrew_fixture import (
    ROM_SIZE, build_sg1000_probe_rom, write_sg1000_probe,
)


class OriginalSG1000FixtureTests(unittest.TestCase):
    def test_generates_deterministic_legacy_vdp_cartridge(self):
        rom = build_sg1000_probe_rom()
        self.assertEqual(len(rom), ROM_SIZE)
        self.assertEqual(rom[:4], bytes.fromhex("F3 31 F0 DF"))
        self.assertIn(bytes.fromhex("3E 00 D3 BF 3E 80 D3 BF"), rom[:200])
        self.assertIn(bytes.fromhex("3E C0 D3 BF"), rom[:400])
        self.assertIn(bytes.fromhex("3E 8F D3 7F"), rom[:400])
        self.assertNotIn(b"TMR SEGA", rom)
        self.assertEqual(rom, build_sg1000_probe_rom())

    def test_one_native_8bit_cartridge_without_external_firmware(self):
        with TemporaryDirectory() as root:
            one = Path(root)/"original.sg"
            details = write_sg1000_probe(one)
            self.assertEqual(details["system"], "sg1000")
            self.assertEqual(details["bytes"], 32768)
            self.assertEqual(one.read_bytes(), build_sg1000_probe_rom())
            with self.assertRaises(ValueError):
                write_sg1000_probe(Path(root)/"wrong.sms")


if __name__ == "__main__":
    unittest.main()
