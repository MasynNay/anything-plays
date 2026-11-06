"""Headless tests for independent game input and audio buffering."""

import ctypes as C
import unittest

import numpy as np

from anything_plays.libretro_audio import AudioSink
from anything_plays.libretro_input import IDS, InputBuffer


class InputBufferTests(unittest.TestCase):
    def test_camera_press_expires_on_exact_frame(self):
        inputs = InputBuffer()
        inputs.queue_press("A", 2)
        for _ in range(2):
            inputs.before_frame(armed=True)
            self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 1)
            inputs.after_frame()
        inputs.before_frame(armed=True)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 0)

    def test_manual_input_survives_disarmed_camera(self):
        inputs = InputBuffer()
        inputs.set_manual("B", True)
        inputs.queue_press("A", 5)
        inputs.before_frame(armed=False)
        self.assertEqual(inputs.state(0, 1, 0, IDS["B"]), 1)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 0)
        inputs.release_manual()
        inputs.before_frame(armed=False)
        self.assertEqual(inputs.state(0, 1, 0, IDS["B"]), 0)

    def test_input_is_restricted_to_first_joypad(self):
        inputs = InputBuffer()
        inputs.set_manual("A", True)
        inputs.before_frame(armed=False)
        self.assertEqual(inputs.state(1, 1, 0, IDS["A"]), 0)
        self.assertEqual(inputs.state(0, 2, 0, IDS["A"]), 0)

    def test_camera_queue_is_bounded(self):
        inputs = InputBuffer()
        for _ in range(100):
            inputs.queue_press("Left", 1)
        self.assertEqual(inputs.commands.qsize(), 32)


class AudioBufferTests(unittest.TestCase):
    def test_silence_is_filled_after_audio_runs_out(self):
        audio = AudioSink()
        audio.push(np.array([[10, 20], [-1, -2]], dtype=np.int16))
        output = np.full((4, 2), 900, dtype=np.int16)
        audio.callback(output, 4, None, None)
        self.assertEqual(output.tolist(), [[10, 20], [-1, -2], [0, 0], [0, 0]])

    def test_single_sample_audio_uses_fixed_size_blocks(self):
        audio = AudioSink()
        for index in range(3000):
            audio.sample(index % 12000, -(index % 12000))
        # 3000 callbacks used to create 3000 arrays and flood the queue.
        self.assertEqual(audio.chunks.qsize(), 11)
        self.assertEqual(audio._single_count, 184)
        audio._flush_single_samples()
        self.assertEqual(audio.chunks.qsize(), 12)
        self.assertEqual(audio._single_count, 0)
        output = np.zeros((3000, 2), dtype=np.int16)
        audio.callback(output, 3000, None, None)
        self.assertEqual(output[0].tolist(), [0, 0])
        self.assertEqual(output[-1].tolist(), [2999, -2999])

    def test_audio_memory_is_bounded_after_many_samples(self):
        audio = AudioSink()
        for index in range(20000):
            audio.sample(index % 100, -(index % 100))
        self.assertLessEqual(audio.chunks.qsize(), 32)
        self.assertLessEqual(audio._single_count, 256)
        # Even after an overnight session, old samples are dropped instead of
        # allocating an ever-growing backlog.
        self.assertLessEqual(
            sum(chunk.nbytes for chunk in list(audio.chunks.queue)),
            32 * 256 * 2 * np.dtype(np.int16).itemsize,
        )

    def test_native_audio_batch_copies_core_owned_buffer(self):
        audio = AudioSink()
        samples = (C.c_int16 * 4)(1, 2, 3, 4)
        self.assertEqual(audio.batch(C.cast(samples, C.c_void_p), 2), 2)
        samples[0] = 99
        out = np.zeros((2, 2), dtype=np.int16)
        audio.callback(out, 2, None, None)
        self.assertEqual(out.tolist(), [[1, 2], [3, 4]])


if __name__ == "__main__":
    unittest.main()
