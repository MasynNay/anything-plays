"""Original 65816 PPU/SPC program must be deterministic and header-valid."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from tools.snes_homebrew_fixture import (
    CPU_BASE, ROM_SIZE, TEST_SPC_SAMPLE, build_snes_probe_rom, write_snes_probe,
)


class OriginalSNESFixtureTests(unittest.TestCase):
    def test_lorom_header_and_vectors(self):
        rom = build_snes_probe_rom()
        self.assertEqual(len(rom), ROM_SIZE)
        self.assertEqual(rom[:7], bytes.fromhex("78 18 FB C2 10 E2 20"))
        self.assertEqual(rom[0x7FD5], 0x20)
        self.assertEqual(rom[0x7FD7], 0x05)
        self.assertEqual(int.from_bytes(rom[0x7FFC:0x7FFE], "little"), CPU_BASE)
        checksum = int.from_bytes(rom[0x7FDE:0x7FE0], "little")
        complement = int.from_bytes(rom[0x7FDC:0x7FDE], "little")
        self.assertEqual((checksum + complement) & 0xFFFF, 0xFFFF)
        self.assertEqual(rom, build_snes_probe_rom())

    def test_real_ppu_registers_and_spc_boot_handshake(self):
        program = build_snes_probe_rom()[:0x6000]
        for sequence in (
            b"\x8D\x00\x21", b"\x8D\x22\x21",
            b"\x8D\x40\x21", b"\x8D\x41\x21",
            b"\x8D\x42\x21", b"\x8D\x43\x21",
            b"\x8D\x18\x21", b"\x9C\x19\x21",
        ):
            self.assertIn(sequence, program)
        self.assertEqual(len(TEST_SPC_SAMPLE), 22)

    def test_writer_uses_only_snes_extensions(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "original.sfc"
            q = Path(d) / "another.sfc"
            self.assertEqual(write_snes_probe(p), write_snes_probe(q))
            self.assertEqual(p.read_bytes(), q.read_bytes())
            with self.assertRaises(ValueError):
                write_snes_probe(Path(d) / "wrong.smcx")


if __name__ == "__main__":
    unittest.main()
