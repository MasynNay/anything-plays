"""PortAudio callbacks belong to one candidate stream, even after failure.

Synthetic drivers only. No actual audio device, native core, ROM or speakers.
"""
import threading
import unittest
from unittest.mock import Mock, patch

import numpy as np

from anything_plays.libretro_audio import AudioSink


def take(callback, count=2):
    out = np.full((count, 2), -300, dtype=np.int16)
    callback(out, count, None, None)
    return out


class CallbackOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.audio = AudioSink()
        self.pcm = np.array([[100, 200], [300, 400], [500, 600],
                             [700, 800]], dtype=np.int16)
        self.audio.push(self.pcm)
        self.backend = Mock()
        self.backend.query_devices.return_value = {"default_samplerate": 44100}
        self.streams = []
        self.callbacks = []
        self.scope = patch("anything_plays.libretro_audio.sd", self.backend)
        self.scope.start()
        self.addCleanup(self.scope.stop)
        self.addCleanup(self.audio.close)

    def make_stream(self, **kwargs):
        stream = Mock()
        self.streams.append(stream)
        self.callbacks.append(kwargs["callback"])
        return stream

    def test_normal_candidate_callback_delivers_pcm_and_metrics(self):
        self.backend.OutputStream.side_effect = self.make_stream
        self.audio.start(48000)
        np.testing.assert_array_equal(take(self.callbacks[0]), self.pcm[:2])
        self.assertEqual(self.audio.output_callback_calls, 1)
        self.assertTrue(self.audio.output_active)

    def test_constructor_callback_is_silent_until_queue_is_ready(self):
        captured = []
        def constructor(**kwargs):
            stream = self.make_stream(**kwargs)
            captured.append(take(kwargs["callback"]))
            return stream
        self.backend.OutputStream.side_effect = constructor
        self.audio.start(48000)
        np.testing.assert_array_equal(captured[0], np.zeros((2, 2)))
        self.assertEqual(self.audio.output_callback_calls, 0)
        np.testing.assert_array_equal(take(self.callbacks[0]), self.pcm[:2])

    def test_rejected_stream_cannot_consume_replacement_queue(self):
        def constructor(**kwargs):
            stream = self.make_stream(**kwargs)
            if len(self.streams) == 1:
                def reject():
                    take(self.callbacks[0], 1)
                    raise RuntimeError("failed start")
                stream.start.side_effect = reject
                stream.close.side_effect = OSError("failed cleanup")
            return stream
        self.backend.OutputStream.side_effect = constructor
        self.audio.start(48000)
        self.assertEqual(len(self.callbacks), 2)
        self.assertIs(self.audio.stream, self.streams[1])
        self.assertEqual(self.audio.output_callback_calls, 0)
        before = self.audio.chunks.qsize()
        np.testing.assert_array_equal(take(self.callbacks[0]), np.zeros((2, 2)))
        self.assertEqual(self.audio.chunks.qsize(), before)
        self.assertEqual(self.audio.output_callback_calls, 0)
        out = take(self.callbacks[1], 1)
        self.assertGreater(out[0, 0], 0)
        self.assertEqual(self.audio.output_callback_calls, 1)

    def test_callback_during_rejected_stream_close_does_not_consume_source(self):
        captured = []
        def constructor(**kwargs):
            stream = self.make_stream(**kwargs)
            if len(self.streams) == 1:
                stream.start.side_effect = RuntimeError("start rejected")
                stream.close.side_effect = lambda: captured.append(
                    take(self.callbacks[0])
                )
            return stream
        self.backend.OutputStream.side_effect = constructor
        self.audio.start(48000)
        np.testing.assert_array_equal(captured[0], np.zeros((2, 2)))
        self.assertEqual(self.audio.output_callback_calls, 0)
        self.assertEqual(self.audio.output_callback_requested_frames, 0)
        self.assertGreater(take(self.callbacks[1], 1)[0, 0], 0)

    def test_all_rejected_callbacks_remain_silent_after_failure(self):
        def constructor(**kwargs):
            stream = self.make_stream(**kwargs)
            stream.start.side_effect = RuntimeError("failed device")
            return stream
        self.backend.OutputStream.side_effect = constructor
        self.audio.start(48000)
        before = self.audio.chunks.qsize()
        self.assertFalse(self.audio.output_active)
        for callback in self.callbacks:
            np.testing.assert_array_equal(take(callback), np.zeros((2, 2)))
        self.assertEqual(self.audio.chunks.qsize(), before)
        self.assertEqual(self.audio.output_callback_calls, 0)

    def test_close_revokes_before_native_stop_or_close_callbacks(self):
        captured = []
        self.backend.OutputStream.side_effect = self.make_stream
        self.audio.start(48000)
        stream = self.streams[0]
        stream.stop.side_effect = lambda: captured.append(take(self.callbacks[0]))
        stream.close.side_effect = lambda: captured.append(take(self.callbacks[0]))
        self.audio.close()
        self.assertEqual(len(captured), 2)
        for output in captured:
            np.testing.assert_array_equal(output, np.zeros((2, 2)))
        self.assertEqual(self.audio.output_callback_calls, 0)
        self.assertFalse(self.audio.output_active)

    def test_closed_callback_cannot_drain_audio_after_later_start(self):
        self.backend.OutputStream.side_effect = self.make_stream
        self.audio.start(48000)
        self.audio.close()
        self.audio.start(48000)
        before = self.audio.chunks.qsize()
        np.testing.assert_array_equal(take(self.callbacks[0]), np.zeros((2, 2)))
        self.assertEqual(self.audio.chunks.qsize(), before)
        self.assertEqual(self.audio.output_callback_calls, 0)
        np.testing.assert_array_equal(take(self.callbacks[1]), self.pcm[:2])

    def test_delayed_stale_callbacks_on_another_thread_are_all_silent(self):
        self.backend.OutputStream.side_effect = self.make_stream
        self.audio.start(48000)
        self.audio.close()
        self.audio.start(48000)
        outputs = []
        def delayed():
            for _ in range(300):
                outputs.append(take(self.callbacks[0]))
        thread = threading.Thread(target=delayed)
        thread.start()
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(outputs), 300)
        self.assertTrue(all(not np.any(out) for out in outputs))
        self.assertEqual(self.audio.output_callback_calls, 0)
        np.testing.assert_array_equal(take(self.callbacks[1]), self.pcm[:2])


if __name__ == "__main__":
    unittest.main()
