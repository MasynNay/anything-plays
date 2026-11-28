"""Owned XRGB8888 decode preserves the established little-endian contract."""
import ctypes as C
import unittest
from unittest.mock import patch

import numpy as np

from anything_plays.libretro_video import (
    decode_frame, XRGB8888, SOFTWARE_RGBA8888, RGB565, RGB1555,
    MAX_FRAME_BYTES, RETRO_HW_FRAME_BUFFER_VALID,
)


class NativeXrgbDecodeTests(unittest.TestCase):
    def test_every_byte_value_and_unused_alpha_are_handled(self):
        pixels = np.zeros((256, 4), dtype=np.uint8)
        pixels[:, 0] = np.arange(256, dtype=np.uint8)
        pixels[:, 1] = pixels[::-1, 0]
        pixels[:, 2] = np.roll(pixels[:, 0], 37)
        pixels[:, 3] = np.roll(pixels[:, 0], 101)
        raw = C.create_string_buffer(pixels.tobytes())
        actual = decode_frame(C.addressof(raw), 256, 1, 1024, XRGB8888)
        np.testing.assert_array_equal(actual, pixels[None, :, 2::-1])

    def test_random_padded_unaligned_rows_match_previous_numeric_decoder(self):
        rng = np.random.default_rng(331)
        for width, height in ((1, 1), (3, 5), (160, 144), (640, 480)):
            for padding in (0, 1, 7, 32):
                pitch = width * 4 + padding
                native = rng.integers(0, 256, size=pitch * height,
                                      dtype=np.uint8).tobytes()
                raw = C.create_string_buffer(native)
                words = np.ndarray((height, width), dtype="<u4",
                                   buffer=native, strides=(pitch, 4))
                expected = np.stack(((words >> 16) & 255,
                                     (words >> 8) & 255, words & 255),
                                    axis=-1).astype(np.uint8)
                actual = decode_frame(C.addressof(raw), width, height,
                                      pitch, XRGB8888)
                np.testing.assert_array_equal(actual, expected)
                self.assertTrue(actual.flags.c_contiguous)
                self.assertTrue(actual.flags.owndata)

    def test_native_buffer_reuse_does_not_mutate_previously_published_frame(self):
        raw = C.create_string_buffer(bytes([1, 2, 3, 255, 7, 8, 9, 99]))
        first = decode_frame(C.addressof(raw), 2, 1, 8, XRGB8888)
        C.memset(C.addressof(raw), 42, 8)
        second = decode_frame(C.addressof(raw), 2, 1, 8, XRGB8888)
        np.testing.assert_array_equal(first, [[[3, 2, 1], [9, 8, 7]]])
        np.testing.assert_array_equal(second, [[[42, 42, 42], [42, 42, 42]]])

    def test_xrgb_path_does_not_stack_full_frame_channel_arrays(self):
        raw = C.create_string_buffer(bytes([1, 2, 3, 4]) * 16)
        with patch("anything_plays.libretro_video.np.stack",
                   side_effect=AssertionError("unnecessary full frame stack")):
            result = decode_frame(C.addressof(raw), 4, 4, 16, XRGB8888)
        self.assertEqual(result.shape, (4, 4, 3))
        self.assertEqual(result.dtype, np.uint8)
        np.testing.assert_array_equal(result[0, 0], [3, 2, 1])

    def test_dolphin_rgba_path_keeps_its_distinct_channel_order(self):
        raw = C.create_string_buffer(bytes([1, 2, 3, 4]))
        actual = decode_frame(C.addressof(raw), 1, 1, 4, SOFTWARE_RGBA8888)
        np.testing.assert_array_equal(actual, [[[1, 2, 3]]])

    def test_16bit_color_expansion_remains_unchanged(self):
        for fmt, red, green in ((RGB565, 0xF800, 0x07E0),
                                (RGB1555, 0x7C00, 0x03E0)):
            raw = C.create_string_buffer(
                b"".join(v.to_bytes(2, "little") for v in (red, green, 31))
            )
            actual = decode_frame(C.addressof(raw), 3, 1, 6, fmt)
            np.testing.assert_array_equal(actual, [[[255, 0, 0],
                                                     [0, 255, 0],
                                                     [0, 0, 255]]])

    def test_invalid_sizes_and_hardware_sentinel_never_read_pointer(self):
        with patch("anything_plays.libretro_video.C.string_at") as read:
            self.assertIsNone(decode_frame(RETRO_HW_FRAME_BUFFER_VALID,
                                           10, 10, 40, XRGB8888))
            with self.assertRaises(ValueError):
                decode_frame(1, 100, 100, 399, XRGB8888)
            with self.assertRaises(ValueError):
                decode_frame(1, 4096, 4096, MAX_FRAME_BYTES, XRGB8888)
            read.assert_not_called()


if __name__ == "__main__":
    unittest.main()
