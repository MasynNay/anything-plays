"""Original NES fixture and bounded audio+video probe contracts."""
import json
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.nes_homebrew_fixture import build_nes_probe_rom, write_nes_probe
from tools.probe_nes_homebrew import ObservedAudio, _parent


class OriginalNESProbeTests(unittest.TestCase):
    def test_nrom128_has_consistent_vectors_and_cartridge_tiles(self):
        rom = build_nes_probe_rom()
        self.assertEqual(len(rom), 16 + 16384 + 8192)
        self.assertEqual(rom[:6], b"NES\x1a\x01\x01")
        self.assertEqual(rom[16+16384-6:16+16384], b"\x00\x80"*3)
        self.assertEqual(rom[16+16384:16+16384+4], b"\xAA\x55\xAA\x55")
        self.assertEqual(rom, build_nes_probe_rom())

    def test_audio_recorder_rejects_unbounded_native_batches(self):
        audio = ObservedAudio()
        self.assertEqual(audio.batch(C.c_void_p(1), 50000), 0)
        self.assertEqual(audio.samples, 0)
        audio.sample(-40, 0)
        self.assertEqual(audio.peak, 40)
        self.assertEqual(audio.nonzero, 1)

    def test_parent_keeps_crash_result_and_original_fixture_hash(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "fceumm_libretro.so"
            core.write_bytes(b"synthetic")
            report = root / "nes-report.json"
            with patch("tools.probe_nes_homebrew.subprocess.run",
                       return_value=CompletedProcess(["test"], -11,
                                                    stdout="native segfault")):
                self.assertEqual(_parent(core, report, 2), 1)
            saved = json.loads(report.read_text())
            self.assertEqual(saved["native_exit_code"], -11)
            self.assertFalse(saved["passed"])
            self.assertEqual(saved["fixture"]["sha256"],
                             write_nes_probe(root / "rom.nes")["sha256"])


import ctypes as C

if __name__ == "__main__":
    unittest.main()
