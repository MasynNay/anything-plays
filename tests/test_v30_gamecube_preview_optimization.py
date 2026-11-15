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
    DEFAULT_PREVIEW_MODE, PREVIEW_FPS, preview_fps, should_capture,
)
from anything_plays.libretro_video import RETRO_HW_FRAME_BUFFER_VALID


class PreviewRatePolicyTests(unittest.TestCase):
    def test_balanced_preserves_every_native_frame_only_skips_cheap_preview(self):
        self.assertEqual(DEFAULT_PREVIEW_MODE, "Balanced (30 FPS)")
        self.assertEqual(preview_fps(DEFAULT_PREVIEW_MODE), 30)
        self.assertEqual(preview_fps("Performance (20 FPS)"), 20)
        self.assertEqual(preview_fps("Quality (60 FPS)"), 60)
        self.assertEqual(preview_fps("bad saved preference"), 30)
        self.assertTrue(should_capture(None, 0.0, DEFAULT_PREVIEW_MODE))
        self.assertFalse(should_capture(0.0, 0.010, DEFAULT_PREVIEW_MODE))
        self.assertTrue(should_capture(0.0, 0.035, DEFAULT_PREVIEW_MODE))
        self.assertFalse(should_capture(0.0, 0.040, "Performance (20 FPS)"))
        self.assertTrue(should_capture(0.0, 0.040, "Quality (60 FPS)"))
        self.assertTrue(should_capture(100.0, 0.0, DEFAULT_PREVIEW_MODE))

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

    def test_native_gpu_readback_errors_stop_without_publishing_stale_frames(self):
        for error in (
            OSError("USB GPU device reset"),
            RuntimeError("OpenGL context destroyed"),
            MemoryError("native allocation failed"),
            TypeError("invalid video surface"),
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
