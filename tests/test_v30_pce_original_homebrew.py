"""HuC6280 ROM vectors, hardware banking and PSG/VDC are source-generated."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from tools.pce_homebrew_fixture import (
    ROM_SIZE, RESET_CPU, RESET_VECTOR_ROM_OFFSET,
    build_pce_probe_rom, write_pce_probe,
)


class PCEngineOriginalHuCardContracts(unittest.TestCase):
    def test_vectors_and_hardware_banking(self):
        rom = build_pce_probe_rom()
        self.assertEqual(len(rom), ROM_SIZE)
        self.assertEqual(rom[:3], bytes((0x78, 0xD8, 0xD4)))
        self.assertEqual(
            rom[RESET_VECTOR_ROM_OFFSET:RESET_VECTOR_ROM_OFFSET + 2],
            RESET_CPU.to_bytes(2, "little"),
        )
        self.assertIn(b"\xA9\xFF\x53\x01", rom[:256])
        self.assertIn(b"\xA9\xF8\x53\x02", rom[:256])
        self.assertEqual(build_pce_probe_rom(), rom)

    def test_native_vdc_vce_and_real_psg_writes(self):
        code = build_pce_probe_rom()[:1300]
        for sequence in (
            b"\x03\x00", b"\x03\x02", b"\x03\x05",
            b"\x03\x0B", b"\x03\x0D",
            b"\x8D\x04\x04", b"\x8D\x05\x04",
            b"\x8D\x01\x08", b"\x8D\x04\x08",
            b"\x8D\x06\x08",
        ):
            self.assertIn(sequence, code)

    def test_requires_only_original_hucard_file(self):
        with TemporaryDirectory() as tmp:
            a = Path(tmp)/"original.pce"
            b = Path(tmp)/"second.pce"
            self.assertEqual(write_pce_probe(a), write_pce_probe(b))
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with self.assertRaises(ValueError):
                write_pce_probe(Path(tmp)/"invalid.iso")


if __name__ == "__main__":
    unittest.main()
