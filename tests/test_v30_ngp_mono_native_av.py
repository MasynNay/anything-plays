"""Byte-exact original K1GE/PSG mono animation and strict native CI evidence tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest

from tools.build_v30_ngp_mono_native_av import (
    BACKGROUND_CONTROL, BACKGROUND_SHADES, HEADER_BYTES, ROM_BYTES, STATUS,
    WINDOW_REGISTERS, create_original_mono_av_rom,
    frame_delay, original_monochrome_audio_video_code,
    store8_absolute,
)
from tools.build_v30_ngp_original_mono_psg import original_mono_psg_code
from tools.probe_v30_ngp_mono_native_av import native_monochrome_av


class AuthenticMonoAVTests(unittest.TestCase):
    def test_exact_source_generated_mono_cart_and_native_audio_boot(self):
        rom = create_original_mono_av_rom()
        self.assertEqual(len(rom), ROM_BYTES)
        self.assertEqual(rom[0x23], 0)
        self.assertEqual(struct.unpack_from("<I", rom, 0x1c)[0], 0x200040)
        boot = original_mono_psg_code("stop-z80-tone")[:-5]
        self.assertEqual(rom[HEADER_BYTES:HEADER_BYTES + len(boot)], boot)
        self.assertIn(bytes.fromhex("0ab855aa"), boot)
        self.assertIn(bytes.fromhex("08a18a08a10d08a190"), boot)
        body = original_monochrome_audio_video_code()
        self.assertEqual(rom[HEADER_BYTES:HEADER_BYTES + len(body)], body)
        self.assertTrue(rom.endswith(b"\xff" * 256))
        self.assertEqual(
            hashlib.sha256(create_original_mono_av_rom()).hexdigest(),
            hashlib.sha256(rom).hexdigest(),
        )

    def test_real_k1ge_video_address_and_monochrome_palette_values(self):
        self.assertEqual(WINDOW_REGISTERS, (
            (0x8002, 10), (0x8003, 10), (0x8004, 140), (0x8005, 132),
        ))
        self.assertEqual(BACKGROUND_CONTROL, 0x8118)
        self.assertEqual(BACKGROUND_SHADES, (0x83, 0x87))
        self.assertEqual(store8_absolute(0x8118, 0x87),
                         bytes.fromhex("2187f1188141"))
        with self.assertRaises(ValueError):
            store8_absolute(0x10000, 1)
        with self.assertRaises(ValueError):
            store8_absolute(0x8118, 300)
        code = original_monochrome_audio_video_code()
        for address, value in WINDOW_REGISTERS:
            self.assertIn(store8_absolute(address, value), code)
        for shade in BACKGROUND_SHADES:
            self.assertIn(store8_absolute(BACKGROUND_CONTROL, shade), code)
        # The last JR must be a real backward branch to the first animation
        # iteration, not an infinite loop pointing inside the instruction.
        self.assertEqual(code[-2], 0x68)
        offset = int.from_bytes(code[-1:], "little", signed=True)
        target = len(code) + offset
        first = code.index(bytes.fromhex("086f4e"), 15)
        self.assertEqual(target, first)

    def test_delay_byte_register_decrements_update_zero_flag(self):
        self.assertEqual(frame_delay(96),
                         bytes.fromhex("226023ffcb696efcca696ef6"))
        with self.assertRaises(ValueError):
            frame_delay(0)
        with self.assertRaises(ValueError):
            frame_delay(256)

    def test_report_requires_real_native_audio_video_input_simulated_contract(self):
        with TemporaryDirectory() as td:
            p = Path(td)
            core = p/"actual_native.so"
            core.write_bytes(b"UNIT TEST FAKE CORE" * 15)
            def fake_runner(cmd, **kwargs):
                self.assertIn("--child", cmd)
                self.assertEqual(cmd[cmd.index("--system")+1], "ngp")
                self.assertEqual(Path(cmd[cmd.index("--rom")+1]).read_bytes()[0x23], 0)
                details = {
                    "system": "ngp",
                    "native_video_frames": 720,
                    "observed_fps": 59.7,
                    "sampled_nonblank_frames": 600,
                    "distinct_nonblank_frames": 2,
                    "distinct_all_frames": 2,
                    "rgb_min_max": [20, 250],
                    "native_audio_frames": 400000,
                    "native_nonzero_pcm_values": 300000,
                    "native_audio_peak": 6000,
                    "sample_rate": 44100,
                    "video_gate_passed": True,
                    "audio_gate_passed": True,
                    "input_gate_passed": True,
                    "manual_a_native_positive_samples": 15,
                    "camera_b_native_positive_samples": 14,
                    "save_state_roundtrip": {"supported": True},
                    "passed": True,
                }
                Path(cmd[cmd.index("--report")+1]).write_text(json.dumps(details))
                class Result:
                    returncode = 0
                    stdout = ""
                    stderr = ""
                return Result()
            info = native_monochrome_av(core, p/"results",
                                          seconds=5, runner=fake_runner)
            self.assertTrue(info["full_native_audio_video_input_verified"])
            self.assertFalse(info["public_distribution_approved"])
            self.assertFalse(info["all_four_platforms_verified"])
            self.assertFalse(info["physical_speaker_or_retail_gameplay_verified"])
            self.assertEqual(
                {x.name for x in (p/"results").iterdir()},
                {"NGP_ORIGINAL_MONO_K1GE_NATIVE_AV_UNAPPROVED.json", "SHA256SUMS.txt"},
            )

    def test_no_real_signal_means_no_native_release_pass(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            core = root/"actual_native.so"
            core.write_bytes(b"UNIT TEST FAKE CORE" * 15)
            def silent_runner(cmd, **kwargs):
                details = {
                    "system": "ngp",
                    "native_video_frames": 600, "observed_fps": 60,
                    "sampled_nonblank_frames": 0, "distinct_nonblank_frames": 0,
                    "distinct_all_frames": 1, "rgb_min_max": [20, 20],
                    "native_audio_frames": 400000,
                    "native_nonzero_pcm_values": 0, "native_audio_peak": 0,
                    "sample_rate": 44100, "video_gate_passed": False,
                    "audio_gate_passed": False, "input_gate_passed": True,
                    "manual_a_native_positive_samples": 15,
                    "camera_b_native_positive_samples": 15,
                    "save_state_roundtrip": {"supported": False},
                    "passed": False,
                }
                Path(cmd[cmd.index("--report")+1]).write_text(json.dumps(details))
                class Result:
                    returncode = 1
                    stdout = ""
                    stderr = ""
                return Result()
            info = native_monochrome_av(core, root/"out", seconds=5,
                                        runner=silent_runner)
            self.assertFalse(info["full_native_audio_video_input_verified"])
            self.assertFalse(info["audio_verified_in_native_test"])
            self.assertFalse(info["changing_monochrome_video_verified_in_native_test"])
            self.assertTrue(info["native_manual_and_camera_input_query_verified"])

    def test_workflow_does_not_distribute_roms_or_approve_public_release(self):
        base = Path(__file__).resolve().parents[1]
        yml = (base/".github/workflows/v30-ngp-mono-native-av.yml").read_text("utf-8")
        self.assertIn("probe_v30_ngp_mono_native_av", yml)
        self.assertIn("fail-fast: false", yml)
        for target in ("linux-x64", "windows-x64",
                       "macos-arm64", "macos-x64"):
            self.assertIn(f"target: {target}", yml)
        self.assertIn("matrix.ext", yml)
        self.assertIn("matrix.target", yml)
        self.assertIn("if: runner.os == 'Linux'", yml)
        self.assertIn("NGP_ORIGINAL_MONO_K1GE_NATIVE_AV_UNAPPROVED.json", yml)
        self.assertNotIn("gh release create", yml)
        self.assertNotIn("continue-on-error: true", yml)
        self.assertNotIn("*.ngp", yml)


if __name__ == "__main__":
    unittest.main()
