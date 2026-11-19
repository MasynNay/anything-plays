"""3.3 GameCube preview-mode changes: only GL preview cadence may change.

All tests run with synthetic RGB frames and a mocked GPU host. Native Dolphin
retro_run, input, PortAudio and physical OBS/speaker/camera behavior are not
exercised, so no hardware performance claim is made.
"""
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from anything_plays.gamecube_gpu import GameCubeHardwareSession
from anything_plays.gamecube_preview import PreviewCadenceTracker
from anything_plays.libretro_video import RETRO_HW_FRAME_BUFFER_VALID


def fake_session(mode="Performance (20 FPS)"):
    session = object.__new__(GameCubeHardwareSession)
    session.host = Mock(
        read_frame=Mock(return_value=np.full((8, 8, 3), 83, dtype=np.uint8))
    )
    session.emulator = SimpleNamespace(
        frame=None, frame_serial=0, lock=threading.Lock(),
        gamecube_preview_mode=mode, stop_event=threading.Event(),
    )
    session.hardware_frames = 0
    session.gpu_readback_seconds = 0.0
    session.gpu_readback_max_seconds = 0.0
    session.gpu_readback_calls = 0
    session.gpu_readback_timing_samples = 0
    session.preview_clock_failures = 0
    session.preview_readback_skips = 0
    session.raw_video_callbacks = 0
    session.null_video_callbacks = 0
    session.opengl_error = None
    session._last_preview_capture = None
    session._last_preview_publication = None
    session._last_preview_readback_duration = 0.0
    session._preview_cadence = PreviewCadenceTracker()
    return session


def native_video(session, start, finished=None):
    timestamps = (start,) if finished is None else (start, finished)
    with patch(
        "anything_plays.gamecube_gpu.time.monotonic",
        side_effect=timestamps,
    ):
        session.video(RETRO_HW_FRAME_BUFFER_VALID, 8, 8, 32)


class PreviewRateHandoffTests(unittest.TestCase):
    def test_upshift_20_to_60_releases_old_preview_deadline_once(self):
        session = fake_session()
        native_video(session, 10.0, 10.004)
        self.assertEqual(session.host.read_frame.call_count, 1)
        self.assertEqual(session._preview_cadence.snapshot()[
            "gamecube_preview_target_fps"], 20)

        # Just 8ms after the previous 20-FPS copy: the 20-FPS deadline
        # would ordinarily forbid a fresh GPU preview for another 42ms.
        session.emulator.gamecube_preview_mode = "Quality (60 FPS)"
        native_video(session, 10.008, 10.012)
        self.assertEqual(session.host.read_frame.call_count, 2)
        self.assertEqual(session.hardware_frames, 2)
        self.assertEqual(session.emulator.frame_serial, 2)
        self.assertEqual(session._preview_cadence.snapshot()[
            "gamecube_preview_target_fps"], 60)
        self.assertEqual(session._preview_cadence.snapshot()[
            "gamecube_preview_cadence_intervals"], 0)

        # The forced handoff is one copy only; native callbacks that arrive
        # before the new 60 FPS interval still skip expensive GPU readback.
        native_video(session, 10.016)
        self.assertEqual(session.host.read_frame.call_count, 2)
        native_video(session, 10.025, 10.029)
        self.assertEqual(session.host.read_frame.call_count, 3)
        self.assertEqual(session.preview_readback_skips, 1)
        self.assertEqual(session.raw_video_callbacks, 4)
        self.assertFalse(session.emulator.stop_event.is_set())

    def test_downshift_60_to_20_does_not_force_unneeded_gpu_copy(self):
        session = fake_session("Quality (60 FPS)")
        native_video(session, 20.0, 20.004)
        session.emulator.gamecube_preview_mode = "Performance (20 FPS)"
        native_video(session, 20.020)
        self.assertEqual(session.host.read_frame.call_count, 1)
        self.assertEqual(session.preview_readback_skips, 1)
        self.assertEqual(session._preview_cadence.snapshot()[
            "gamecube_preview_target_fps"], 20)
        native_video(session, 20.050, 20.054)
        self.assertEqual(session.host.read_frame.call_count, 2)
        self.assertEqual(session.hardware_frames, 2)
        self.assertEqual(session.emulator.frame_serial, 2)
        self.assertFalse(session.emulator.stop_event.is_set())

    def test_unrecognized_mode_normalizes_without_unwanted_extra_readback(self):
        session = fake_session("Balanced (30 FPS)")
        native_video(session, 30.0, 30.004)
        session.emulator.gamecube_preview_mode = {"not": "a known mode"}
        native_video(session, 30.010)
        self.assertEqual(session.host.read_frame.call_count, 1)
        self.assertEqual(session._preview_cadence.snapshot()[
            "gamecube_preview_target_fps"], 30)
        native_video(session, 30.035, 30.039)
        self.assertEqual(session.host.read_frame.call_count, 2)
        self.assertEqual(session.preview_readback_skips, 1)


if __name__ == "__main__":
    unittest.main()
