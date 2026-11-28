"""Borrowed PCM ingress must never escape the synchronous push boundary."""
import ctypes as C
import unittest
from unittest.mock import patch

import numpy as np

from anything_plays.libretro_audio import (
    AudioSink, RESAMPLE_INPUT_CHUNK, MAX_QUEUE_CHUNK_FRAMES,
)


class AudioIngressOwnershipTests(unittest.TestCase):
    def test_queue_receives_borrowed_views_but_owns_every_block(self):
        sink = AudioSink()
        source = np.arange(10000, dtype=np.int16).reshape(-1, 2)
        expected = source.copy()
        with patch.object(sink, "_enqueue_bounded",
                          wraps=sink._enqueue_bounded) as enqueue:
            sink.push(source)
        self.assertEqual(enqueue.call_count, 3)
        for call in enqueue.call_args_list:
            self.assertTrue(np.shares_memory(call.args[0], source))
        for part in sink.chunks.queue:
            self.assertTrue(part.flags.owndata)
            self.assertFalse(np.shares_memory(part, source))
        source.fill(0)
        out = np.empty_like(expected)
        sink.callback(out, len(out), None, None)
        np.testing.assert_array_equal(out, expected)

    def test_noncontiguous_input_remains_owned_and_ordered(self):
        sink = AudioSink()
        source = np.arange(16000, dtype=np.int16).reshape(-1, 4)[:, ::2]
        expected = source.copy()
        sink.push(source)
        source.fill(-123)
        out = np.empty_like(expected)
        sink.callback(out, len(out), None, None)
        np.testing.assert_array_equal(out, expected)

    def test_native_batch_is_independent_of_reused_ctypes_storage(self):
        sink = AudioSink()
        count = RESAMPLE_INPUT_CHUNK * 2 + 1
        source = np.arange(count * 2, dtype=np.int16).reshape(-1, 2)
        native = (C.c_int16 * (count * 2))(*source.ravel())
        self.assertEqual(sink.batch(C.addressof(native), count), count)
        C.memset(C.addressof(native), 0, C.sizeof(native))
        out = np.empty_like(source)
        sink.callback(out, count, None, None)
        np.testing.assert_array_equal(out, source)
        self.assertEqual(sink.native_pcm_frames, count)

    def test_resampled_tail_and_queue_do_not_alias_input(self):
        rng = np.random.default_rng(331)
        for step in (131072 / 48000, 44100 / 48000, 8000 / 48000):
            with self.subTest(step=step):
                sink = AudioSink()
                reference = AudioSink()
                sink._resample_step = reference._resample_step = step
                first = rng.integers(-32768, 32767, size=(3001, 2),
                                     dtype=np.int16)
                second = rng.integers(-32768, 32767, size=(222, 2),
                                      dtype=np.int16)
                # The previous implementation copied each input chunk.
                for begin in range(0, len(first), RESAMPLE_INPUT_CHUNK):
                    part = first[begin:begin + RESAMPLE_INPUT_CHUNK].copy()
                    reference._enqueue_bounded(reference._resample(part))
                sink.push(first)
                self.assertFalse(np.shares_memory(sink._resample_tail, first))
                for part in sink.chunks.queue:
                    self.assertFalse(np.shares_memory(part, first))
                    self.assertLessEqual(len(part), MAX_QUEUE_CHUNK_FRAMES)
                first.fill(0)
                sink.push(second)
                reference.push(second.copy())
                np.testing.assert_array_equal(
                    np.concatenate(list(sink.chunks.queue)),
                    np.concatenate(list(reference.chunks.queue)),
                )
                self.assertEqual(sink._resample_next, reference._resample_next)

    def test_single_sample_staging_is_safe_to_reuse(self):
        sink = AudioSink()
        for index in range(600):
            sink.sample(index, -index)
        sink._flush_single_samples()
        sink._single_samples.fill(999)
        out = np.empty((600, 2), dtype=np.int16)
        sink.callback(out, len(out), None, None)
        expected = np.arange(600, dtype=np.int16)
        np.testing.assert_array_equal(out[:, 0], expected)
        np.testing.assert_array_equal(out[:, 1], -expected)

    def test_large_batches_keep_existing_queue_drop_policy(self):
        sink = AudioSink()
        source = np.arange(RESAMPLE_INPUT_CHUNK * 40 * 2,
                           dtype=np.int16).reshape(-1, 2)
        sink.push(source)
        self.assertEqual(sink.chunks.qsize(), 32)
        self.assertEqual(sink.queue_dropped_frames, RESAMPLE_INPUT_CHUNK * 8)
        expected = source[RESAMPLE_INPUT_CHUNK * 8:].copy()
        source.fill(0)
        out = np.empty_like(expected)
        sink.callback(out, len(out), None, None)
        np.testing.assert_array_equal(out, expected)


if __name__ == "__main__":
    unittest.main()
