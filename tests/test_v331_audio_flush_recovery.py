"""Recover the fixed single-sample buffer after a failed PCM flush."""
import ctypes as C
import unittest
from unittest.mock import patch

import numpy as np

from anything_plays.libretro_audio import AudioSink, SAMPLE_BLOCK_FRAMES


class AudioFlushRecoveryTests(unittest.TestCase):
    def test_failed_full_block_does_not_poison_future_single_samples(self):
        sink = AudioSink()
        for index in range(SAMPLE_BLOCK_FRAMES - 1):
            sink.sample(index, -index)
        with patch.object(sink, "push", side_effect=MemoryError("allocation")):
            with self.assertRaises(MemoryError):
                sink.sample(99, -99)
        self.assertEqual(sink._single_count, 0)
        self.assertEqual(sink.native_pcm_frames, SAMPLE_BLOCK_FRAMES)
        sink.sample(23, -23)
        sink._flush_single_samples()
        out = np.empty((1, 2), dtype=np.int16)
        sink.callback(out, 1, None, None)
        np.testing.assert_array_equal(out, [[23, -23]])

    def test_failed_partial_flush_can_recover_with_batch(self):
        sink = AudioSink()
        sink.sample(10, -10)
        data = (C.c_int16 * 4)(12, -12, 13, -13)
        with patch.object(sink, "push", side_effect=RuntimeError("queue")):
            with self.assertRaises(RuntimeError):
                sink.batch(C.addressof(data), 2)
        self.assertEqual(sink._single_count, 0)
        self.assertEqual(sink.batch(C.addressof(data), 2), 2)
        out = np.empty((2, 2), dtype=np.int16)
        sink.callback(out, 2, None, None)
        np.testing.assert_array_equal(out, [[12, -12], [13, -13]])

    def test_partially_enqueued_block_is_not_replayed_on_retry(self):
        sink = AudioSink()
        sink.sample(11, -11)
        sink.sample(22, -22)
        push = sink.push
        def partial(block):
            push(block[:1])
            raise MemoryError("partial")
        with patch.object(sink, "push", side_effect=partial):
            with self.assertRaises(MemoryError):
                sink._flush_single_samples()
        self.assertEqual(sink._single_count, 0)
        sink.sample(33, -33)
        sink._flush_single_samples()
        out = np.empty((3, 2), dtype=np.int16)
        sink.callback(out, 3, None, None)
        np.testing.assert_array_equal(out, [[11, -11], [33, -33], [0, 0]])
        self.assertEqual(sink.native_pcm_frames, 3)
        self.assertEqual(sink.output_underrun_frames, 1)

    def test_successful_flush_keeps_original_sample_order(self):
        sink = AudioSink()
        sink.sample(10, -10)
        sink.sample(20, -20)
        data = (C.c_int16 * 2)(30, -30)
        sink.batch(C.addressof(data), 1)
        sink.sample(40, -40)
        sink._flush_single_samples()
        out = np.empty((4, 2), dtype=np.int16)
        sink.callback(out, 4, None, None)
        np.testing.assert_array_equal(out, [[10, -10], [20, -20],
                                           [30, -30], [40, -40]])
        self.assertEqual(sink._single_count, 0)


if __name__ == "__main__":
    unittest.main()
