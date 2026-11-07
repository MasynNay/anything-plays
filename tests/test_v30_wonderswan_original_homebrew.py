"""WonderSwan and WonderSwan Color source ROM contracts, no original games."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from tools.wonderswan_homebrew_fixture import (
    ROM_SIZE, SYSTEMS, build_wonderswan_probe_rom, write_wonderswan_probe,
)


class WonderSwanOriginalCartridgeTests(unittest.TestCase):
    def test_both_cartridges_have_wonderswan_reset_vector_and_checksum(self):
        ws = build_wonderswan_probe_rom("ws")
        wsc = build_wonderswan_probe_rom("wsc")
        self.assertEqual(len(ws), ROM_SIZE)
        self.assertEqual(len(wsc), ROM_SIZE)
        for data in (ws, wsc):
            self.assertEqual(data[:3], bytes.fromhex("FA 31 C0"))
            self.assertEqual(data[-16:-11], bytes.fromhex("EA 00 00 00 E0"))
            self.assertEqual(data[-6], 0)
            self.assertEqual(int.from_bytes(data[-2:], "little"),
                             sum(data[:-2]) & 0xFFFF)
        self.assertEqual(ws[-9], 0)
        self.assertEqual(wsc[-9], 1)
        self.assertNotEqual(ws, wsc)

    def test_native_video_and_audio_port_io_in_both_programs(self):
        for system in SYSTEMS:
            with self.subTest(system=system):
                code = build_wonderswan_probe_rom(system)[:2048]
                for port in (0x00, 0x07, 0x14, 0x80, 0x81,
                             0x88, 0x8F, 0x90, 0x91):
                    self.assertIn(bytes((0xE6, port)), code)
                self.assertIn(bytes.fromhex("F3 AB"), code)
        self.assertIn(bytes.fromhex("B0 80 E6 60"),
                      build_wonderswan_probe_rom("wsc")[:2048])
        self.assertIn(bytes.fromhex("BF 00 20"),
                      build_wonderswan_probe_rom("wsc")[:2048])
        self.assertNotIn(bytes.fromhex("B0 20 E6 60"),
                         build_wonderswan_probe_rom("wsc")[:2048])

    def test_writer_creates_only_legal_test_rom_extensions(self):
        with TemporaryDirectory() as folder:
            for system in SYSTEMS:
                target = Path(folder) / ("test." + system)
                info = write_wonderswan_probe(target, system)
                self.assertEqual(info["bytes"], 128 * 1024)
                self.assertFalse(info["requires_bios_file"])
                self.assertEqual(target.read_bytes(),
                                 build_wonderswan_probe_rom(system))
            with self.assertRaises(ValueError):
                write_wonderswan_probe(Path(folder)/"wrong.ws","wsc")


if __name__ == "__main__":
    unittest.main()
