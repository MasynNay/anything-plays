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

    def test_missing_audio_backend_is_reported_to_game(self):
        from unittest.mock import patch
        with patch("anything_plays.libretro_audio.sd", None):
            audio = AudioSink()
            audio.start(44100)
        self.assertFalse(audio.output_active)
        self.assertIn("audio backend", audio.output_error)
        audio.close()

    def test_device_failure_is_not_silently_treated_as_sound(self):
        from unittest.mock import Mock, patch
        fake = Mock()
        fake.OutputStream.side_effect = RuntimeError("device missing")
        with patch("anything_plays.libretro_audio.sd", fake):
            audio = AudioSink()
            audio.start(48000)
        self.assertFalse(audio.output_active)
        self.assertIn("device missing", audio.output_error)

    def test_no_default_audio_device_cannot_crash_native_gameplay(self):
        from unittest.mock import Mock, patch
        fake = Mock()
        # Matches PortAudioError from sounddevice.query_devices(kind="output")
        # when the OS has no current default output device.
        class NoDefaultOutput(Exception):
            pass
        fake.query_devices.side_effect = NoDefaultOutput(
            "Error querying device -1"
        )
        fake.OutputStream.side_effect = NoDefaultOutput(
            "Error opening OutputStream: device -1"
        )
        with patch("anything_plays.libretro_audio.sd", fake):
            audio = AudioSink()
            audio.start(48000)
            self.assertFalse(audio.output_active)
            self.assertIn("No usable audio output device", audio.output_error)
            self.assertIn("device -1", audio.output_error)
            # Core audio must still be accepted in silent-mode operation.
            audio.push(np.array([[12, -12]], dtype=np.int16))
            self.assertEqual(audio.chunks.qsize(), 1)
            audio.close()

    def test_no_default_device_can_fallback_to_48000_hz(self):
        from unittest.mock import Mock, patch
        fake = Mock()
        fake.query_devices.side_effect = RuntimeError("No default speaker")
        with patch("anything_plays.libretro_audio.sd", fake):
            audio = AudioSink()
            audio.start(131072)
            self.assertTrue(audio.output_active)
            self.assertEqual(audio.source_sample_rate, 131072)
            self.assertEqual(audio.output_sample_rate, 48000)
            self.assertAlmostEqual(audio._resample_step, 131072 / 48000)
            audio.close()

    def test_native_gb_sample_rate_resamples_to_real_device_frequency(self):
        from unittest.mock import Mock, patch
        fake = Mock()
        fake.query_devices.return_value = {"default_samplerate": 48000.0}
        with patch("anything_plays.libretro_audio.sd", fake):
            audio = AudioSink()
            audio.start(131072)
        self.assertTrue(audio.output_active)
        self.assertEqual(audio.source_sample_rate, 131072)
        self.assertEqual(audio.output_sample_rate, 48000)
        self.assertAlmostEqual(audio._resample_step, 131072 / 48000)
        self.assertEqual(fake.OutputStream.call_args.kwargs["samplerate"], 48000)
        n = 2048
        t = np.arange(n, dtype=np.float64)
        signal = (10000 * np.sin(2 * np.pi * 440 * t / 131072)).astype(np.int16)
        stereo = np.stack((signal, -signal), axis=1)
        audio.push(stereo)
        converted = audio.chunks.get_nowait()
        self.assertGreater(len(converted), 700)
        self.assertLess(len(converted), 780)
        self.assertGreater(np.max(np.abs(converted)), 1000)
        self.assertTrue(np.array_equal(converted[:, 0], -converted[:, 1]))
        audio.close()

    def test_resampling_does_not_restart_phase_at_chunk_boundaries(self):
        from unittest.mock import Mock, patch
        device = Mock()
        device.query_devices.return_value = {"default_samplerate": 48000.0}
        n = 4096
        t = np.arange(n, dtype=np.float64)
        values = (5000 * np.sin(2 * np.pi * 330 * t / 131072)).astype(np.int16)
        wave = np.stack((values, values), axis=1)
        with patch("anything_plays.libretro_audio.sd", device):
            whole = AudioSink()
            whole.start(131072)
            fragmented = AudioSink()
            fragmented.start(131072)
        whole.push(wave)
        for offset in range(0, len(wave), 157):
            fragmented.push(wave[offset:offset + 157])
        continuous = np.concatenate(list(whole.chunks.queue), axis=0)
        fragments = np.concatenate(list(fragmented.chunks.queue), axis=0)
        self.assertEqual(continuous.shape, fragments.shape)
        np.testing.assert_array_equal(continuous, fragments)
        whole.close()
        fragmented.close()

    def test_large_native_audio_batches_cannot_exhaust_queue_memory(self):
        from unittest.mock import Mock, patch
        from anything_plays.libretro_audio import MAX_QUEUE_CHUNK_FRAMES
        fake = Mock()
        fake.query_devices.return_value = {"default_samplerate": 48000.0}
        with patch("anything_plays.libretro_audio.sd", fake):
            audio = AudioSink()
            audio.start(8000)
        # A 192000-frame native batch at 8kHz must not queue a full 24s
        # of PCM in one huge unbounded chunk when resampled to 48kHz.
        # Force output-rate conversion even for the common 8kHz source.
        audio._resample_step = 8000 / 48000
        chunk = np.tile(np.array([[100, -100]], dtype=np.int16), (192000, 1))
        audio.push(chunk)
        self.assertLessEqual(audio.chunks.qsize(), 32)
        self.assertTrue(all(
            len(part) <= MAX_QUEUE_CHUNK_FRAMES
            for part in list(audio.chunks.queue)
        ))
        self.assertLessEqual(
            sum(part.nbytes for part in list(audio.chunks.queue)),
            32 * MAX_QUEUE_CHUNK_FRAMES * 2 * np.dtype(np.int16).itemsize,
        )
        audio.close()

    def test_common_native_rate_is_not_needlessly_resampled(self):
        from unittest.mock import Mock, patch
        fake = Mock()
        fake.query_devices.return_value = {"default_samplerate": 48000.0}
        with patch("anything_plays.libretro_audio.sd", fake):
            audio = AudioSink()
            audio.start(44100)
        self.assertIsNone(audio._resample_step)
        self.assertEqual(audio.output_sample_rate, 44100)
        audio.close()

    def test_malformed_native_audio_count_is_ignored_before_pointer_read(self):
        from anything_plays.libretro_audio import MAX_AUDIO_BATCH_FRAMES
        audio = AudioSink()
        # Invalid lengths paired with a nonsense pointer must not even try
        # to dereference the native core's memory.
        bogus = C.c_void_p(1)
        self.assertEqual(
            audio.batch(bogus, MAX_AUDIO_BATCH_FRAMES + 1), 0
        )
        self.assertEqual(audio.batch(bogus, -1), 0)
        self.assertTrue(audio.chunks.empty())

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
