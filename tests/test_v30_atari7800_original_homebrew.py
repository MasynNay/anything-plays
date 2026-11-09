"""Atari 7800 original A78 has valid format and touches MARIA/TIA registers."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from tools.atari7800_homebrew_fixture import (
    ROM_SIZE, HEADER_SIZE, build_atari7800_probe_rom, write_atari7800_probe,
)


class OriginalAtari7800FixtureContracts(unittest.TestCase):
    def test_a78_header_6502_vectors_and_native_registers(self):
        rom = build_atari7800_probe_rom()
        self.assertEqual(len(rom), HEADER_SIZE + ROM_SIZE)
        self.assertEqual(rom[0], 1)
        self.assertEqual(rom[1:10], b"ATARI7800")
        self.assertEqual(int.from_bytes(rom[49:53], "big"), ROM_SIZE)
        self.assertEqual(rom[HEADER_SIZE:HEADER_SIZE+5], b"\x78\xD8\xA2\xFF\x9A")
        self.assertEqual(rom[100:128], b"ACTUAL CART DATA STARTS HERE")
        self.assertIn(bytes((0xA9, 0x07, 0x85, 0x01)), rom[:HEADER_SIZE + 512])
        self.assertIn(bytes((0xA9, 0x40, 0x85, 0x3C)), rom[:HEADER_SIZE + 1024])
        self.assertEqual(rom[HEADER_SIZE + 0x1000:HEADER_SIZE + 0x1004],
                         bytes.fromhex("AA E4 1B FF"))
        self.assertEqual(rom[HEADER_SIZE+ROM_SIZE-8:HEADER_SIZE+ROM_SIZE-6],
                         b"\xFF\x87")
        self.assertEqual(rom[-4:-2], b"\x00\x80")
        code = rom[HEADER_SIZE:HEADER_SIZE+1024]
        for register in (0x20, 0x24, 0x15, 0x17, 0x19):
            self.assertIn(bytes((0x85, register)), code)
        self.assertEqual(rom, build_atari7800_probe_rom())

    def test_original_cartridge_is_not_shipped_as_part_of_app(self):
        with TemporaryDirectory() as tmp:
            p = Path(tmp)/"original.a78"
            details = write_atari7800_probe(p)
            self.assertEqual(details["bytes"], 32896)
            self.assertEqual(p.read_bytes(), build_atari7800_probe_rom())
            with self.assertRaises(ValueError):
                write_atari7800_probe(Path(tmp)/"wrong.bin")


if __name__ == "__main__":
    unittest.main()
