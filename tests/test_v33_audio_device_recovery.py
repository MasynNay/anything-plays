"""3.3 PortAudio shutdown/recovery: no device, speakers or ROM needed."""
import io
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from anything_plays.libretro_audio import AudioSink


class AudioDeviceRecoveryTests(unittest.TestCase):
    def test_stop_failure_still_closes_native_output_stream(self):
        audio = AudioSink()
        stream = Mock()
        stream.stop.side_effect = OSError("PRIVATE audio serial /dev/dri/secret")
        audio.stream = stream
        log = io.StringIO()
        with patch("anything_plays.libretro_audio.sys.stderr", log):
            audio.close()
        stream.stop.assert_called_once_with()
        stream.close.assert_called_once_with()
        self.assertIsNone(audio.stream)
        self.assertFalse(audio.output_active)
        self.assertIn("Could not stop audio output (OSError)", log.getvalue())
        self.assertNotIn("PRIVATE", log.getvalue())
        audio.close()
        stream.stop.assert_called_once_with()
        stream.close.assert_called_once_with()

    def test_both_stop_and_close_failures_are_nonfatal(self):
        audio = AudioSink()
        stream = Mock()
        stream.stop.side_effect = RuntimeError("private speaker token")
        stream.close.side_effect = OSError("private output path /Users/owner")
        audio.stream = stream
        log = io.StringIO()
        with patch("anything_plays.libretro_audio.sys.stderr", log):
            audio.close()
        stream.close.assert_called_once_with()
        self.assertIn("Could not stop audio output (RuntimeError)", log.getvalue())
        self.assertIn("Could not close audio output (OSError)", log.getvalue())
        self.assertNotIn("private", log.getvalue())
        self.assertNotIn("/Users/", log.getvalue())
        self.assertIsNone(audio.stream)

    def test_closed_stderr_never_masks_portaudio_teardown_error(self):
        audio = AudioSink()
        stream = Mock()
        stream.stop.side_effect = OSError("private stop failure")
        stream.close.side_effect = OSError("private close failure")
        audio.stream = stream
        closed = io.StringIO()
        closed.close()
        with patch("anything_plays.libretro_audio.sys.stderr", closed):
            audio.close()
        stream.stop.assert_called_once()
        stream.close.assert_called_once()
        self.assertIsNone(audio.stream)

    def test_missing_backend_still_allows_silent_gameplay_with_closed_stderr(self):
        audio = AudioSink()
        closed = io.StringIO()
        closed.close()
        with (
            patch("anything_plays.libretro_audio.sd", None),
            patch("anything_plays.libretro_audio.sys.stderr", closed),
        ):
            audio.start(48000)
        self.assertFalse(audio.output_active)
        self.assertIn("audio backend", audio.output_error)
        audio.push(np.array([[17, -17]], dtype=np.int16))
        self.assertEqual(audio.chunks.qsize(), 1)
        audio.close()

    def test_failed_output_device_reports_status_with_closed_stderr(self):
        audio = AudioSink()
        device = Mock()
        device.query_devices.return_value = {"default_samplerate": 48000}
        device.OutputStream.side_effect = OSError(
            "PRIVATE unplugged speaker /home/owner/audio"
        )
        closed = io.StringIO()
        closed.close()
        with (
            patch("anything_plays.libretro_audio.sd", device),
            patch("anything_plays.libretro_audio.sys.stderr", closed),
        ):
            audio.start(48000)
        self.assertFalse(audio.output_active)
        self.assertEqual(audio.output_error, "No usable audio output device (OSError)")
        self.assertIsNone(audio.stream)
        audio.push(np.array([[30, 50]], dtype=np.int16))
        self.assertEqual(audio.chunks.qsize(), 1)
        audio.close()


    def test_wrong_48k_device_default_recovers_at_44k1_with_real_pcm(self):
        audio = AudioSink()
        backend = Mock()
        backend.query_devices.return_value = {"default_samplerate": 48000.0}
        streams = {}
        attempts = []

        def create_stream(*, samplerate, **kwargs):
            attempts.append(samplerate)
            stream = Mock()
            if samplerate == 48000:
                stream.start.side_effect = OSError(
                    "PRIVATE HDMI driver /Users/owner/speaker-serial"
                )
            streams[samplerate] = stream
            return stream

        backend.OutputStream.side_effect = create_stream
        with patch("anything_plays.libretro_audio.sd", backend):
            audio.start(48000)
        self.assertTrue(audio.output_active)
        self.assertIsNone(audio.output_error)
        self.assertEqual(attempts, [48000, 44100])
        streams[48000].close.assert_called_once_with()
        self.assertIs(audio.stream, streams[44100])
        self.assertEqual(audio.source_sample_rate, 48000)
        self.assertEqual(audio.output_sample_rate, 44100)
        self.assertAlmostEqual(audio._resample_step, 48000 / 44100)
        audio.push(np.tile(np.array([[1200, -1200]], dtype=np.int16),
                           (4800, 1)))
        output = np.zeros((4000, 2), dtype=np.int16)
        audio.callback(output, 4000, None, None)
        self.assertTrue(np.all(output[:, 0] == 1200))
        self.assertTrue(np.all(output[:, 1] == -1200))
        self.assertEqual(audio.delivery_snapshot()[
            "audio_output_underrun_frames"], 0)
        audio.close()
        streams[44100].stop.assert_called_once_with()
        streams[44100].close.assert_called_once_with()

    def test_wrong_44k1_default_recovers_at_48k_and_keeps_pcm(self):
        audio = AudioSink()
        backend = Mock()
        backend.query_devices.return_value = {"default_samplerate": 44100.0}
        streams = {}
        attempts = []

        def create_stream(*, samplerate, **kwargs):
            attempts.append(samplerate)
            stream = Mock()
            if samplerate == 44100:
                stream.start.side_effect = RuntimeError(
                    "PRIVATE old speaker /dev/audio-device"
                )
            streams[samplerate] = stream
            return stream

        backend.OutputStream.side_effect = create_stream
        with patch("anything_plays.libretro_audio.sd", backend):
            audio.start(44100)
        self.assertEqual(attempts, [44100, 48000])
        self.assertTrue(audio.output_active)
        self.assertEqual(audio.output_sample_rate, 48000)
        self.assertAlmostEqual(audio._resample_step, 44100 / 48000)
        streams[44100].close.assert_called_once_with()
        audio.push(np.tile(np.array([[600, -600]], dtype=np.int16),
                           (4410, 1)))
        output = np.zeros((4000, 2), dtype=np.int16)
        audio.callback(output, 4000, None, None)
        self.assertTrue(np.all(output[:, 0] == 600))
        self.assertTrue(np.all(output[:, 1] == -600))
        audio.close()

    def test_all_standard_rate_failures_stop_attempts_and_allow_silent_game(self):
        audio = AudioSink()
        backend = Mock()
        backend.query_devices.return_value = {"default_samplerate": 48000}
        attempts = []
        streams = []

        def failing_stream(*, samplerate, **kwargs):
            attempts.append(samplerate)
            stream = Mock()
            stream.start.side_effect = OSError("PRIVATE serial /home/audio")
            streams.append(stream)
            return stream

        backend.OutputStream.side_effect = failing_stream
        with patch("anything_plays.libretro_audio.sd", backend):
            audio.start(48000)
        self.assertEqual(attempts, [48000, 44100])
        self.assertEqual(len(streams), 2)
        for stream in streams:
            stream.close.assert_called_once_with()
        self.assertFalse(audio.output_active)
        self.assertIsNone(audio.stream)
        self.assertEqual(audio.output_error,
                         "No usable audio output device (OSError)")
        self.assertNotIn("PRIVATE", audio.output_error)
        audio.push(np.array([[7, -7]], dtype=np.int16))
        self.assertEqual(audio.chunks.qsize(), 1)
        audio.close()


    def test_nonfinite_native_sample_rates_fail_closed_before_audio_device_io(self):
        backend = Mock()
        invalid_rates = (
            float("nan"), float("inf"), float("-inf"),
            np.float64("nan"), np.float32("inf"),
            None, True, False, np.bool_(True), "48000",
            {}, [], object(), 0, -1, 7999.9, 192000.1,
            10 ** 1000,
        )
        with patch("anything_plays.libretro_audio.sd", backend):
            for rate in invalid_rates:
                with self.subTest(rate_type=type(rate).__name__,
                                  rate_repr=str(rate)[:30]):
                    audio = AudioSink()
                    audio.start(rate)
                    self.assertEqual(
                        audio.output_error,
                        "Emulator reported an invalid sample rate",
                    )
                    self.assertFalse(audio.output_active)
                    self.assertIsNone(audio.stream)
                    # Even a damaged native clock must not block gameplay.
                    audio.push(np.array([[17, -17]], dtype=np.int16))
                    self.assertEqual(audio.chunks.qsize(), 1)
                    audio.close()
        backend.query_devices.assert_not_called()
        backend.OutputStream.assert_not_called()

    def test_valid_finite_numpy_core_rate_still_starts_and_delivers_pcm(self):
        backend = Mock()
        backend.query_devices.return_value = {"default_samplerate": 48000.0}
        with patch("anything_plays.libretro_audio.sd", backend):
            audio = AudioSink()
            audio.start(np.float64(48000.25))
        self.assertTrue(audio.output_active)
        self.assertIsNone(audio.output_error)
        self.assertEqual(audio.source_sample_rate, 48000)
        self.assertEqual(audio.output_sample_rate, 48000)
        self.assertIsNone(audio._resample_step)
        backend.OutputStream.assert_called_once()
        audio.push(np.array([[1200, -1200], [600, -600]], dtype=np.int16))
        out = np.zeros((2, 2), dtype=np.int16)
        audio.callback(out, 2, None, None)
        self.assertEqual(out.tolist(), [[1200, -1200], [600, -600]])
        audio.close()

    def test_portaudio_status_property_error_does_not_interrupt_pcm(self):
        class BrokenStatus:
            @property
            def output_underflow(self):
                raise OSError("PRIVATE driver property /Users/owner")
        audio = AudioSink()
        audio.push(np.array([[100, -100], [50, 25]], dtype=np.int16))
        out = np.full((3, 2), 999, dtype=np.int16)
        audio.callback(out, 3, None, BrokenStatus())
        self.assertEqual(out.tolist(), [[100, -100], [50, 25], [0, 0]])
        metrics = audio.delivery_snapshot()
        self.assertEqual(metrics["audio_output_callback_calls"], 1)
        self.assertEqual(metrics["audio_output_requested_frames"], 3)
        self.assertEqual(metrics["audio_output_underrun_frames"], 1)
        self.assertEqual(metrics["audio_output_device_underflow_callbacks"], 0)

    def test_successful_native_underflow_status_still_counted(self):
        audio = AudioSink()
        out = np.full((1, 2), 77, dtype=np.int16)
        audio.callback(out, 1, None, SimpleNamespace(output_underflow=True))
        self.assertEqual(out.tolist(), [[0, 0]])
        self.assertEqual(
            audio.delivery_snapshot()["audio_output_device_underflow_callbacks"], 1
        )


if __name__ == "__main__":
    unittest.main()
