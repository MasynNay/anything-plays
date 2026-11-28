"""Native teardown survives independent final PCM and audio-sink failures."""
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from anything_plays.gba_emulator import CoreSession
from anything_plays.libretro_audio import AudioSink


class AudioShutdownTests(unittest.TestCase):
    def test_failed_final_pcm_flush_still_releases_device(self):
        audio = AudioSink()
        stream = Mock()
        audio.stream = stream
        audio.output_active = True
        audio._single_count = 1
        with patch.object(audio, "_flush_single_samples",
                          side_effect=MemoryError("private device path")):
            audio.close()
        stream.stop.assert_called_once()
        stream.close.assert_called_once()
        self.assertIsNone(audio.stream)
        self.assertFalse(audio.output_active)
        self.assertEqual(audio._single_count, 0)

    def test_failed_flush_and_stop_still_attempt_close(self):
        audio = AudioSink()
        stream = Mock()
        stream.stop.side_effect = OSError("private")
        audio.stream = stream
        with patch.object(audio, "_flush_single_samples",
                          side_effect=RuntimeError("private")):
            audio.close()
            audio.close()
        stream.stop.assert_called_once()
        stream.close.assert_called_once()

    def test_flush_failure_leaves_old_callback_silent(self):
        audio = AudioSink()
        owner = object()
        audio._callback_owner = owner
        audio.push(np.array([[100, 200]], dtype=np.int16))
        with patch.object(audio, "_flush_single_samples",
                          side_effect=RuntimeError("private")):
            audio.close()
        output = np.full((1, 2), 99, dtype=np.int16)
        audio._owned_callback(owner, output, 1, None, None)
        self.assertFalse(np.any(output))
        self.assertEqual(audio.output_callback_calls, 0)

    def test_flush_failure_diagnostic_does_not_expose_exception_text(self):
        audio = AudioSink()
        with (patch.object(audio, "_flush_single_samples",
                           side_effect=RuntimeError("PRIVATE /home/user")),
              patch("anything_plays.libretro_audio._audio_diagnostic") as log):
            audio.close()
        log.assert_called_once_with("Could not flush final audio samples")


class NativeShutdownTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.core_file = Path(tmp.name) / "fake-core.so"
        self.core_file.write_bytes(b"synthetic")
        self.stop = threading.Event()
        self.emu = SimpleNamespace(inputs=Mock(), stop_event=self.stop,
                                   armed=False, running=False, launching=True,
                                   audio_sink=None, audio_warning=None,
                                   save_warning=None)
        self.session = CoreSession.__new__(CoreSession)
        self.session.emulator = self.emu
        self.session.system = "gba"
        self.session.rom = Path(tmp.name) / "fake.gba"
        self.session.core_path = str(self.core_file)
        self.session.native = None
        self.session.audio = Mock(output_error=None)
        self.session.save_ram = None
        self.session.enable_state_resume = False
        self.session._load_game = Mock()
        self.session.persist_game_progress = Mock()
        self.native = Mock()
        self.native.run.side_effect = lambda: self.stop.set()
        self.scope = patch("anything_plays.gba_emulator.NativeCore",
                           return_value=self.native)
        self.scope.start()
        self.addCleanup(self.scope.stop)
        self.saves = patch("anything_plays.gba_emulator.SaveRAM")
        self.saves.start()
        self.addCleanup(self.saves.stop)

    def test_normal_close_orders_audio_before_core(self):
        events = []
        self.session.audio.close.side_effect = lambda: events.append("audio")
        self.native.close.side_effect = lambda: events.append("native")
        self.session.run()
        self.assertEqual(events, ["audio", "native"])
        self.assertIsNone(self.emu.audio_sink)

    def test_audio_close_failure_does_not_skip_native_close(self):
        self.session.audio.close.side_effect = MemoryError("PRIVATE /home/user")
        self.session.run()
        self.native.close.assert_called_once()
        self.assertIsNone(self.emu.audio_sink)
        self.assertEqual(self.emu.audio_warning,
                         "Audio cleanup failed. Check your audio output.")

    def test_audio_failure_does_not_mask_original_playback_error(self):
        self.native.run.side_effect = RuntimeError("original playback error")
        self.session.audio.close.side_effect = OSError("audio failure")
        with self.assertRaisesRegex(RuntimeError, "original playback error"):
            self.session.run()
        self.native.close.assert_called_once()
        self.assertIsNone(self.emu.audio_sink)

    def test_native_close_failure_is_not_hidden_by_audio_failure(self):
        self.session.audio.close.side_effect = OSError("audio failure")
        self.native.close.side_effect = RuntimeError("native close failure")
        with self.assertRaisesRegex(RuntimeError, "native close failure"):
            self.session.run()
        self.native.close.assert_called_once()

    def test_failed_native_initialization_still_closes_core(self):
        self.native.init.side_effect = RuntimeError("initialization failure")
        self.session.audio.close.side_effect = RuntimeError("audio failure")
        with self.assertRaisesRegex(RuntimeError, "initialization failure"):
            self.session.run()
        self.native.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
