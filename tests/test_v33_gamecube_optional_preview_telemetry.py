"""GPU preview timing/report failures must not interrupt native GameCube video.

Uses a fake host, RGB pixels, and no Dolphin executable, ROM, controller,
webcam, speaker or physical GPU. Only safe aggregate report data is asserted.
"""
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from anything_plays.gamecube_gpu import GameCubeHardwareSession
from anything_plays.gamecube_native_timing import GameCubeNativeTiming
from anything_plays.gamecube_preview import (
    PreviewCadenceTracker, ReadbackTimingHistogram,
)
from anything_plays.libretro_video import RETRO_HW_FRAME_BUFFER_VALID
from anything_plays.libretro_audio import AudioSink
from anything_plays.ui_setup_diagnostics import _gamecube_performance_summary_lines


def session_with_fake_gpu():
    s = object.__new__(GameCubeHardwareSession)
    rgb = np.full((8, 8, 3), 42, dtype=np.uint8)
    s.host = Mock(read_frame=Mock(return_value=rgb))
    s.emulator = SimpleNamespace(
        frame=None, frame_serial=0, lock=threading.Lock(),
        gamecube_preview_mode="Balanced (30 FPS)",
        stop_event=threading.Event(),
    )
    s.raw_video_callbacks = 0
    s.null_video_callbacks = 0
    s.hardware_frames = 0
    s.preview_readback_skips = 0
    s.gpu_readback_calls = 0
    s.gpu_readback_seconds = 0.0
    s.gpu_readback_max_seconds = 0.0
    s.gpu_readback_timing_samples = 0
    s.preview_clock_failures = 0
    s._last_preview_capture = None
    s._last_preview_publication = None
    s._last_preview_readback_duration = 0.0
    s._readback_histogram = ReadbackTimingHistogram()
    s._preview_cadence = PreviewCadenceTracker()
    s.native_run_timing = GameCubeNativeTiming()
    s.audio = Mock()
    s.audio.delivery_snapshot.return_value = {
        "audio_output_callback_calls": 0,
        "audio_output_requested_frames": 0,
        "audio_output_underrun_frames": 0,
        "audio_output_device_underflow_callbacks": 0,
        "audio_queue_dropped_frames": 0,
    }
    s.opengl_error = None
    return s, rgb


def video_at(s, begin, end):
    with (
        patch("anything_plays.gamecube_gpu.time.monotonic",
              side_effect=[begin, end]),
        patch("anything_plays.gamecube_gpu.time.perf_counter",
              side_effect=[100.0, 100.004]),
    ):
        s.video(RETRO_HW_FRAME_BUFFER_VALID, 8, 8, 32)


