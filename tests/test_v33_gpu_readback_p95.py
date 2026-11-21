"""3.3 GameCube GPU readback P95: bounded instrumentation, not physical FPS."""
import json
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from anything_plays.gamecube_preview import (
    ReadbackTimingHistogram, PreviewCadenceTracker, DEFAULT_PREVIEW_MODE,
)
from anything_plays.gamecube_native_timing import GameCubeNativeTiming
from anything_plays.gamecube_gpu import GameCubeHardwareSession
from anything_plays.libretro_video import RETRO_HW_FRAME_BUFFER_VALID
from anything_plays.ui_setup_diagnostics import _gamecube_performance_summary_lines


class GPUReadbackP95Tests(unittest.TestCase):
    def test_p95_rejects_one_extreme_outlier_but_detects_repeated_stalls(self):
        hist = ReadbackTimingHistogram()
        self.assertEqual(hist.snapshot()["gpu_readback_p95_bucket_code"], -1)
        for _ in range(19):
            hist.record(0.004)
        hist.record(0.250)
        self.assertEqual(hist.snapshot()["gpu_readback_p95_bucket_code"], 1)
        hist.record(0.250)
        self.assertEqual(hist.snapshot()["gpu_readback_p95_bucket_code"], 7)
        self.assertEqual(hist.snapshot()["gpu_readback_over_33ms"], 2)
        self.assertEqual(sum(hist.buckets), hist.samples)

    def test_stress_clock_corruption_and_bounded_memory(self):
        hist = ReadbackTimingHistogram()
        for bad in (None, "private /home/user", True, [], {},
                    float("nan"), float("inf"), -1.0, 3601, 10**1000):
            self.assertFalse(hist.record(bad))
        self.assertEqual(hist.samples, 0)
        for _ in range(10000):
            hist.record(0.017)
        self.assertEqual(sum(hist.buckets), 10000)
        self.assertEqual(hist.snapshot()["gpu_readback_p95_bucket_code"], 4)
        self.assertEqual(hist.snapshot()["gpu_readback_over_16ms"], 10000)
        self.assertEqual(hist.snapshot()["gpu_readback_over_33ms"], 0)
        self.assertLessEqual(len(hist.buckets), 9)
        self.assertLessEqual(len(vars(hist)), 4)
        self.assertNotIn("buckets", hist.snapshot())

    def test_actual_gpu_video_callback_reports_only_timed_copies(self):
        import numpy as np

        sess = object.__new__(GameCubeHardwareSession)
        frame = np.full((8, 8, 3), 40, dtype=np.uint8)
        sess.host = Mock(read_frame=Mock(return_value=frame))
        sess.emulator = SimpleNamespace(
            frame=None, frame_serial=0, lock=threading.Lock(),
            gamecube_preview_mode=DEFAULT_PREVIEW_MODE,
            stop_event=threading.Event(),
        )
        sess.native_run_timing = GameCubeNativeTiming()
        sess.native_run_timing.record_native_run(0.080)
        sess.native_run_timing.record_native_run(0.080)
        sess.audio = Mock(delivery_snapshot=Mock(return_value={
            "audio_output_device_underflow_callbacks": 0,
            "audio_output_underrun_frames": 0,
            "audio_queue_dropped_frames": 0,
        }))
        sess.gpu_readback_seconds = 0.0
        sess.gpu_readback_max_seconds = 0.0
        sess.gpu_readback_calls = 0
        sess.gpu_readback_timing_samples = 0
        sess.preview_clock_failures = 0
        sess.hardware_frames = 0
        sess.preview_readback_skips = 0
        sess._last_preview_capture = None
        sess._last_preview_publication = None
        sess._last_preview_readback_duration = 0.0
        sess.raw_video_callbacks = 0
        sess.null_video_callbacks = 0
        sess.opengl_error = None
        sess._preview_cadence = PreviewCadenceTracker()
        sess._readback_histogram = ReadbackTimingHistogram()
        for (n1, n2, p1, p2) in (
            (0.000, 0.004, 1.000, 1.004),
            (0.050, 0.090, 1.050, 1.090),
        ):
            with (
                patch("anything_plays.gamecube_gpu.time.monotonic",
                      side_effect=(n1, n2)),
                patch("anything_plays.gamecube_gpu.time.perf_counter",
                      side_effect=(p1, p2)),
            ):
                sess.video(RETRO_HW_FRAME_BUFFER_VALID, 8, 8, 32)
        report = sess.performance_snapshot()
        metrics = report["metrics"]
        self.assertEqual(metrics["gpu_readback_calls"], 2)
        self.assertEqual(metrics["gpu_readback_timing_samples"], 2)
        self.assertEqual(metrics["gpu_readback_p95_bucket_code"], 5)
        self.assertEqual(metrics["gpu_readback_over_16ms"], 1)
        self.assertEqual(metrics["gpu_readback_over_33ms"], 1)
        self.assertEqual(sess.emulator.frame_serial, 2)
        self.assertFalse(sess.emulator.stop_event.is_set())
        ui = _gamecube_performance_summary_lines(report)
        self.assertTrue(any("readback P95" in line and "33–50 ms" in line
                            for line in ui))
        encoded = json.dumps(report)
        self.assertNotIn("/home/", encoded)
        self.assertNotIn("private", encoded)
        self.assertNotIn("buckets", encoded)


if __name__ == "__main__":
    unittest.main()
