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

    def test_scheduler_missed_deadlines_are_aggregate_and_do_not_change_pacing(self):
        t = GameCubeNativeTiming()
        t.record_lateness(0.004)  # Ignore minor timer jitter
        t.record_lateness(0.012)
        t.record_lateness(0.320, resynchronized=True)
        snap = t.snapshot()
        self.assertEqual(snap["scheduler_late_frames"], 2)
        self.assertAlmostEqual(snap["scheduler_late_total_seconds"], 0.332)
        self.assertEqual(snap["scheduler_late_max_ms"], 320.0)
        self.assertEqual(snap["scheduler_resyncs"], 1)
        self.assertEqual(snap["native_run_calls"], 0)
        self.assertEqual(snap["scheduler_wait_calls"], 0)

    def test_bad_clock_data_never_produces_nan_or_unsafe_counter(self):
        t = GameCubeNativeTiming()
        for value in (float("nan"), float("inf"), float("-inf"), -1, None, "1"):
            t.record_native_run(value)
            t.record_wait(value)
            t.record_lateness(value, resynchronized=True)
        self.assertEqual(t.scheduler_late_frames, 0)
        self.assertEqual(t.scheduler_resyncs, 0)
        self.assertEqual(t.native_run_calls, 0)
        self.assertEqual(t.scheduler_wait_calls, 0)
        snap = t.snapshot(gpu_readback_seconds=float("nan"))
        self.assertEqual(snap["native_run_mean_ms"], 0.0)
        self.assertTrue(all(math.isfinite(v) for v in snap.values()))

    def test_gpu_readback_report_rejects_malformed_clock_without_failing(self):
        timing = GameCubeNativeTiming()
        timing.record_native_run(0.03)
        for invalid in (None, "device /home/private", 10**1000):
            with self.subTest(invalid_type=type(invalid).__name__):
                metric = timing.snapshot(gpu_readback_seconds=invalid)
                self.assertEqual(metric["gpu_readback_share_of_native_run"], 0)
                self.assertEqual(metric["native_run_non_readback_mean_ms"], 30)

    def test_gpu_readback_must_not_exceed_native_run_time_in_report(self):
        t = GameCubeNativeTiming()
        t.record_native_run(0.050)
        snap = t.snapshot(gpu_readback_seconds=10.0)
        self.assertEqual(snap["gpu_readback_share_of_native_run"], 1.0)
        self.assertEqual(snap["native_run_non_readback_mean_ms"], 0.0)

    def test_p95_frame_time_histogram_is_bounded_and_not_average(self):
        t = GameCubeNativeTiming()
        self.assertEqual(t.snapshot()["native_run_p95_bucket_code"], -1)
        # A single 900ms stall does not distort the 95th percentile of
        # twenty native calls; it still affects max and mean as expected.
        for _ in range(19):
            t.record_native_run(0.010)
        t.record_native_run(0.900)
        metrics = t.snapshot()
        self.assertEqual(metrics["native_run_calls"], 20)
        self.assertEqual(metrics["native_run_p95_bucket_code"], 1)  # 8–16ms
        self.assertEqual(metrics["native_run_max_ms"], 900)
        self.assertEqual(sum(t.native_run_histogram), 20)
        # Adding a second >500ms frame moves rank 19 into the slow bucket.
        t.record_native_run(0.900)
        self.assertEqual(t.snapshot()["native_run_p95_bucket_code"], 8)
        self.assertEqual(len(t.native_run_histogram), 9)
        self.assertNotIn("native_run_histogram", metrics)

    def test_nonfinite_or_giant_native_timing_never_crashes_gameplay(self):
        t = GameCubeNativeTiming()
        for bad in (None, "private device", True, float("nan"),
                    float("inf"), -0.1, 10**1000):
            t.record_native_run(bad)
        self.assertEqual(t.native_run_calls, 0)
        self.assertEqual(t.snapshot()["native_run_p95_bucket_code"], -1)
        t.record_native_run(0.2)
        self.assertEqual(t.snapshot()["native_run_p95_bucket_code"], 6)

    def test_native_scheduler_timing_faults_never_cross_core_boundary(self):
        """Optional clock instrumentation must not kill the native worker."""
        t = GameCubeNativeTiming()
        for bad in (
            10**1000, float("inf"), float("-inf"), float("nan"),
            None, "private /home/user/game.iso", {}, [], True,
            -1, 3601, 1e308,
        ):
            with self.subTest(value_type=type(bad).__name__):
                t.record_native_run(bad)
                t.record_wait(bad)
                t.record_lateness(bad, resynchronized=True)
        self.assertEqual(t.native_run_calls, 0)
        self.assertEqual(t.scheduler_wait_calls, 0)
        self.assertEqual(t.scheduler_late_frames, 0)
        self.assertEqual(t.scheduler_resyncs, 0)

        t.reported_core_fps = 10**1000
        self.assertEqual(t.snapshot()["native_reported_core_fps"], 0)
        t.reported_core_fps = float("nan")
        self.assertEqual(t.snapshot()["native_reported_core_fps"], 0)
        t.reported_core_fps = 59.94
        t.record_native_run(0.017)
        t.record_wait(0.004)
        t.record_lateness(0.015, resynchronized=True)
        recovered = t.snapshot()
        self.assertEqual(recovered["native_run_calls"], 1)
        self.assertEqual(recovered["scheduler_wait_calls"], 1)
        self.assertEqual(recovered["scheduler_late_frames"], 1)
        self.assertEqual(recovered["scheduler_resyncs"], 1)
        self.assertEqual(recovered["native_reported_core_fps"], 59.94)
        self.assertEqual(recovered["native_run_p95_bucket_code"], 2)
        self.assertTrue(all(math.isfinite(v) for v in recovered.values()))

    def test_long_suspended_clock_is_not_a_native_frame_duration(self):
        t = GameCubeNativeTiming()
        t.record_native_run(0.02)
        t.record_native_run(3700.0)
        t.record_wait(3700.0)
        t.record_lateness(3700.0, resynchronized=True)
        s = t.snapshot()
        self.assertEqual(s["native_run_calls"], 1)
        self.assertEqual(s["scheduler_wait_calls"], 0)
        self.assertEqual(s["scheduler_resyncs"], 0)
        self.assertEqual(s["native_run_max_ms"], 20)
        self.assertEqual(s["native_run_p95_bucket_code"], 2)

    def test_counters_do_not_hold_frames_timestamps_or_game_data(self):
        t = GameCubeNativeTiming()
        for _ in range(10000):
            t.record_native_run(0.006)
        self.assertEqual(t.native_run_calls, 10000)
        self.assertLessEqual(len(vars(t)), 14)
        self.assertEqual(t.snapshot()["native_run_over_50ms"], 0)

    def test_actual_core_loop_records_native_calls_without_mocking_frame_counts(self):
        # The full source suite installs NumPy and exercises the real loop.
        # The earliest native-installer preflight intentionally runs without
        # scientific/GUI dependencies; skip ONLY this full-module integration
        # case there, while all standard-library profiler tests still run.
        try:
            from anything_plays.gba_emulator import CoreSession
        except ModuleNotFoundError as exc:
            if exc.name in ("numpy", "PIL", "cv2", "sounddevice", "pygame"):
                self.skipTest("Full emulator dependencies installed in later CI stage")
            raise
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
            self.assertGreater(
                session.native_run_timing.reported_core_fps, 20
            )
            self.assertEqual(fake.close.call_count, 1)
            self.assertEqual(emu.audio_sink, None)
            self.assertTrue(emu.running)
            self.assertGreaterEqual(session.native_run_timing.native_run_total_seconds, 0)

    def test_real_core_loop_records_behind_schedule_and_resyncs(self):
        # Synthetic, deterministic slow native core. The real CoreSession
        # scheduling loop must count missed deadlines without dropping any
        # retro_run() calls or depending on a physical GPU/audio device.
        try:
            from anything_plays.gba_emulator import CoreSession
        except ModuleNotFoundError as exc:
            if exc.name in ("numpy", "PIL", "cv2", "sounddevice", "pygame"):
                self.skipTest("Full emulator dependencies installed in later CI stage")
            raise
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "dolphin_libretro.so"
            core.write_bytes(b"original-synthetic-core")
            session = object.__new__(CoreSession)
            session.system = "gamecube"
            session.rom = Path(td) / "test-homebrew.dol"
            session.rom.write_bytes(b"original test fixture")
            session.core_path = str(core)
            session._load_game = Mock()
            session.persist_game_progress = Mock()
            session.audio = Mock(output_error=None)
            session.save_ram = None
            session.enable_state_resume = False
            session.native_run_timing = GameCubeNativeTiming()
            stop = threading.Event()
            emu = SimpleNamespace(
                inputs=Mock(system="gamecube"), stop_event=stop,
                armed=False, running=False, launching=True,
                audio_sink=None, audio_warning=None, save_warning=None,
            )
            session.emulator = emu
            fake = MagicMock()
            fake.av_info = Mock()
            fake.memory_data = Mock(return_value=None)
            fake.memory_size = Mock(return_value=0)
            virtual_clock = [0.0]
            core_calls = []

            def slow_native_step():
                core_calls.append(True)
                virtual_clock[0] += 0.35  # >250ms catch-up reset threshold
                if len(core_calls) == 3:
                    stop.set()

            fake.run.side_effect = slow_native_step
            with (
                patch("anything_plays.gba_emulator.NativeCore", return_value=fake),
                patch("anything_plays.gba_emulator.SaveRAM"),
                patch("anything_plays.gba_emulator.time.monotonic",
                      side_effect=lambda: virtual_clock[0]),
            ):
                session.run()
            snapshot = session.native_run_timing.snapshot()
            self.assertEqual(len(core_calls), 3)
            self.assertEqual(snapshot["native_run_calls"], 3)
            self.assertEqual(snapshot["scheduler_late_frames"], 3)
            self.assertEqual(snapshot["scheduler_resyncs"], 3)
            self.assertGreater(snapshot["scheduler_late_max_ms"], 250)
            self.assertEqual(snapshot["scheduler_wait_calls"], 0)
            fake.close.assert_called_once()

    def test_live_gamecube_aggregate_contains_no_native_session_or_private_names(self):
        from anything_plays.gamecube_gpu import GameCubeHardwareSession
        session = object.__new__(GameCubeHardwareSession)
        timing = GameCubeNativeTiming()
        timing.record_native_run(0.040)
        timing.record_native_run(0.060)
        timing.record_lateness(0.09, resynchronized=False)
        session.native_run_timing = timing
        session.gpu_readback_seconds = 0.008
        session.gpu_readback_max_seconds = 0.005
        session.gpu_readback_calls = 2
        session.hardware_frames = 2
        session.preview_readback_skips = 4
        session.audio = Mock(
            delivery_snapshot=Mock(return_value={
                "audio_output_callback_calls": 15,
                "audio_output_requested_frames": 1280,
                "audio_output_underrun_frames": 16,
                "audio_output_device_underflow_callbacks": 1,
                "audio_queue_dropped_frames": 64,
            }),
            device_name="Private output /home/user/speakers"
        )
        session.rom = "/home/user/ROMs/private.game.iso"
        session.host = Mock(driver_info="NVIDIA id XYZSECRET")
        performance = session.performance_snapshot()
        self.assertEqual(performance["format"], "anything-plays-gamecube-performance")
        self.assertEqual(performance["metrics"]["native_run_calls"], 2)
        self.assertEqual(performance["metrics"]["gpu_readback_calls"], 2)
        self.assertEqual(performance["metrics"]["gamecube_hardware_frames"], 2)
        self.assertEqual(performance["metrics"]["scheduler_late_frames"], 1)
        self.assertAlmostEqual(
            performance["metrics"]["gpu_readback_share_of_native_run"], .08
        )
        self.assertEqual(
            performance["metrics"]["audio_output_device_underflow_callbacks"], 1
        )
        import json
        encoded = json.dumps(performance)
        for private in ("private.game.iso", "/home/", "XYZSECRET", "device_name",
                        "driver_info", "speaker", "rom", "host"):
            self.assertNotIn(private, encoded.lower() if private == "rom" else encoded)

    def test_emulator_exposes_live_and_final_gamecube_metrics_without_session_retention(self):
        from anything_plays.gba_emulator import Emulator
        emu = Emulator()
        emu.system = "gamecube"
        emu.rom = "/home/user/private-game.iso"
        emu.core_path = "/home/user/private-dolphin.so"
        expected = {
            "format": "anything-plays-gamecube-performance",
            "version": 1,
            "scope": "aggregate_native_av_not_physical_hardware_certification",
            "metrics": {"native_run_calls": 12},
        }
        fake = Mock(performance_snapshot=Mock(return_value=expected))
        def run_game():
            self.assertIs(emu._gamecube_session, fake)
            self.assertEqual(emu.gamecube_performance_snapshot(), expected)
        fake.run.side_effect = run_game
        with patch("anything_plays.gamecube_gpu.GameCubeHardwareSession",
                   return_value=fake):
            emu._run()
        self.assertIsNone(emu._gamecube_session)
        self.assertIs(emu.gamecube_performance_snapshot(), expected)
        fake.performance_snapshot.assert_called()
        emu.system = "gba"
        self.assertIsNone(emu.gamecube_performance_snapshot())

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
                "audio_output_callback_calls": 22,
                "audio_output_requested_frames": 22000,
                "audio_output_underrun_frames": 1024,
                "audio_queue_dropped_frames": 512,
                "audio_output_device_underflow_callbacks": 3,
                "scheduler_late_frames": 12,
                "scheduler_late_total_seconds": 1.6,
                "scheduler_late_max_ms": 320.0,
                "scheduler_resyncs": 2,
                "native_run_calls": 120,
                "native_reported_core_fps": 59.7,
                "native_run_loop_fps": 49.0,
                "gamecube_preview_capture_fps": 5.8,
                "raw_libretro_video_callbacks": 150,
                "null_libretro_video_callbacks": 3,
                "preview_readback_skips": 1,
                "native_run_mean_ms": 160.0,
                "native_run_non_readback_mean_ms": 157.0,
                "gpu_readback_share_of_native_run": 0.01875,
                "console_tail": "/home/user/private/game.dol",
            },
        }
        record = safe_evidence("gamecube", raw, 0, False)
        self.assertTrue(record["native_probe_verified"])
        self.assertEqual(record["native_run_calls"], 120)
        self.assertEqual(record["audio_output_callback_calls"], 22)
        self.assertEqual(record["audio_output_requested_frames"], 22000)
        self.assertEqual(record["audio_output_underrun_frames"], 1024)
        self.assertEqual(record["audio_queue_dropped_frames"], 512)
        self.assertEqual(record["audio_output_device_underflow_callbacks"], 3)
        self.assertEqual(record["scheduler_late_frames"], 12)
        self.assertEqual(record["scheduler_late_total_seconds"], 1.6)
        self.assertEqual(record["scheduler_late_max_ms"], 320.0)
        self.assertEqual(record["scheduler_resyncs"], 2)
        self.assertFalse(record["physical_speakers_tested"])
        self.assertEqual(record["native_run_loop_fps"], 49.0)
        self.assertEqual(record["gamecube_preview_capture_fps"], 5.8)
        self.assertEqual(record["raw_libretro_video_callbacks"], 150)
        self.assertEqual(record["null_libretro_video_callbacks"], 3)
        self.assertEqual(record["native_run_mean_ms"], 160.0)
        self.assertEqual(record["gpu_readback_share_of_native_run"], 0.01875)
        self.assertNotIn("console_tail", record)
        self.assertNotIn("game.dol", str(record))


if __name__ == "__main__":
    unittest.main()