class OptionalPreviewTelemetryIsolationTests(unittest.TestCase):
    def assert_frame_alive(self, s, rgb):
        self.assertIs(s.emulator.frame, rgb)
        self.assertEqual(s.emulator.frame_serial, 1)
        self.assertEqual(s.hardware_frames, 1)
        self.assertEqual(s.host.read_frame.call_count, 1)
        self.assertIsNone(s.opengl_error)
        self.assertFalse(s.emulator.stop_event.is_set())

    def test_failing_mode_cadence_reset_cannot_drop_native_video(self):
        s, rgb = session_with_fake_gpu()
        s._preview_cadence.reset_for = Mock(
            side_effect=OSError("PRIVATE /Users/owner/gpu-adapter")
        )
        video_at(s, 10.0, 10.004)
        self.assert_frame_alive(s, rgb)
        self.assertIsNone(s._preview_cadence)
        m = s.performance_snapshot()["metrics"]
        self.assertEqual(m["gamecube_preview_target_fps"], 0)
        self.assertEqual(m["gpu_readback_calls"], 1)
        self.assertNotIn("PRIVATE", str(m))

    def test_failing_histogram_record_does_not_drop_valid_pixels(self):
        s, rgb = session_with_fake_gpu()
        s._readback_histogram.record = Mock(
            side_effect=RuntimeError("PRIVATE /home/operator/serial")
        )
        video_at(s, 10.0, 10.004)
        self.assert_frame_alive(s, rgb)
        self.assertIsNone(s._readback_histogram)
        m = s.performance_snapshot()["metrics"]
        self.assertEqual(m["gpu_readback_p95_bucket_code"], -1)
        self.assertEqual(m["gpu_readback_calls"], 1)
        self.assertNotIn("PRIVATE", str(m))

    def test_failed_publication_collector_preserves_image_and_recovers(self):
        s, rgb = session_with_fake_gpu()
        s._preview_cadence.record_published = Mock(
            side_effect=OSError("PRIVATE native timing collector")
        )
        video_at(s, 10.0, 10.004)
        self.assert_frame_alive(s, rgb)
        self.assertIsNone(s._preview_cadence)
        video_at(s, 10.040, 10.044)
        self.assertEqual(s.hardware_frames, 2)
        self.assertEqual(s.emulator.frame_serial, 2)
        self.assertFalse(s.emulator.stop_event.is_set())

    def test_snapshot_failures_and_private_fields_fallback_to_safe_metrics(self):
        s, _ = session_with_fake_gpu()
        s._readback_histogram.snapshot = Mock(
            side_effect=RuntimeError("PRIVATE /Users/owner/GameCube")
        )
        s._preview_cadence.snapshot = Mock(
            return_value={
                "gamecube_preview_target_fps": 30,
                "gamecube_preview_observed_capture_fps": 1.0,
                "gamecube_preview_cadence_intervals": 2,
                "gamecube_preview_max_interval_ms": 500.0,
                "PRIVATE /home/device": "secret",
            }
        )
        m = s.performance_snapshot()["metrics"]
        self.assertEqual(m["gpu_readback_p95_bucket_code"], -1)
        self.assertEqual(m["gamecube_preview_target_fps"], 30)
        self.assertEqual(m["gamecube_preview_cadence_intervals"], 2)
        self.assertNotIn("PRIVATE", str(m))
        s._preview_cadence.snapshot = Mock(
            side_effect=OSError("PRIVATE /dev/video0")
        )
        m = s.performance_snapshot()["metrics"]
        self.assertEqual(m["gamecube_preview_target_fps"], 0)
        self.assertNotIn("PRIVATE", str(m))

    def test_malformed_histogram_snapshot_cannot_inject_private_report_data(self):
        s, _ = session_with_fake_gpu()
        s._readback_histogram.snapshot = Mock(return_value={
            "gpu_readback_p95_bucket_code": "/Users/private",
            "gpu_readback_over_16ms": 1,
            "gpu_readback_over_33ms": 1,
        })
        m = s.performance_snapshot()["metrics"]
        self.assertEqual(m["gpu_readback_p95_bucket_code"], -1)
        self.assertNotIn("private", str(m))


    def test_failed_audio_delivery_cannot_invent_zero_underruns(self):
        s, _ = session_with_fake_gpu()
        s.audio.delivery_snapshot.side_effect = OSError(
            "PRIVATE /Users/someone/USB-serial"
        )
        report = s.performance_snapshot()
        m = report["metrics"]
        self.assertFalse(m["audio_delivery_measurements_available"])
        self.assertEqual(m["audio_output_device_underflow_callbacks"], 0)
        self.assertNotIn("PRIVATE", str(report))
        audio_line = _gamecube_performance_summary_lines(report)[-1]
        self.assertIn("measurements unavailable", audio_line)
        self.assertIn("speaker unverified", audio_line)
        self.assertNotIn("0 device underflow callbacks", audio_line)

    def test_audio_delivery_reports_only_known_nonnegative_integer_counters(self):
        s, _ = session_with_fake_gpu()
        baseline = s.audio.delivery_snapshot.return_value.copy()
        baseline["audio_output_callback_calls"] = 5
        baseline["audio_output_device_underflow_callbacks"] = 2
        baseline["PRIVATE /home/person/serial"] = "device-name"
        s.audio.delivery_snapshot.return_value = baseline
        report = s.performance_snapshot()
        m = report["metrics"]
        self.assertTrue(m["audio_delivery_measurements_available"])
        self.assertEqual(m["audio_output_callback_calls"], 5)
        self.assertEqual(m["audio_output_device_underflow_callbacks"], 2)
        self.assertNotIn("PRIVATE", str(report))
        self.assertIn("2 device underflow callbacks",
                      _gamecube_performance_summary_lines(report)[-1])

        baseline["audio_output_underrun_frames"] = "/private/ROMs/game.iso"
        self.assertFalse(
            s.performance_snapshot()["metrics"][
                "audio_delivery_measurements_available"
            ]
        )
        baseline["audio_output_underrun_frames"] = -10
        self.assertFalse(
            s.performance_snapshot()["metrics"][
                "audio_delivery_measurements_available"
            ]
        )

    def test_invalid_audio_snapshot_type_and_native_pcm_observer_failure(self):
        s, _ = session_with_fake_gpu()
        s.audio.delivery_snapshot.return_value = ["PRIVATE /home/operator"]
        self.assertFalse(
            s.performance_snapshot()["metrics"][
                "audio_delivery_measurements_available"
            ]
        )
        sink = AudioSink()
        sink.output_callback_calls = 7
        s.audio = sink
        with patch.object(sink, "native_pcm_snapshot",
                          side_effect=RuntimeError("PRIVATE /dev/audio")):
            report = s.performance_snapshot()
        m = report["metrics"]
        self.assertTrue(m["audio_delivery_measurements_available"])
        self.assertEqual(m["audio_output_callback_calls"], 7)
        self.assertNotIn("audio_core_pcm_frames", m)
        self.assertNotIn("PRIVATE", str(report))

    def test_broken_driver_status_properties_do_not_break_setup_report(self):
        counters = session_with_fake_gpu()[0].audio.delivery_snapshot.return_value
        class BrokenDriverStatus:
            def delivery_snapshot(self):
                return counters

            @property
            def output_active(self):
                raise OSError("PRIVATE /home/driver")

            @property
            def output_ever_started(self):
                raise OSError("PRIVATE USB serial")

        s, _ = session_with_fake_gpu()
        s.audio = BrokenDriverStatus()
        report = s.performance_snapshot()
        self.assertTrue(
            report["metrics"]["audio_delivery_measurements_available"]
        )
        self.assertNotIn("audio_stream_active", report["metrics"])
        self.assertNotIn("PRIVATE", str(report))
        self.assertIn("Audio:", _gamecube_performance_summary_lines(report)[-1])

if __name__ == "__main__":
    unittest.main()
