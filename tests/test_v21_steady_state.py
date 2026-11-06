"""Bounded-resource soak of emulated video, audio, and frame-only state.

This is a synthetic regression test, not a substitute for a 24-hour test
using a real Libretro core, camera, and supported OS/graphics device.
"""
import ctypes as C
import gc
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
import tracemalloc
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import weakref

from anything_plays.gba_emulator import CoreSession
from anything_plays.libretro_video import XRGB8888


class SteadyStateTests(unittest.TestCase):
    def test_repeated_native_video_frames_replace_previous_storage(self):
        with TemporaryDirectory() as folder:
            emulator = SimpleNamespace(
                frame=None, frame_serial=0, lock=Lock()
            )
            with patch("pathlib.Path.home", return_value=Path(folder)):
                session = CoreSession(
                    emulator, "gba", Path(folder) / "synthetic.gba", None
                )
            session.pixel_format = XRGB8888
            width, height = 160, 120
            raw = C.create_string_buffer(width * height * 4)
            session.video(raw, width, height, width * 4)
            initial_frame = weakref.ref(emulator.frame)
            tracemalloc.start()
            try:
                for _ in range(1500):
                    session.video(raw, width, height, width * 4)
                gc.collect()
                retained, _ = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertEqual(emulator.frame_serial, 1501)
            self.assertEqual(emulator.frame.shape, (height, width, 3))
            self.assertIsNone(initial_frame(), "Old native frame is still held")
            self.assertLess(
                retained, 2 * 1024 * 1024,
                "Too much Python memory retained after 1500 video frames",
            )


if __name__ == "__main__":
    unittest.main()
