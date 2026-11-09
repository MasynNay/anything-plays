"""Validate original Sega 8-bit cartridge format, Z80 branches and IO writes."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from tools.sega8_homebrew_fixture import (
    ROM_SIZE, SYSTEMS, build_sega8_probe_rom, write_sega8_probe,
)


class Sega8OriginalFixtureTests(unittest.TestCase):
    def test_sms_gg_headers_are_deterministic_and_distinct(self):
        sms = build_sega8_probe_rom("mastersystem")
        gg = build_sega8_probe_rom("gamegear")
        self.assertEqual(len(sms), ROM_SIZE)
        self.assertEqual(len(gg), ROM_SIZE)
        self.assertEqual(sms[0], 0xF3)
        self.assertEqual(gg[0], 0xF3)
        self.assertEqual(sms[0x7FF0:0x7FF8], b"TMR SEGA")
        self.assertEqual(sms[0x7FFF], 0x4C)
        self.assertEqual(gg[0x7FFF], 0x6C)
        self.assertNotEqual(sms, gg)
        self.assertEqual(sms, build_sega8_probe_rom("mastersystem"))

    def test_original_program_writes_native_vdp_and_psg_ports(self):
        for system in SYSTEMS:
            with self.subTest(system=system):
                code = build_sega8_probe_rom(system)[:1600]
                for command in (b"\xD3\xBF", b"\xD3\xBE", b"\xD3\x7F"):
                    self.assertIn(command, code)
                self.assertIn(b"\x01\x00\x07", code)
                self.assertIn(b"\xC3", code)

    def test_exported_files_match_platform_specific_extensions(self):
        with TemporaryDirectory() as d:
            for system, suffix in (("mastersystem", ".sms"), ("gamegear", ".gg")):
                with self.subTest(system=system):
                    f = Path(d) / ("test" + suffix)
                    info = write_sega8_probe(f, system)
                    self.assertEqual(info["bytes"], 32768)
                    self.assertEqual(f.read_bytes(), build_sega8_probe_rom(system))
            with self.assertRaises(ValueError):
                write_sega8_probe(Path(d) / "wrong.sms", "gamegear")
            with self.assertRaises(ValueError):
                build_sega8_probe_rom("sg1000")


if __name__ == "__main__":
    unittest.main()
