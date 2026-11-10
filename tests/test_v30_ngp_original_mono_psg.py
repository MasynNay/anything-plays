"""Original mono test ROM must use real PSG writes, never fake audio callbacks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest

from tools.build_v30_ngp_original_mono_psg import (
    ENTRY, HEADER_BYTES, ROM_BYTES, VARIANTS, create_original_mono_rom,
    io8, io16, original_mono_psg_code,
)
from tools.probe_v30_ngp_original_mono_psg import STATUS, measure_original_psg


class OriginalMonoPSGResearchContracts(unittest.TestCase):
    def test_actual_mono_header_and_four_documented_psg_modes(self):
        for name in VARIANTS:
            with self.subTest(name=name):
                rom = create_original_mono_rom(name)
                self.assertEqual(len(rom), ROM_BYTES)
                self.assertEqual(rom[0x23], 0)  # Not a relabeled NGPC color ROM!
                self.assertEqual(struct.unpack_from("<I", rom, 0x1C)[0], ENTRY)
                self.assertEqual(rom[HEADER_BYTES:HEADER_BYTES+len(original_mono_psg_code(name))],
                                 original_mono_psg_code(name))
                # Sound ON must be B8=0x55; Z80 must be OFF at B9=0xAA
                # before any direct PSG writes. Never confuse these registers.
                self.assertNotIn(io8(0xB9, 0x55) +
                                 io8(0xA1, 0x8A), rom)
                if name == "direct-tone":
                    self.assertTrue(
                        original_mono_psg_code(name).startswith(
                            io8(0xB9, 0xAA) + io8(0xB8, 0x55)
                        )
                    )
                elif name == "restart-z80-tone":
                    self.assertTrue(
                        original_mono_psg_code(name).startswith(
                            io16(0xB8, 0x5555) + io8(0xB9, 0xAA)
                        )
                    )
                else:
                    self.assertTrue(
                        original_mono_psg_code(name).startswith(
                            io16(0xB8, 0xAA55)
                        )
                    )
                # Exact native PSG tone latch, divider data, loud attenuation.
                self.assertIn(io8(0xA1, 0x8A) + io8(0xA1, 0x0D)
                              + io8(0xA1, 0x90), rom)
                self.assertTrue(rom[HEADER_BYTES:].endswith(b"\xff" * 64))

    def test_cpu_machine_encoding_and_loop_are_unchanged(self):
        self.assertEqual(io8(0xA1, 0x8A), bytes.fromhex("08a18a"))
        self.assertEqual(io16(0xB8, 0xAA55), bytes.fromhex("0ab855aa"))
        self.assertEqual(io8(0xB8, 0x55), bytes.fromhex("08b855"))
        self.assertEqual(io8(0xB9, 0xAA), bytes.fromhex("08b9aa"))
        for name in VARIANTS:
            code = original_mono_psg_code(name)
            self.assertEqual(code[-5:], bytes.fromhex("086f4e68fb"))
        with self.assertRaises(ValueError):
            original_mono_psg_code("fake-color-ROM")
        with self.assertRaises(ValueError):
            io8(300, 1)
        with self.assertRaises(ValueError):
            io16(0xB8, -1)

    def test_original_build_is_deterministic_for_exact_sha256(self):
        for name in VARIANTS:
            self.assertEqual(hashlib.sha256(create_original_mono_rom(name)).hexdigest(),
                             hashlib.sha256(create_original_mono_rom(name)).hexdigest())

    def test_real_native_child_is_required_to_mark_any_pcm_valid(self):
        with TemporaryDirectory() as root:
            root = Path(root)
            core = root / "mednafen_ngp_libretro.so"
            core.write_bytes(b"INERT TEST-NATIVE-LIBRARY-BYTES-" * 8)
            seen = []
            def simulate(cmd, **kwargs):
                self.assertIn("--child", cmd)
                self.assertEqual(cmd[cmd.index("--system")+1], "ngp")
                rom = Path(cmd[cmd.index("--rom")+1])
                self.assertEqual(rom.read_bytes()[0x23], 0)
                num = len(seen)
                native = {
                    "system": "ngp",
                    "native_audio_frames": 40000,
                    "native_nonzero_pcm_values": 140 if num == 1 else 0,
                    "native_audio_peak": 340 if num == 1 else 0,
                    "sampled_nonblank_frames": 8,
                    "manual_a_native_positive_samples": 2,
                    "camera_b_native_positive_samples": 2,
                    "audio_gate_passed": num == 1,
                    "video_gate_passed": True,
                    "input_gate_passed": True,
                    "passed": num == 1,
                }
                Path(cmd[cmd.index("--report")+1]).write_text(json.dumps(native))
                seen.append(rom.read_bytes())
                class Result:
                    stdout = ""
                    stderr = ""
                    returncode = 0 if num == 1 else 1
                return Result()
            report = measure_original_psg(core, root/"evidence", seconds=4, runner=simulate)
            self.assertEqual(len(seen), 4)
            self.assertEqual(report["status"], STATUS)
            self.assertEqual(report["native_pcm_pass_variants"], [VARIANTS[1]])
            self.assertEqual(report["full_native_video_pcm_input_pass_variants"], [VARIANTS[1]])
            self.assertFalse(report["public_release_approved"])
            self.assertFalse(report["binary_redistribution_approved"])
            self.assertFalse(report["combined_license_review_complete"])
            evidence = root / "evidence"
            self.assertEqual({x.name for x in evidence.iterdir()},
                             {"NGP_ORIGINAL_MONO_PSG_UNAPPROVED.json", "SHA256SUMS.txt"})

    def test_no_native_audio_fraud_or_unapproved_rom_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        builder = (root / "tools/build_v30_ngp_original_mono_psg.py").read_text()
        runner = (root / "tools/probe_v30_ngp_original_mono_psg.py").read_text()
        workflow = (root / "docs/history/workflows/v30-ngp-original-mono-psg.yml").read_text()
        self.assertIn("--child", runner)
        self.assertIn("_check_native_child", runner)
        self.assertIn("real_native_audio_gate_passed", runner)
        self.assertIn("NGP_ORIGINAL_MONO_PSG_UNAPPROVED.json", workflow)
        self.assertIn("SOURCE-BUILT-MONO-PSG", workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("gh release upload", workflow)
        self.assertNotIn("continue-on-error: true", workflow)
        self.assertNotIn("C:\\\\TOSHIBA", builder)


if __name__ == "__main__":
    unittest.main()
