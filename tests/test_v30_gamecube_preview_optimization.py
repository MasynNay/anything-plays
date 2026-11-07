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

    def test_null_callbacks_stay_null_without_copy(self):
        session = object.__new__(GameCubeHardwareSession)
        session.raw_video_callbacks = 0
        session.null_video_callbacks = 0
        session.video(None, 0, 0, 0)
        self.assertEqual(session.raw_video_callbacks, 1)
        self.assertEqual(session.null_video_callbacks, 1)


if __name__ == "__main__":
    unittest.main()
