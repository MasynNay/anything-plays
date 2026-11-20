"""3.3: late Libretro software frames cannot resurrect stopped game pixels.

Tests deliberately overlap Stop, native decode, and frame-lock acquisition
without loading a native core, ROM, camera or using external keyboard events.
"""
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from anything_plays.gba_emulator import CoreSession


def software_session():
    session = object.__new__(CoreSession)
    session.pixel_format = 0
    session.emulator = SimpleNamespace(
        stop_event=threading.Event(), lock=threading.Lock(),
        frame=None, frame_serial=7,
    )
    return session


class SoftwareVideoStopRaceTests(unittest.TestCase):
    def test_stop_before_native_decode_skips_unneeded_copy(self):
        session = software_session()
        session.emulator.stop_event.set()
        with patch("anything_plays.gba_emulator.decode_frame") as decode:
            session.video(1, 16, 16, 32)
        decode.assert_not_called()
        self.assertIsNone(session.emulator.frame)
        self.assertEqual(session.emulator.frame_serial, 7)

    def test_stop_during_decode_discards_late_frame(self):
        session = software_session()
        pixel_frame = object()

        def decode_then_stop(*_args):
            session.emulator.stop_event.set()
            return pixel_frame

        with patch("anything_plays.gba_emulator.decode_frame",
                   side_effect=decode_then_stop) as decode:
            session.video(1, 16, 16, 32)
        decode.assert_called_once_with(1, 16, 16, 32, 0)
        self.assertIsNone(session.emulator.frame)
        self.assertEqual(session.emulator.frame_serial, 7)

    def test_stop_while_waiting_for_frame_lock_drops_old_image(self):
        session = software_session()
        old_pixels = object()

        class StopDuringAcquire:
            def __enter__(self):
                # Simulate Stop while the decoder waits for the UI frame lock.
                session.emulator.stop_event.set()
                session.emulator.frame = None
                session.emulator.frame_serial += 1
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        session.emulator.lock = StopDuringAcquire()
        with patch("anything_plays.gba_emulator.decode_frame",
                   return_value=old_pixels) as decode:
            session.video(1, 8, 8, 16)
        decode.assert_called_once()
        self.assertIsNone(session.emulator.frame)
        self.assertEqual(session.emulator.frame_serial, 8)

    def test_normal_software_frame_publishes_and_advances_revision(self):
        session = software_session()
        rgb = object()
        with patch("anything_plays.gba_emulator.decode_frame",
                   return_value=rgb):
            session.video(1, 24, 16, 48)
            self.assertIs(session.emulator.frame, rgb)
            self.assertEqual(session.emulator.frame_serial, 8)
            session.video(1, 24, 16, 48)
            self.assertEqual(session.emulator.frame_serial, 9)

    def test_legacy_emulator_without_stop_event_still_accepts_video(self):
        session = software_session()
        del session.emulator.stop_event
        rgb = object()
        with patch("anything_plays.gba_emulator.decode_frame",
                   return_value=rgb):
            session.video(1, 24, 16, 48)
        self.assertIs(session.emulator.frame, rgb)
        self.assertEqual(session.emulator.frame_serial, 8)

    def test_empty_or_rejected_native_frames_do_not_increase_revision(self):
        session = software_session()
        with patch("anything_plays.gba_emulator.decode_frame",
                   return_value=None):
            session.video(1, 24, 16, 48)
        with patch("anything_plays.gba_emulator.decode_frame",
                   side_effect=ValueError("unsupported pixel buffer")):
            session.video(1, 24, 16, 48)
        self.assertIsNone(session.emulator.frame)
        self.assertEqual(session.emulator.frame_serial, 7)


if __name__ == "__main__":
    unittest.main()
