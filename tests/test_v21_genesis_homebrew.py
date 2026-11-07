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

    def test_dbcc_displacements_land_on_instruction_boundaries(self):
        # DBRA PC is the EXTENSION word address (opcode address + 2).
        # Both animation DBRAs must target NOP, and the tile-writing DBRA
        # must target MOVE.W D0,(A0). Off-by-2 formerly branched into data.
        rom = build_genesis_probe_rom()
        branches = [
            i for i in range(ENTRY, ROM_SIZE - 3, 2)
            if rom[i:i + 2] == bytes.fromhex("51c9")
        ]
        self.assertEqual(len(branches), 3)
        for instruction, expected in zip(
                branches, (bytes.fromhex("3080"), bytes.fromhex("4e71"),
                           bytes.fromhex("4e71"))):
            with self.subTest(dbcc_at=hex(instruction)):
                displacement = int.from_bytes(
                    rom[instruction + 2:instruction + 4], "big", signed=True
                )
                pc = instruction + 2
                target = pc + displacement
                self.assertGreaterEqual(target, ENTRY)
                self.assertEqual(target % 2, 0)
                self.assertEqual(rom[target:target + 2], expected)

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
