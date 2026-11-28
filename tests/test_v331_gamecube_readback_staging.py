"""GameCube GL staging buffer is bounded and reused without aliasing RGB frames.

The fake GL driver only writes small synthetic ctypes arrays. No real GPU,
Dolphin core, ROM, webcam, Tk window or private user data is accessed.
"""
import ctypes as C
import threading
import unittest

import numpy as np

from anything_plays.libretro_gpu_egl import (
    EGLFrameHost, bounded_dimensions,
)
from anything_plays.libretro_gpu_portable import PortableGLFrameHost


def fake_host(host_class=EGLFrameHost, *, width=6, height=5):
    host = host_class.__new__(host_class)
    host.owner = threading.get_ident()
    host.width, host.height = width, height
    host.fbo = 19
    host.last_gl_error = 0
    host._readback_staging = None
    captured = []
    invocations = []
    read_counter = [0]
    failures = [False]

    def gl(name, _restype, _argtypes):
        def call(*args):
            invocations.append(name)
            if name == "glGetError":
                return 0
            if name == "glReadPixels":
                if failures[0]:
                    raise RuntimeError("PRIVATE GPU driver path /home/someone")
                rgba = args[-1]
                captured.append(rgba)
                read_counter[0] += 1
                value = read_counter[0]
                # First/last pixels allow checking orientation and ownership.
                rgba[0:4] = [value, 30, 40, 255]
                index = (args[2] * args[3] - 1) * 4
                rgba[index:index + 4] = [value + 50, 60, 70, 255]
        return call

    host._gl = gl
    return host, captured, invocations, failures


class GameCubeReadbackStagingTests(unittest.TestCase):
    def test_repeated_reads_use_one_native_transfer_array(self):
        host, captured, _, _ = fake_host()
        frames = [host.read_frame(6, 5, flip_vertical=False) for _ in range(40)]
        self.assertEqual(len({id(buffer) for buffer in captured}), 1)
        self.assertIs(host._readback_staging, captured[0])
        self.assertEqual(len(host._readback_staging), 6 * 5 * 4)
        self.assertEqual([int(frame[0, 0, 0]) for frame in frames],
                         list(range(1, 41)))

    def test_returned_rgb_frames_do_not_alias_reused_rgba_storage(self):
        host, captured, _, _ = fake_host()
        first = host.read_frame(6, 5, flip_vertical=False)
        original = first.copy()
        second = host.read_frame(6, 5, flip_vertical=False)
        self.assertIs(captured[0], captured[1])
        self.assertFalse(np.shares_memory(first, second))
        self.assertTrue(first.flags.c_contiguous)
        self.assertEqual(first.shape, (5, 6, 3))
        self.assertTrue(np.array_equal(first, original))
        self.assertEqual(second[0, 0].tolist(), [2, 30, 40])
        captured[1][0] = 199  # mutating staging must not change Tk pixels
        self.assertEqual(first[0, 0, 0], 1)
        self.assertEqual(second[0, 0, 0], 2)

    def test_vertical_flip_still_produces_owned_correct_orientation(self):
        host, captured, _, _ = fake_host()
        flipped = host.read_frame(6, 5, flip_vertical=True)
        self.assertEqual(flipped[0, -1].tolist(), [51, 60, 70])
        self.assertEqual(flipped[-1, 0].tolist(), [1, 30, 40])
        host.read_frame(6, 5, flip_vertical=True)
        self.assertEqual(flipped[0, -1].tolist(), [51, 60, 70])
        self.assertIs(captured[0], captured[1])

    def test_resize_reallocates_once_then_reuses_new_bounded_buffer(self):
        host, captured, _, _ = fake_host()
        host.read_frame(6, 5)
        old = host._readback_staging
        host.read_frame(3, 2)
        updated = host._readback_staging
        self.assertIsNot(old, updated)
        self.assertEqual(len(updated), 3 * 2 * 4)
        host.read_frame(3, 2)
        self.assertIs(host._readback_staging, updated)
        self.assertIs(captured[1], captured[2])

    def test_invalid_dimension_does_not_allocate_or_call_gl(self):
        host, captured, gl_calls, _ = fake_host()
        for width, height in ((0, 2), (6, 0), (7, 2), (6, 6), (-1, 1)):
            with self.subTest(width=width, height=height):
                with self.assertRaises(ValueError):
                    host.read_frame(width, height)
        self.assertIsNone(host._readback_staging)
        self.assertEqual(captured, [])
        self.assertEqual(gl_calls, [])

    def test_native_read_error_restores_gl_state_and_never_returns_old_rgb(self):
        host, captured, calls, fails = fake_host()
        host.read_frame(6, 5)
        fails[0] = True
        with self.assertRaisesRegex(RuntimeError, "PRIVATE GPU"):
            host.read_frame(6, 5)
        # Restoration must run even when native transfer fails, and the
        # failed frame never reaches the app's published output.
        self.assertEqual(calls[-1], "glBindFramebuffer")
        self.assertEqual(len(captured), 1)
        fails[0] = False
        good = host.read_frame(6, 5, flip_vertical=False)
        self.assertEqual(good[0, 0].tolist(), [2, 30, 40])
        self.assertIs(host._readback_staging, captured[0])

    def test_portable_windows_macos_host_shares_the_same_reader(self):
        host, captures, _, _ = fake_host(PortableGLFrameHost)
        first = host.read_frame(6, 5, flip_vertical=False)
        second = host.read_frame(6, 5, flip_vertical=False)
        self.assertIs(captures[0], captures[1])
        self.assertEqual(first[0, 0, 0], 1)
        self.assertEqual(second[0, 0, 0], 2)

    def test_egl_close_retires_buffer_even_with_no_native_context(self):
        host, _, _, _ = fake_host()
        host.read_frame(6, 5)
        self.assertIsNotNone(host._readback_staging)
        host.display = None
        host.surface = None
        host.context = None
        host._entered = False
        host._eglfunc = {}
        host.core_reset = host.core_destroy = None
        host.color_tex = host.depth_stencil = 0
        host.close()
        self.assertIsNone(host._readback_staging)

    def test_portable_close_retires_buffer_even_if_context_was_lost(self):
        host, _, _, _ = fake_host(PortableGLFrameHost)
        host.read_frame(6, 5)
        host.context = None
        host._entered = False
        host.close()
        self.assertIsNone(host._readback_staging)

    def test_long_session_allocations_stay_bounded_without_frame_aliasing(self):
        host, captured, _, _ = fake_host(width=4, height=4)
        first = host.read_frame(4, 4)
        expected = first.copy()
        for _ in range(500):
            last = host.read_frame(4, 4)
        self.assertEqual(len(captured), 501)
        self.assertEqual(len({id(buffer) for buffer in captured}), 1)
        self.assertTrue(np.array_equal(first, expected))
        self.assertEqual(last.shape, (4, 4, 3))


if __name__ == "__main__":
    unittest.main()
