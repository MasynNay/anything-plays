"""Original WonderSwan/Color cartridge headers, code and checksum tests."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from tools.wswan_homebrew_fixture import ROM_SIZE,CODE_OFFSET,build_wonder_probe_rom,write_wonder_probe


class WonderSwanOriginalROMContracts(unittest.TestCase):
    def test_footer_has_original_reset_far_jump_and_correct_checksum(self):
        ws=build_wonder_probe_rom("ws")
        wsc=build_wonder_probe_rom("wsc")
        self.assertEqual(len(ws),ROM_SIZE)
        self.assertEqual(ws[-16:-11],bytes.fromhex("EA 00 00 00 F0"))
        self.assertEqual(wsc[-16:-11],ws[-16:-11])
        self.assertEqual(ws[-9],0)
        self.assertEqual(wsc[-9],1)
        self.assertEqual(ws[-6],0)
        for rom in (ws,wsc):
            self.assertEqual(
                int.from_bytes(rom[-2:],"little"),
                sum(rom[:-2])&0xFFFF
            )
            self.assertEqual(rom[CODE_OFFSET],0xFA)
        self.assertNotEqual(ws,wsc)
        self.assertEqual(ws,build_wonder_probe_rom("ws"))

    def test_native_wonderswan_video_and_audio_io_instructions(self):
        ws=build_wonder_probe_rom("ws")[CODE_OFFSET:CODE_OFFSET+300]
        wsc=build_wonder_probe_rom("wsc")[CODE_OFFSET:CODE_OFFSET+300]
        for code in (ws,wsc):
            for io in (0x00,0x07,0x10,0x14,0x8F,0x80,0x81,0x88,0x90,0x91):
                self.assertIn(bytes((0xE6,io)),code)
            self.assertIn(b"\xF3\xAB",code)
        self.assertIn(b"\xE6\x60",wsc)
        self.assertIn(b"\xC7\x06\x02\xFE",wsc)

    def test_files_have_console_correct_extensions(self):
        with TemporaryDirectory() as folder:
            for system in ("ws","wsc"):
                path=Path(folder)/("original."+system)
                result=write_wonder_probe(path,system)
                self.assertEqual(result["bytes"],ROM_SIZE)
                self.assertEqual(path.read_bytes(),build_wonder_probe_rom(system))
            with self.assertRaises(ValueError):
                build_wonder_probe_rom("gba")


if __name__=="__main__":
    unittest.main()
