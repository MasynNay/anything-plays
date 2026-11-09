"""Original 68000 staged cartridge isolates native initialization failures."""
import unittest
from tools.genesis_homebrew_fixture import PHASES, ROM_SIZE, ENTRY, build_genesis_probe_rom


class GenesisStageIsolationContracts(unittest.TestCase):
    def test_all_diagnostic_phases_preserve_cartridge_header_and_vectors(self):
        full = build_genesis_probe_rom()
        self.assertEqual(PHASES[0], "idle")
        self.assertEqual(PHASES[-1], "full")
        self.assertEqual(len(PHASES), 8)
        for phase in PHASES:
            with self.subTest(phase=phase):
                rom = build_genesis_probe_rom(phase)
                self.assertEqual(len(rom), ROM_SIZE)
                self.assertEqual(rom[:8], full[:8])
                self.assertEqual(rom[0x100:0x104], b"SEGA")
                if phase != "full":
                    self.assertNotEqual(rom, full)
                    self.assertIn(b"\x60\xfe", rom[ENTRY:ENTRY+4096])
        self.assertEqual(full, build_genesis_probe_rom())

    def test_invalid_phase_fails_closed(self):
        with self.assertRaises(ValueError):
            build_genesis_probe_rom("unexpected")


if __name__ == "__main__":
    unittest.main()
