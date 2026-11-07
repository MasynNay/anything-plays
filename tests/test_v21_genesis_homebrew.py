"""Deterministic M68000 Genesis ROM structural regression contracts."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from tools.genesis_homebrew_fixture import (
    ENTRY, ROM_SIZE, build_genesis_probe_rom, write_genesis_probe
)


class GenesisHomebrewTests(unittest.TestCase):
    def test_valid_origin_reset_vector_and_sega_cart_header(self):
        data = build_genesis_probe_rom()
        self.assertEqual(len(data), ROM_SIZE)
        self.assertEqual(int.from_bytes(data[:4], "big"), 0x00FFFF00)
        self.assertEqual(int.from_bytes(data[4:8], "big"), ENTRY)
        self.assertEqual(data[0x100:0x104], b"SEGA")
        self.assertEqual(data[ENTRY:ENTRY+4], b"\x46\xFC\x27\x00")

    def test_test_rom_is_deterministic_and_original(self):
        with TemporaryDirectory() as tmp:
            a = Path(tmp) / "one.md"
            b = Path(tmp) / "two.md"
            x = write_genesis_probe(a)
            y = write_genesis_probe(b)
            self.assertEqual(x["sha256"], y["sha256"])
            self.assertEqual(a.read_bytes(), b.read_bytes())


if __name__ == "__main__":
    unittest.main()
