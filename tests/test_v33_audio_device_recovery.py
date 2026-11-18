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
