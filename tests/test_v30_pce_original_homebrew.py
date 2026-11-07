"""Original PC Engine ROM uses actual HuC6280 VCE/VDC and PSG register IO."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.pce_homebrew_fixture import (
    ROM_SIZE, CPU_ENTRY, BANK_BYTES, build_pce_probe_rom, write_pce_probe,
)


class OriginalPCEHomebrewTests(unittest.TestCase):
    def test_vce_vdc_and_psg_registers_are_written_from_native_cpu(self):
        rom = build_pce_probe_rom()
        self.assertEqual(len(rom), ROM_SIZE)
        self.assertEqual(rom[:2], bytes.fromhex("78 D8"))
        self.assertIn(bytes.fromhex("A9 FF 53 01"), rom[:128])
        self.assertIn(bytes.fromhex("A9 F8 53 02"), rom[:128])
        for addr in (0x0000, 0x0002, 0x0003, 0x0402, 0x0404,
                     0x0800, 0x0801, 0x0802, 0x0804, 0x0806):
            with self.subTest(register=hex(addr)):
                self.assertIn(
                    bytes((0x8D, addr & 255, addr >> 8)), rom[:0x1800]
                )
        for base in range(0, ROM_SIZE, BANK_BYTES):
            self.assertEqual(rom[base+0x1FFE:base+0x2000],
                             CPU_ENTRY.to_bytes(2, "little"))
        self.assertEqual(rom, build_pce_probe_rom())

    def test_test_rom_is_generated_only_for_hucard_extension(self):
        with TemporaryDirectory() as folder:
            first = Path(folder) / "a.pce"
            second = Path(folder) / "b.pce"
            a = write_pce_probe(first)
            b = write_pce_probe(second)
            self.assertEqual(a, b)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertFalse(a["requires_cd_bios"])
            with self.assertRaises(ValueError):
                write_pce_probe(Path(folder) / "wrong.cue")


if __name__ == "__main__":
    unittest.main()
