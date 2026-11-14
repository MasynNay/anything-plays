"""GameCube native-loop cost must be separated from GPU readback and audio.

These are real numeric counters from retro_run(), not a fabricated FPS
estimate. Do not claim rendering changes improved performance merely
because an offscreen Mesa runner differs from a user's GPU.
"""
import math
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, Mock, patch
from types import SimpleNamespace

from anything_plays.gamecube_native_timing import GameCubeNativeTiming
from anything_plays.gba_emulator import CoreSession


class NativeLoopTimingTests(unittest.TestCase):
    def test_native_run_exceeds_20fps_limit_while_readback_remains_small(self):
        t = GameCubeNativeTiming()
        t.record_native_run(0.160)
        t.record_native_run(0.120)
        t.record_native_run(0.010)
        t.record_wait(0.002)
        sample = t.snapshot(gpu_readback_seconds=0.009)
        self.assertEqual(sample["native_run_calls"], 3)
        self.assertEqual(sample["native_run_over_50ms"], 2)
        self.assertEqual(sample["native_run_over_100ms"], 2)
        self.assertEqual(sample["native_run_over_16ms"], 2)
        self.assertAlmostEqual(sample["native_run_mean_ms"], 96.667, places=2)
        self.assertAlmostEqual(sample["native_run_non_readback_mean_ms"], 93.667, places=2)
        self.assertAlmostEqual(sample["gpu_readback_share_of_native_run"], 0.031, places=3)
        self.assertEqual(sample["scheduler_wait_calls"], 1)

    def test_bad_clock_data_never_produces_nan_or_unsafe_counter(self):
        t = GameCubeNativeTiming()
        for value in (float("nan"), float("inf"), float("-inf"), -1, None, "1"):
            t.record_native_run(value)
            t.record_wait(value)
        self.assertEqual(t.native_run_calls, 0)
        self.assertEqual(t.scheduler_wait_calls, 0)
        snap = t.snapshot(gpu_readback_seconds=float("nan"))
        self.assertEqual(snap["native_run_mean_ms"], 0.0)
        self.assertTrue(all(math.isfinite(v) for v in snap.values()))

    def test_gpu_readback_must_not_exceed_native_run_time_in_report(self):
        t = GameCubeNativeTiming()
        t.record_native_run(0.050)
        snap = t.snapshot(gpu_readback_seconds=10.0)
        self.assertEqual(snap["gpu_readback_share_of_native_run"], 1.0)
        self.assertEqual(snap["native_run_non_readback_mean_ms"], 0.0)

    def test_counters_do_not_hold_frames_timestamps_or_game_data(self):
        t = GameCubeNativeTiming()
        for _ in range(10000):
            t.record_native_run(0.006)
        self.assertEqual(t.native_run_calls, 10000)
        self.assertLessEqual(len(vars(t)), 8)
        self.assertEqual(t.snapshot()["native_run_over_50ms"], 0)

    def test_actual_core_loop_records_native_calls_without_mocking_frame_counts(self):
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "dolphin_libretro.so"
            core.write_bytes(b"test-core-bytes")
            session = object.__new__(CoreSession)
            session.system = "gamecube"
            session.rom = Path(td) / "original-homebrew.dol"
            session.rom.write_bytes(b"original test")
            session.core_path = str(core)
            session._load_game = Mock()
            session.persist_game_progress = Mock()
            session.audio = Mock()
            session.audio.output_error = None
            session.audio.start = Mock()
            session.audio.close = Mock()
            session.save_ram = None
            session.enable_state_resume = False
            session.native_run_timing = GameCubeNativeTiming()
            inputs = Mock()
            inputs.system = "gamecube"
            stop = threading.Event()
            emu = SimpleNamespace(
                inputs=inputs, stop_event=stop, armed=True,
                running=False, launching=True, audio_sink=None,
                audio_warning=None, save_warning=None,
            )
            session.emulator = emu
            fake = MagicMock()
            fake.av_info = Mock()
            fake.memory_data = Mock(return_value=None)
            fake.memory_size = Mock(return_value=0)
            calls = []
            def native_step():
                calls.append(True)
                if len(calls) == 4:
                    stop.set()
            fake.run.side_effect = native_step
            with patch("anything_plays.gba_emulator.NativeCore", return_value=fake), \
                 patch("anything_plays.gba_emulator.SaveRAM"):
                session.run()
            self.assertEqual(len(calls), 4)
            self.assertEqual(session.native_run_timing.native_run_calls, 4)
            self.assertEqual(fake.close.call_count, 1)
            self.assertEqual(emu.audio_sink, None)
            self.assertTrue(emu.running)
            self.assertGreaterEqual(session.native_run_timing.native_run_total_seconds, 0)

    def test_research_metrics_are_allowlisted_not_raw_logs(self):
        from tools.v32_extended_native_runtime import safe_evidence
        raw = {
            "passed": True,
            "fixture_sha256": "b"*64,
            "details": {
                "passed": True,
                "backend": "production GameCubeHardwareSession + platform GPU host",
                "uses_external_dolphin": False,
                "passes_in_app_frame_queue": True,
                "gamecube_rgb_callback_frames": 120,
                "sampled_nonblank_frames": 60,
                "distinct_rgb_frame_hashes": 10,
                "native_controller_polls": 2000,
                "native_pcm_frame_samples": 5000,
                "native_run_calls": 120,
                "native_run_mean_ms": 160.0,
                "native_run_non_readback_mean_ms": 157.0,
                "gpu_readback_share_of_native_run": 0.01875,
                "console_tail": "/home/user/private/game.dol",
            },
        }
        record = safe_evidence("gamecube", raw, 0, False)
        self.assertTrue(record["native_probe_verified"])
        self.assertEqual(record["native_run_calls"], 120)
        self.assertEqual(record["native_run_mean_ms"], 160.0)
        self.assertEqual(record["gpu_readback_share_of_native_run"], 0.01875)
        self.assertNotIn("console_tail", record)
        self.assertNotIn("game.dol", str(record))


if __name__ == "__main__":
    unittest.main()
