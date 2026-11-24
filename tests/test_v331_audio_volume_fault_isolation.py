"""3.3.1: changing local volume must survive optional audio-device failures.

No actual audio device, native ROM/core, microphone, or private file is used.
Only fake AudioSink instances and pure numeric inputs are exercised.
"""
import math
import unittest
from unittest.mock import Mock

from anything_plays.gba_emulator import Emulator


def fake_emulator(sink=None):
    emu = object.__new__(Emulator)
    emu.volume = 0.35
    emu.audio_sink = sink
    emu.audio_warning = None
    return emu


class PoisonFloat:
    def __float__(self):
        raise RuntimeError("PRIVATE device /Users/person/audio")


class AudioVolumeFailureTests(unittest.TestCase):
    def test_live_volume_reaches_healthy_audio_sink(self):
        sink = Mock()
        emu = fake_emulator(sink)
        emu.set_volume(0.67)
        self.assertEqual(emu.volume, 0.67)
        sink.set_volume.assert_called_once_with(0.67)
        self.assertIsNone(emu.audio_warning)

    def test_device_unplug_during_volume_change_does_not_crash(self):
        sink = Mock()
        sink.set_volume.side_effect = OSError(
            "PRIVATE /Users/person/USB audio interface serial 123"
        )
        emu = fake_emulator(sink)
        emu.set_volume(0.82)
        self.assertEqual(emu.volume, 0.82)
        sink.set_volume.assert_called_once_with(0.82)
        self.assertIn("Volume adjustment unavailable", emu.audio_warning)
        self.assertNotIn("PRIVATE", emu.audio_warning)
        self.assertNotIn("/Users/", emu.audio_warning)
        self.assertNotIn("123", emu.audio_warning)

    def test_new_audio_sink_receives_saved_gain_after_recovery(self):
        lost = Mock()
        lost.set_volume.side_effect = OSError("PRIVATE device disconnected")
        emu = fake_emulator(lost)
        emu.set_volume(0.42)
        self.assertEqual(emu.volume, 0.42)
        recovered = Mock()
        emu.audio_sink = recovered
        emu.audio_warning = None
        emu.set_volume(emu.volume)
        recovered.set_volume.assert_called_once_with(0.42)
        self.assertIsNone(emu.audio_warning)

    def test_sink_error_does_not_change_other_native_session_state(self):
        failed = Mock()
        failed.set_volume.side_effect = RuntimeError("broken native wrapper")
        emu = fake_emulator(failed)
        emu.running = True
        emu.armed = True
        emu.current_rom = "/synthetic/previous.gba"
        emu.set_volume(0.13)
        self.assertTrue(emu.running)
        self.assertTrue(emu.armed)
        self.assertEqual(emu.current_rom, "/synthetic/previous.gba")
        self.assertEqual(emu.volume, 0.13)

    def test_out_of_range_inputs_stay_bounded_on_native_sink(self):
        sink = Mock()
        emu = fake_emulator(sink)
        emu.set_volume(-100.0)
        self.assertEqual(emu.volume, 0.0)
        emu.set_volume(100.0)
        self.assertEqual(emu.volume, 1.0)
        self.assertEqual(
            [call.args[0] for call in sink.set_volume.call_args_list],
            [0.0, 1.0],
        )

    def test_nonfinite_input_never_reaches_native_output(self):
        sink = Mock()
        emu = fake_emulator(sink)
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                emu.set_volume(value)
                self.assertTrue(math.isfinite(emu.volume))
                self.assertEqual(emu.volume, 0.35)
        self.assertEqual(sink.set_volume.call_count, 3)

    def test_bad_numeric_wrapper_cannot_abort_audio_control(self):
        sink = Mock()
        emu = fake_emulator(sink)
        emu.set_volume(PoisonFloat())
        self.assertEqual(emu.volume, 0.35)
        sink.set_volume.assert_called_once_with(0.35)
        self.assertIsNone(emu.audio_warning)

    def test_no_audio_sink_still_saves_volume_for_later_session(self):
        emu = fake_emulator()
        emu.set_volume("0.24")
        self.assertEqual(emu.volume, 0.24)
        self.assertIsNone(emu.audio_warning)

    def test_audio_warning_overrides_no_other_input_state(self):
        sink = Mock()
        sink.set_volume.side_effect = RuntimeError(
            "PRIVATE ALSA /home/owner/hardware"
        )
        emu = fake_emulator(sink)
        emu.running = False
        emu.set_volume(0.5)
        self.assertEqual(emu.audio_warning, (
            "Volume adjustment unavailable. "
            "Check your audio output and try again."
        ))
        self.assertFalse(emu.running)


if __name__ == "__main__":
    unittest.main()
