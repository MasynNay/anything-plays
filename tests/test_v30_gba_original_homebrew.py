"""Original GBA program must be ABI-correct and contain only generated code."""
import unittest
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from tools.gba_homebrew_fixture import (
    SIZE, ENTRY_OFFSET, ROM_BASE, DISPCNT, VRAM_BASE,
    arm_immediate, make_program, build_gba_probe_rom, write_gba_probe,
)

class GBAOriginalCartridgeContracts(unittest.TestCase):
    def test_header_entrypoints_checksum_and_original_arm_body(self):
        rom=build_gba_probe_rom()
        self.assertEqual(len(rom), SIZE)
        self.assertEqual(struct.unpack_from("<I",rom)[0], 0xEA00002E)
        self.assertEqual(rom[0xA0:0xAC], b"ANYTHINGPLAY")
        self.assertEqual(rom[0xB2], 0x96)
        self.assertEqual((sum(rom[0xA0:0xBD])+rom[0xBD])&255, 0x19)
        self.assertEqual(rom[ENTRY_OFFSET:ENTRY_OFFSET+len(make_program())],
                         make_program())
        self.assertEqual(rom,build_gba_probe_rom())

    def test_has_direct_arm_video_and_sound_register_writes(self):
        program=make_program()
        words=[struct.unpack_from("<I",program,i)[0]
               for i in range(0,len(program),4)]
        self.assertIn(0xE18230B5, words)  # STRH pixel to VRAM
        self.assertIn(0xE2555001, words)  # SUBS delay timer
        self.assertIn(0xEA000000|((ENTRY_OFFSET-8)//4),
                      (struct.unpack_from("<I",build_gba_probe_rom(),0)[0],))
        self.assertLess(len(program),2048)

    def test_gba_ci_runs_native_gpu_and_audio_on_each_desktop_platform(self):
        content = (Path(__file__).resolve().parents[1] /
                   ".github/workflows/v30-cores.yml").read_text("utf-8")
        job = content.split("  gba-original-video-audio:", 1)[1].split(
            "  gb-gbc-original-video-audio:", 1
        )[0]
        for target in ("linux-x64", "windows-x64", "macos-arm64", "macos-x64"):
            self.assertIn(target, job)
        self.assertIn("probe_gba_homebrew.py", job)
        self.assertIn("mgba_libretro.", job)

    def test_writer_requires_native_gba_extension(self):
        with TemporaryDirectory() as tmp:
            a=Path(tmp)/"one.gba"
            b=Path(tmp)/"two.gba"
            one=write_gba_probe(a)
            self.assertEqual(one,write_gba_probe(b))
            self.assertEqual(a.read_bytes(),b.read_bytes())
            with self.assertRaises(ValueError):
                write_gba_probe(Path(tmp)/"not-gba.bin")

if __name__=="__main__":
    unittest.main()
