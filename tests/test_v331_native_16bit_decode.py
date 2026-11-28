"""16-bit Libretro video preserves every legacy color and owns RGB pixels."""
import ctypes as C
import unittest
from unittest.mock import patch

import numpy as np

from anything_plays.libretro_video import decode_frame, RGB565, RGB1555


def historical_rgb(words, fmt):
    shift, mask = (11, 63) if fmt == RGB565 else (10, 31)
    return np.stack((((words >> shift) & 31) * 255 // 31,
                     ((words >> 5) & mask) * 255 // mask,
                     (words & 31) * 255 // 31),
                    axis=-1).astype(np.uint8)


class Native16BitDecodeTests(unittest.TestCase):
    def test_every_16bit_word_matches_legacy_color_expansion(self):
        words = np.arange(65536, dtype="<u2").reshape(256, 256)
        data = C.create_string_buffer(words.tobytes())
        for fmt in (RGB565, RGB1555):
            with self.subTest(fmt=fmt):
                actual = decode_frame(C.addressof(data), 256, 256, 512, fmt)
                np.testing.assert_array_equal(actual, historical_rgb(words, fmt))
                self.assertTrue(actual.flags.owndata)
                self.assertTrue(actual.flags.c_contiguous)
                self.assertEqual(actual.dtype, np.uint8)

    def test_random_unaligned_padded_scanlines(self):
        rng = np.random.default_rng(331)
        for fmt in (RGB565, RGB1555):
            for width, height in ((1, 1), (3, 5), (160, 144), (240, 160),
                                  (640, 480)):
                for padding in (0, 1, 7, 32):
                    with self.subTest(fmt=fmt, size=(width, height), pad=padding):
                        pitch = width * 2 + padding
                        native = rng.integers(0, 256, size=pitch * height,
                                              dtype=np.uint8).tobytes()
                        data = C.create_string_buffer(native)
                        words = np.ndarray((height, width), dtype="<u2",
                                           buffer=native, strides=(pitch, 2))
                        actual = decode_frame(C.addressof(data), width, height,
                                              pitch, fmt)
                        np.testing.assert_array_equal(actual, historical_rgb(words, fmt))

    def test_rgb1555_unused_high_bit_does_not_change_colors(self):
        words = np.arange(32768, dtype="<u2")
        raw = np.concatenate((words, words | 0x8000)).astype("<u2")
        data = C.create_string_buffer(raw.tobytes())
        actual = decode_frame(C.addressof(data), 256, 256, 512, RGB1555)
        np.testing.assert_array_equal(actual[:128], actual[128:])

    def test_published_frame_survives_native_buffer_reuse(self):
        for fmt in (RGB565, RGB1555):
            data = C.create_string_buffer(b"\xff\xff\x00\x00")
            first = decode_frame(C.addressof(data), 2, 1, 4, fmt)
            C.memset(C.addressof(data), 0, 4)
            second = decode_frame(C.addressof(data), 2, 1, 4, fmt)
            np.testing.assert_array_equal(first, [[[255, 255, 255], [0, 0, 0]]])
            np.testing.assert_array_equal(second, [[[0, 0, 0], [0, 0, 0]]])
            self.assertFalse(np.shares_memory(first, second))

    def test_only_one_rgb_output_and_one_channel_scratch_are_allocated(self):
        data = C.create_string_buffer(b"\xff\xff" * 12)
        original_empty = np.empty
        for fmt in (RGB565, RGB1555):
            with (
                patch("anything_plays.libretro_video.np.empty",
                      wraps=original_empty) as allocate,
                patch("anything_plays.libretro_video.np.stack",
                      side_effect=AssertionError("full-frame stack")),
            ):
                actual = decode_frame(C.addressof(data), 4, 3, 8, fmt)
            self.assertEqual(allocate.call_count, 2)
            self.assertEqual(allocate.call_args_list[0].args[0], (3, 4, 3))
            self.assertEqual(allocate.call_args_list[0].kwargs["dtype"], np.uint8)
            self.assertEqual(allocate.call_args_list[1].args[0], (3, 4))
            self.assertEqual(allocate.call_args_list[1].kwargs["dtype"], np.uint16)
            self.assertEqual(actual.shape, (3, 4, 3))

    def test_every_channel_operation_reuses_same_scratch(self):
        data = C.create_string_buffer(b"\x34\x12" * 12)
        with (
            patch("anything_plays.libretro_video.np.right_shift",
                  wraps=np.right_shift) as shift,
            patch("anything_plays.libretro_video.np.bitwise_and",
                  wraps=np.bitwise_and) as mask,
            patch("anything_plays.libretro_video.np.multiply",
                  wraps=np.multiply) as scale,
            patch("anything_plays.libretro_video.np.floor_divide",
                  wraps=np.floor_divide) as divide,
        ):
            decode_frame(C.addressof(data), 4, 3, 8, RGB565)
        scratch = shift.call_args_list[0].kwargs["out"]
        for operation in (shift, mask, scale, divide):
            self.assertEqual(operation.call_count, 3)
            for call in operation.call_args_list:
                self.assertIs(call.kwargs["out"], scratch)


if __name__ == "__main__":
    unittest.main()
