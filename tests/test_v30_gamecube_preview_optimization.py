"""GameCube display pacing must never modify native emulator execution.

These synthetic tests use the real GPU session's video callback and fake only
the OpenGL host/readback. No commercial game images or device required.
"""
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from anything_plays.gamecube_gpu import GameCubeHardwareSession
from anything_plays.gamecube_preview import (
    DEFAULT_PREVIEW_MODE, PREVIEW_FPS, PreviewCadenceTracker,
    preview_fps, should_capture,
)
from anything_plays.libretro_video import RETRO_HW_FRAME_BUFFER_VALID


class PreviewRatePolicyTests(unittest.TestCase):
    def test_balanced_preserves_every_native_frame_only_skips_cheap_preview(self):
        self.assertEqual(DEFAULT_PREVIEW_MODE, "Balanced (30 FPS)")
        self.assertEqual(preview_fps(DEFAULT_PREVIEW_MODE), 30)
        self.assertEqual(preview_fps("Performance (20 FPS)"), 20)
        self.assertEqual(preview_fps("Quality (60 FPS)"), 60)
        self.assertEqual(preview_fps("bad saved preference"), 30)
        for malformed in (None, [], {}, ["Performance (20 FPS)"], 42):
            with self.subTest(malformed=type(malformed).__name__):
                self.assertEqual(preview_fps(malformed), 30)
                self.assertTrue(should_capture(None, 10.0, malformed))
                self.assertFalse(should_capture(10.0, 10.001, malformed))
                tracker = PreviewCadenceTracker()
                tracker.reset_for(malformed)
                self.assertEqual(
                    tracker.snapshot()["gamecube_preview_target_fps"], 30
                )
        self.assertTrue(should_capture(None, 0.0, DEFAULT_PREVIEW_MODE))
        self.assertFalse(should_capture(0.0, 0.010, DEFAULT_PREVIEW_MODE))
        self.assertTrue(should_capture(0.0, 0.035, DEFAULT_PREVIEW_MODE))
        self.assertFalse(should_capture(0.0, 0.040, "Performance (20 FPS)"))
        self.assertTrue(should_capture(0.0, 0.040, "Quality (60 FPS)"))
        self.assertTrue(should_capture(100.0, 0.0, DEFAULT_PREVIEW_MODE))

    def test_preview_clock_corruption_never_raises_during_native_gpu_callback(self):
        """Only the optional GL-to-Tk snapshot is budgeted, not retro_run."""
        for mode in PREVIEW_FPS:
            for invalid in (
                float("nan"), float("inf"), float("-inf"), -1, True,
                10**1000, "private /Users/owner/device", [], {},
            ):
                with self.subTest(mode=mode, value_type=type(invalid).__name__):
                    self.assertFalse(should_capture(1.0, invalid, mode))
                    self.assertTrue(should_capture(invalid, 1.0, mode))
            self.assertTrue(should_capture(None, 1.0, mode))
            self.assertTrue(should_capture(1.0, 0.5, mode))
            self.assertFalse(should_capture(1.0, 1.005, mode))
            self.assertTrue(should_capture(1.0, 1.2, mode))

    def test_preview_cadence_measures_only_published_intervals_per_mode(self):
        tracker = PreviewCadenceTracker()
        self.assertEqual(tracker.snapshot()["gamecube_preview_target_fps"], 0)
        self.assertEqual(
            tracker.snapshot()["gamecube_preview_observed_capture_fps"], 0.0
        )
        for stamp in (0.004, 0.039, 0.074):
            tracker.record_published(stamp, "Balanced (30 FPS)")
        metrics = tracker.snapshot()
        self.assertEqual(metrics["gamecube_preview_target_fps"], 30)
        self.assertEqual(metrics["gamecube_preview_cadence_intervals"], 2)
        self.assertAlmostEqual(
            metrics["gamecube_preview_observed_capture_fps"], 28.57, places=2
        )
        self.assertEqual(metrics["gamecube_preview_max_interval_ms"], 35.0)
        # A new preview target must NOT mix previous capture cadence.
        tracker.record_published(0.125, "Performance (20 FPS)")
        changed = tracker.snapshot()
        self.assertEqual(changed["gamecube_preview_target_fps"], 20)
        self.assertEqual(changed["gamecube_preview_cadence_intervals"], 0)
        tracker.record_published(0.175, "Performance (20 FPS)")
        self.assertEqual(
            tracker.snapshot()["gamecube_preview_observed_capture_fps"], 20
        )
        # A restarted clock also starts a new segment.
        tracker.record_published(0.0, "Performance (20 FPS)")
        self.assertEqual(tracker.snapshot()["gamecube_preview_cadence_intervals"], 0)

    def test_preview_cadence_discards_suspend_gap_but_keeps_normal_stalls(self):
        tracker = PreviewCadenceTracker()
        tracker.record_published(10.0, DEFAULT_PREVIEW_MODE)
        tracker.record_published(10.05, DEFAULT_PREVIEW_MODE)
        self.assertEqual(tracker.snapshot()["gamecube_preview_cadence_intervals"], 1)
        # A normal gameplay stall is still a genuine measurement.
        tracker.record_published(12.05, DEFAULT_PREVIEW_MODE)
        self.assertEqual(tracker.snapshot()["gamecube_preview_cadence_intervals"], 2)
        # Sleep/resume must not pollute the new active-session FPS average.
        tracker.record_published(4000.0, DEFAULT_PREVIEW_MODE)
        after_resume = tracker.snapshot()
        self.assertEqual(after_resume["gamecube_preview_target_fps"], 30)
        self.assertEqual(after_resume["gamecube_preview_cadence_intervals"], 0)
        self.assertEqual(after_resume["gamecube_preview_observed_capture_fps"], 0.0)
        self.assertEqual(after_resume["gamecube_preview_max_interval_ms"], 0.0)
        self.assertEqual(tracker.published, 1)
        tracker.record_published(4000.05, DEFAULT_PREVIEW_MODE)
        self.assertEqual(tracker.snapshot()["gamecube_preview_cadence_intervals"], 1)
        self.assertAlmostEqual(
            tracker.snapshot()["gamecube_preview_observed_capture_fps"], 20.0
        )

    def test_preview_cadence_rejects_invalid_clock_without_retaining_history(self):
        tracker = PreviewCadenceTracker()
        for value in (None, float("nan"), float("inf"), -1, "private", 10**1000):
            tracker.record_published(value, "Balanced (30 FPS)")
        self.assertEqual(tracker.published, 0)
        for i in range(10000):
            tracker.record_published(i * 0.05, "Performance (20 FPS)")
        snap = tracker.snapshot()
        self.assertEqual(snap["gamecube_preview_cadence_intervals"], 9999)
        self.assertAlmostEqual(
            snap["gamecube_preview_observed_capture_fps"], 20, places=2
        )
        self.assertLessEqual(len(vars(tracker)), 6)
        self.assertNotIn("last_publication", snap)
        self.assertNotIn("frames", str(snap))

    def test_gpu_callback_counts_real_published_preview_cadence(self):
        session = object.__new__(GameCubeHardwareSession)
        frame = np.zeros((8, 8, 3), dtype=np.uint8)
        session.host = Mock(read_frame=Mock(return_value=frame))
        session.emulator = SimpleNamespace(
            frame=None, frame_serial=0, lock=threading.Lock(),
            gamecube_preview_mode=DEFAULT_PREVIEW_MODE,
            stop_event=threading.Event(),
        )
        session.hardware_frames = 0
        session.gpu_readback_seconds = 0.0
        session.gpu_readback_max_seconds = 0.0
        session.gpu_readback_calls = 0
        session.preview_readback_skips = 0
        session._last_preview_capture = None
        session.raw_video_callbacks = 0
        session.null_video_callbacks = 0
        session.opengl_error = None
        session._preview_cadence = PreviewCadenceTracker()
        for start, end in ((0.000, 0.004), (0.035, 0.039), (0.070, 0.074)):
            with patch("anything_plays.gamecube_gpu.time.monotonic",
                       side_effect=(start, end)):
                session.video(RETRO_HW_FRAME_BUFFER_VALID, 8, 8, 32)
        self.assertEqual(session.hardware_frames, 3)
        self.assertEqual(session.emulator.frame_serial, 3)
        stats = session._preview_cadence.snapshot()
        self.assertEqual(stats["gamecube_preview_target_fps"], 30)
        self.assertEqual(stats["gamecube_preview_cadence_intervals"], 2)
        self.assertAlmostEqual(
            stats["gamecube_preview_observed_capture_fps"], 28.57, places=2
        )
        self.assertEqual(session.host.read_frame.call_count, 3)

    def test_native_gpu_callback_survives_failed_optional_monotonic_clock(self):
        """A broken optional clock cannot escape through Dolphin ctypes."""
        session = object.__new__(GameCubeHardwareSession)
        rgb = np.full((8, 8, 3), 17, dtype=np.uint8)
        session.host = Mock(read_frame=Mock(return_value=rgb))
        session.emulator = SimpleNamespace(
            frame=None, frame_serial=0, lock=threading.Lock(),
            gamecube_preview_mode=DEFAULT_PREVIEW_MODE,
            stop_event=threading.Event(),
        )
        session.hardware_frames = 0
        session.gpu_readback_seconds = 0.0
        session.gpu_readback_max_seconds = 0.0
        session.gpu_readback_calls = 0
        session.preview_readback_skips = 0
        session._last_preview_capture = None
        session.raw_video_callbacks = 0
        session.null_video_callbacks = 0
        session.opengl_error = None
        session._preview_cadence = PreviewCadenceTracker()

        with patch("anything_plays.gamecube_gpu.time.monotonic",
                   side_effect=RuntimeError(
                       "clock unavailable /home/user/private-gpu"
                   )):
            session.video(RETRO_HW_FRAME_BUFFER_VALID, 8, 8, 32)
        self.assertEqual(session.raw_video_callbacks, 1)
        self.assertEqual(session.preview_readback_skips, 0)
        self.assertEqual(session.preview_clock_failures, 1)
        self.assertEqual(session.host.read_frame.call_count, 0)
        self.assertEqual(session.emulator.frame_serial, 0)
        self.assertFalse(session.emulator.stop_event.is_set())
        self.assertIsNone(session.opengl_error)
        with patch("anything_plays.gamecube_gpu.time.monotonic",
                   side_effect=(10.0, 10.004)):
            session.video(RETRO_HW_FRAME_BUFFER_VALID, 8, 8, 32)
        self.assertEqual(session.host.read_frame.call_count, 1)
        self.assertEqual(session.emulator.frame_serial, 1)
        self.assertEqual(session.hardware_frames, 1)
        self.assertEqual(session.gpu_readback_calls, 1)
        self.assertEqual(session.gpu_readback_timing_samples, 1)
        self.assertEqual(session.preview_clock_failures, 1)
        self.assertEqual(session._preview_cadence.published, 1)
        self.assertIs(session.emulator.frame, rgb)

    def test_native_gpu_frame_still_publishes_if_timing_clock_fails(self):
        """A failed perf_counter discards metrics, not valid GPU pixels."""
        session = object.__new__(GameCubeHardwareSession)
        rgb = np.zeros((8, 8, 3), dtype=np.uint8)
        session.host = Mock(read_frame=Mock(return_value=rgb))
        session.emulator = SimpleNamespace(
            frame=None, frame_serial=0, lock=threading.Lock(),
            gamecube_preview_mode=DEFAULT_PREVIEW_MODE,
            stop_event=threading.Event(),
        )
        session.hardware_frames = 0
        session.gpu_readback_seconds = 0.0
        session.gpu_readback_max_seconds = 0.0
        session.gpu_readback_calls = 0
        session.preview_readback_skips = 0
        session._last_preview_capture = None
        session.raw_video_callbacks = 0
        session.null_video_callbacks = 0
        session.opengl_error = None
        session._preview_cadence = PreviewCadenceTracker()

        with (
            patch("anything_plays.gamecube_gpu.time.monotonic",
                  side_effect=(20.0, 20.004)),
            patch("anything_plays.gamecube_gpu.time.perf_counter",
                  side_effect=OSError("private GPU serial /Users/owner")),
        ):
            session.video(RETRO_HW_FRAME_BUFFER_VALID, 8, 8, 32)
        self.assertEqual(session.emulator.frame_serial, 1)
        self.assertIs(session.emulator.frame, rgb)
        self.assertEqual(session.hardware_frames, 1)
        self.assertEqual(session.gpu_readback_calls, 1)
        self.assertEqual(session.gpu_readback_seconds, 0.0)
        self.assertEqual(session.gpu_readback_timing_samples, 0)
        self.assertEqual(session.preview_clock_failures, 1)
        self.assertEqual(session._preview_cadence.published, 1)
        self.assertIsNone(session.opengl_error)
        self.assertFalse(session.emulator.stop_event.is_set())

    def test_native_gpu_optional_clock_rejects_nonfinite_and_huge_values(self):
        session = object.__new__(GameCubeHardwareSession)
        for bad in (
            float("nan"), float("inf"), -1.0, 10**1000, True,
            "private GPU /home/owner/core", None,
        ):
            with self.subTest(value_type=type(bad).__name__):
                self.assertIsNone(session._optional_clock(lambda: bad))
        self.assertEqual(session._optional_clock(lambda: 10.0), 10.0)

    def test_preview_target_resets_immediately_when_new_mode_is_throttled(self):
        session = object.__new__(GameCubeHardwareSession)
        session.host = Mock(read_frame=Mock(
            return_value=np.zeros((8, 8, 3), dtype=np.uint8)
        ))
        session.emulator = SimpleNamespace(
            frame=None, frame_serial=0, lock=threading.Lock(),
            gamecube_preview_mode=DEFAULT_PREVIEW_MODE,
            stop_event=threading.Event(),
        )
        session.hardware_frames = 0
        session.gpu_readback_seconds = 0.0
        session.gpu_readback_max_seconds = 0.0
        session.gpu_readback_calls = 0
        session.preview_readback_skips = 0
        session._last_preview_capture = None
        session.raw_video_callbacks = 0
        session.null_video_callbacks = 0
        session.opengl_error = None
        session._preview_cadence = PreviewCadenceTracker()

        with patch("anything_plays.gamecube_gpu.time.monotonic",
                   side_effect=(0.0, 0.004)):
            session.video(RETRO_HW_FRAME_BUFFER_VALID, 8, 8, 32)
        self.assertEqual(session._preview_cadence.snapshot()[
            "gamecube_preview_target_fps"], 30)

        session.emulator.gamecube_preview_mode = "Performance (20 FPS)"
        # The last frame was 20ms ago: a 20 FPS capture must skip this
        # callback, but the setup checker must already show 20, not 30.
        with patch("anything_plays.gamecube_gpu.time.monotonic",
                   return_value=0.020):
            session.video(RETRO_HW_FRAME_BUFFER_VALID, 8, 8, 32)
        snap = session._preview_cadence.snapshot()
        self.assertEqual(snap["gamecube_preview_target_fps"], 20)
        self.assertEqual(snap["gamecube_preview_cadence_intervals"], 0)
        self.assertEqual(session.host.read_frame.call_count, 1)
        self.assertEqual(session.preview_readback_skips, 1)

        session.emulator.gamecube_preview_mode = "Quality (60 FPS)"
        with patch("anything_plays.gamecube_gpu.time.monotonic",
                   side_effect=(0.030, 0.034)):
            session.video(RETRO_HW_FRAME_BUFFER_VALID, 8, 8, 32)
        snap = session._preview_cadence.snapshot()
        self.assertEqual(snap["gamecube_preview_target_fps"], 60)
        self.assertEqual(snap["gamecube_preview_cadence_intervals"], 0)
        self.assertEqual(session.hardware_frames, 2)

    def test_actual_gamecube_gpu_callback_avoids_repeated_gl_readback(self):
        session = object.__new__(GameCubeHardwareSession)
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        session.host = Mock(read_frame=Mock(return_value=frame))
        session.emulator = SimpleNamespace(
            frame=None, frame_serial=0, lock=threading.Lock(),
            gamecube_preview_mode=DEFAULT_PREVIEW_MODE,
            stop_event=threading.Event(),
        )
        session.hardware_frames = 0
        session.gpu_readback_seconds = 0.0
        session.gpu_readback_max_seconds = 0.0
        session.gpu_readback_calls = 0
        session.preview_readback_skips = 0
        session._last_preview_capture = None
        session.raw_video_callbacks = 0
        session.null_video_callbacks = 0
        session.opengl_error = None

        for timestamp in (0.000, 0.008, 0.017, 0.035, 0.045):
            with patch("anything_plays.gamecube_gpu.time.monotonic",
                       return_value=timestamp):
                session.video(RETRO_HW_FRAME_BUFFER_VALID, 160, 120, 640)
        self.assertEqual(session.raw_video_callbacks, 5)
        self.assertEqual(session.gpu_readback_calls, 2)
        self.assertEqual(session.preview_readback_skips, 3)
        self.assertEqual(session.hardware_frames, 2)
        self.assertEqual(session.host.read_frame.call_count, 2)
        self.assertEqual(session.emulator.frame_serial, 2)
        self.assertIs(session.emulator.frame, frame)
        self.assertFalse(session.emulator.stop_event.is_set())
        self.assertIsNone(session.opengl_error)

        # Switch modes while game is running without touching core state.
        session.emulator.gamecube_preview_mode = "Quality (60 FPS)"
        with patch("anything_plays.gamecube_gpu.time.monotonic",
                   return_value=0.052):
            session.video(RETRO_HW_FRAME_BUFFER_VALID, 160, 120, 640)
        self.assertEqual(session.gpu_readback_calls, 3)
        self.assertEqual(session.emulator.frame_serial, 3)

        session.emulator.gamecube_preview_mode = "Performance (20 FPS)"
        with patch("anything_plays.gamecube_gpu.time.monotonic",
                   return_value=0.060):
            session.video(RETRO_HW_FRAME_BUFFER_VALID, 160, 120, 640)
        self.assertEqual(session.gpu_readback_calls, 3)
        self.assertEqual(session.preview_readback_skips, 4)
        self.assertEqual(session.raw_video_callbacks, 7)

    def test_gl_status_failure_stops_native_session_without_publishing_pixels(self):
        session = object.__new__(GameCubeHardwareSession)
        session.emulator = SimpleNamespace(
            frame=None, frame_serial=5, lock=threading.Lock(),
            stop_event=threading.Event(),
            gamecube_preview_mode=DEFAULT_PREVIEW_MODE,
        )
        session.host = Mock(read_frame=Mock(side_effect=RuntimeError(
            "GPU readback OpenGL error"
        )))
        session.opengl_error = None
        session.raw_video_callbacks = 0
        session.null_video_callbacks = 0
        session.preview_readback_skips = 0
        session._last_preview_capture = None
        session.hardware_frames = 0
        session.gpu_readback_seconds = 0.0
        session.gpu_readback_max_seconds = 0.0
        session.gpu_readback_calls = 0
        session.video(RETRO_HW_FRAME_BUFFER_VALID, 4, 4, 16)
        self.assertEqual(session.opengl_error, "GPU readback failed (RuntimeError)")
        self.assertTrue(session.emulator.stop_event.is_set())
        self.assertIsNone(session.emulator.frame)
        self.assertEqual(session.emulator.frame_serial, 5)
        self.assertEqual(session.hardware_frames, 0)
        session.video(RETRO_HW_FRAME_BUFFER_VALID, 4, 4, 16)
        session.host.read_frame.assert_called_once()

    def test_native_gpu_readback_errors_stop_without_publishing_stale_frames(self):
        for error in (
            OSError("USB GPU device reset"),
            RuntimeError("OpenGL context destroyed"),
            MemoryError("native allocation failed"),
            TypeError("invalid video surface"),
            AttributeError("invalid native GL wrapper object"),
            KeyError("missing native framebuffer lookup"),
        ):
            with self.subTest(error=type(error).__name__):
                session = object.__new__(GameCubeHardwareSession)
                stale_frame = np.zeros((4, 4, 3), dtype=np.uint8)
                session.host = Mock(read_frame=Mock(side_effect=error))
                session.emulator = SimpleNamespace(
                    frame=stale_frame, frame_serial=11,
                    lock=threading.Lock(), stop_event=threading.Event(),
                    gamecube_preview_mode=DEFAULT_PREVIEW_MODE,
                )
                session.opengl_error = None
                session.raw_video_callbacks = 0
                session.null_video_callbacks = 0
                session.preview_readback_skips = 0
                session._last_preview_capture = None
                session.hardware_frames = 0
                session.gpu_readback_seconds = 0.0
                session.gpu_readback_max_seconds = 0.0
                session.gpu_readback_calls = 0
                session.video(RETRO_HW_FRAME_BUFFER_VALID, 4, 4, 16)
                self.assertTrue(session.emulator.stop_event.is_set())
                self.assertIn(type(error).__name__, session.opengl_error)
                self.assertEqual(
                    session.opengl_error,
                    f"GPU readback failed ({type(error).__name__})",
                )
                self.assertIs(session.emulator.frame, stale_frame)
                self.assertEqual(session.emulator.frame_serial, 11)
                self.assertEqual(session.hardware_frames, 0)
                self.assertEqual(session.gpu_readback_calls, 0)
                # A second callback during native shutdown must not retry
                # a broken GL host or publish a frame after Stop.
                session.video(RETRO_HW_FRAME_BUFFER_VALID, 4, 4, 16)
                session.host.read_frame.assert_called_once()

    def test_unexpected_native_gl_exception_is_private_and_stops_core(self):
        """Custom GL wrapper failures must not propagate out of ctypes."""
        class PrivateDeviceSerialXYZ(Exception):
            pass

        session = object.__new__(GameCubeHardwareSession)
        old_pixels = np.full((4, 4, 3), 111, dtype=np.uint8)
        session.host = Mock(read_frame=Mock(side_effect=PrivateDeviceSerialXYZ(
            "driver failed /Users/owner/private/serial-123"
        )))
        session.emulator = SimpleNamespace(
            frame=old_pixels, frame_serial=7, lock=threading.Lock(),
            stop_event=threading.Event(),
            gamecube_preview_mode=DEFAULT_PREVIEW_MODE,
        )
        session.opengl_error = None
        session.raw_video_callbacks = 0
        session.null_video_callbacks = 0
        session.preview_readback_skips = 0
        session._last_preview_capture = None
        session.hardware_frames = 0
        session.gpu_readback_seconds = 0.0
        session.gpu_readback_max_seconds = 0.0
        session.gpu_readback_calls = 0

        session.video(RETRO_HW_FRAME_BUFFER_VALID, 4, 4, 16)
        self.assertEqual(
            session.opengl_error, "GPU readback failed (UnexpectedError)"
        )
        for forbidden in (
            "/Users/", "serial-123", "PrivateDeviceSerialXYZ", "driver failed"
        ):
            self.assertNotIn(forbidden, session.opengl_error)
        self.assertTrue(session.emulator.stop_event.is_set())
        self.assertIs(session.emulator.frame, old_pixels)
        self.assertEqual(session.emulator.frame_serial, 7)
        self.assertEqual(session.hardware_frames, 0)
        self.assertEqual(session.gpu_readback_calls, 0)
        session.video(RETRO_HW_FRAME_BUFFER_VALID, 4, 4, 16)
        session.host.read_frame.assert_called_once()

    def test_stop_during_readback_must_not_repaint_old_game(self):
        session = object.__new__(GameCubeHardwareSession)
        stale_frame = np.ones((4, 4, 3), dtype=np.uint8)
        session.emulator = SimpleNamespace(
            frame=stale_frame, frame_serial=9, lock=threading.Lock(),
            stop_event=threading.Event(),
            gamecube_preview_mode=DEFAULT_PREVIEW_MODE,
        )
        def slow_return(_width, _height):
            # Simulates Stop arriving while glReadPixels blocks.
            session.emulator.stop_event.set()
            return np.zeros((4, 4, 3), dtype=np.uint8)
        session.host = Mock(read_frame=Mock(side_effect=slow_return))
        session.opengl_error = None
        session.raw_video_callbacks = 0
        session.null_video_callbacks = 0
        session.preview_readback_skips = 0
        session._last_preview_capture = None
        session.hardware_frames = 0
        session.gpu_readback_seconds = 0.0
        session.gpu_readback_max_seconds = 0.0
        session.gpu_readback_calls = 0
        session.video(RETRO_HW_FRAME_BUFFER_VALID, 4, 4, 16)
        self.assertTrue(session.emulator.stop_event.is_set())
        self.assertIs(session.emulator.frame, stale_frame)
        self.assertEqual(session.emulator.frame_serial, 9)
        self.assertEqual(session.hardware_frames, 0)
        self.assertEqual(session.gpu_readback_calls, 1)
        session.host.read_frame.assert_called_once()

    def test_failed_gpu_blocks_software_frame_fallback_and_redacts_driver(self):
        # The core may emit software callbacks while the native EGL host is
        # shutting down. A broken driver path must never re-enter Tk or leak
        # native exception text containing private device identifiers.
        from anything_plays.gba_emulator import CoreSession
        session = object.__new__(GameCubeHardwareSession)
        session.host = Mock(read_frame=Mock(side_effect=OSError(
            "device /home/private/graphics-driver serial XYZ123 lost"
        )))
        session.emulator = SimpleNamespace(
            frame=None, frame_serial=4, lock=threading.Lock(),
            stop_event=threading.Event(),
            gamecube_preview_mode=DEFAULT_PREVIEW_MODE,
        )
        session.opengl_error = None
        session.raw_video_callbacks = 0
        session.null_video_callbacks = 0
        session.preview_readback_skips = 0
        session._last_preview_capture = None
        session.hardware_frames = 0
        session.gpu_readback_seconds = 0.0
        session.gpu_readback_max_seconds = 0.0
        session.gpu_readback_calls = 0
        session.video(RETRO_HW_FRAME_BUFFER_VALID, 4, 4, 16)
        self.assertEqual(session.opengl_error, "GPU readback failed (OSError)")
        self.assertNotIn("/home/", session.opengl_error)
        self.assertNotIn("XYZ123", session.opengl_error)
        with patch.object(CoreSession, "video") as native_fallback:
            session.video(1, 4, 4, 12)  # native software RGB frame
            native_fallback.assert_not_called()
        self.assertEqual(session.raw_video_callbacks, 2)
        self.assertEqual(session.emulator.frame_serial, 4)
        session.host.read_frame.assert_called_once()

    def test_empty_or_malformed_gpu_pixels_are_rejected_safely(self):
        for malformed in (
            None, np.empty((0, 8, 3), dtype=np.uint8),
            np.zeros((8, 8), dtype=np.uint8),
            np.zeros((8, 8, 4), dtype=np.uint8),
            np.zeros((8, 8, 3), dtype=np.float32),
        ):
            with self.subTest(frame_type=type(malformed).__name__,
                              shape=getattr(malformed, "shape", None)):
                session = object.__new__(GameCubeHardwareSession)
                session.host = Mock(read_frame=Mock(return_value=malformed))
                session.emulator = SimpleNamespace(
                    frame=None, frame_serial=1, lock=threading.Lock(),
                    stop_event=threading.Event(),
                    gamecube_preview_mode=DEFAULT_PREVIEW_MODE,
                )
                session.opengl_error = None
                session.raw_video_callbacks = 0
                session.null_video_callbacks = 0
                session.preview_readback_skips = 0
                session._last_preview_capture = None
                session.hardware_frames = 0
                session.gpu_readback_seconds = 0.0
                session.gpu_readback_max_seconds = 0.0
                session.gpu_readback_calls = 0
                session.video(RETRO_HW_FRAME_BUFFER_VALID, 8, 8, 32)
                self.assertTrue(session.emulator.stop_event.is_set())
                self.assertIsNotNone(session.opengl_error)
                self.assertIsNone(session.emulator.frame)
                self.assertEqual(session.emulator.frame_serial, 1)
                self.assertEqual(session.hardware_frames, 0)

    def test_null_callbacks_stay_null_without_copy(self):
        session = object.__new__(GameCubeHardwareSession)
        session.raw_video_callbacks = 0
        session.null_video_callbacks = 0
        session.video(None, 0, 0, 0)
        self.assertEqual(session.raw_video_callbacks, 1)
        self.assertEqual(session.null_video_callbacks, 1)


if __name__ == "__main__":
    unittest.main()
