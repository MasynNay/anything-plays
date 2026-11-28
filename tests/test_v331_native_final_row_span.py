"""Copy only native video bytes needed by the visible strided RGB image."""
import ctypes as C
import unittest
from unittest.mock import patch

import numpy as np

from anything_plays.libretro_video import (
    decode_frame, XRGB8888, SOFTWARE_RGBA8888, RGB565, RGB1555,
    MAX_FRAME_BYTES, RETRO_HW_FRAME_BUFFER_VALID,
)


class FinalVideoRowSpanTests(unittest.TestCase):
    def test_all_pixel_formats_accept_no_padding_after_final_row(self):
        for fmt, pixel, color in (
            (XRGB8888, b"\x01\x02\x03\x99", (3, 2, 1)),
            (SOFTWARE_RGBA8888, b"\x01\x02\x03\x99", (1, 2, 3)),
            (RGB565, b"\x00\xf8", (255, 0, 0)),
            (RGB1555, b"\x00\x7c", (255, 0, 0)),
        ):
            for height in (1, 3, 17):
                for padding in (0, 1, 13, 31):
                    with self.subTest(fmt=fmt, height=height, padding=padding):
                        width = 5
                        row = pixel * width
                        pitch = len(row) + padding
                        raw = (row + b"\xab" * padding) * (height - 1) + row
                        expected_span = (height - 1) * pitch + len(row)
                        self.assertEqual(len(raw), expected_span)
                        # Exact-sized C array: create_string_buffer normally
                        # adds a trailing NUL. No need to read beyond raw.
                        native = C.create_string_buffer(raw, len(raw))
                        read = C.string_at
                        def bounded_read(pointer, size):
                            self.assertEqual(size, expected_span)
                            return read(pointer, size)
                        with patch("anything_plays.libretro_video.C.string_at",
                                   side_effect=bounded_read) as copy:
                            result = decode_frame(C.addressof(native), width,
                                                  height, pitch, fmt)
                        copy.assert_called_once_with(C.addressof(native),
                                                     expected_span)
                        expected = np.empty((height, width, 3), np.uint8)
                        expected[:] = color
                        np.testing.assert_array_equal(result, expected)
                        self.assertTrue(result.flags.owndata)

    def test_single_row_with_large_pitch_copies_visible_bytes_only(self):
        raw = C.create_string_buffer(b"\x10\x20\x30\xff", 4)
        with patch("anything_plays.libretro_video.C.string_at",
                   return_value=raw.raw) as copy:
            actual = decode_frame(C.addressof(raw), 1, 1, 65536, XRGB8888)
        copy.assert_called_once_with(C.addressof(raw), 4)
        np.testing.assert_array_equal(actual, [[[48, 32, 16]]])

    def test_original_geometry_budget_is_not_relaxed(self):
        # 1025 rows with 65536-byte pitch exceed the old 64MiB budget
        # even though the final visible pixel span is slightly smaller.
        with patch("anything_plays.libretro_video.C.string_at") as copy:
            with self.assertRaises(ValueError):
                decode_frame(1, 1, MAX_FRAME_BYTES // 65536 + 1,
                             65536, XRGB8888)
            with self.assertRaises(ValueError):
                decode_frame(1, 2, 1, 7, XRGB8888)
            self.assertIsNone(decode_frame(RETRO_HW_FRAME_BUFFER_VALID,
                                           2, 2, 8, XRGB8888))
            copy.assert_not_called()

    def test_copy_still_owns_pixels_after_native_buffer_changes(self):
        raw = C.create_string_buffer(bytes([1, 2, 3, 4, 0, 5, 6, 7, 8]), 9)
        actual = decode_frame(C.addressof(raw), 1, 2, 5, XRGB8888)
        C.memset(C.addressof(raw), 0, len(raw))
        np.testing.assert_array_equal(actual, [[[3, 2, 1]], [[7, 6, 5]]])


if __name__ == "__main__":
    unittest.main()
