"""3.3.1 SDL clock failures must never disable a healthy controller.

Synthetic SDL, Tk, gamepad and clock adapters only. No physical controller,
hardware input, emulator, webcam, OBS or user data is touched.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from anything_plays.gamepad import GamepadReader, SCAN_INTERVAL
from anything_plays.ui_gamepad import GamepadMixin


class Pad:
    def __init__(self, *, pressed=False, fail_read=False):
        self.pressed = pressed
        self.fail_read = fail_read
        self.closed = False
        self.close_count = 0

    def attached(self):
        return not self.closed

    def get_button(self, code):
        if self.fail_read:
            raise OSError("PRIVATE controller /Users/owner/device")
        return self.pressed and code == "CONTROLLER_BUTTON_A"

    def get_axis(self, _code):
        if self.fail_read:
            raise OSError("PRIVATE axis driver /dev/input")
        return 0

    def quit(self):
        self.close_count += 1
        self.closed = True


class API:
    def __init__(self, pad):
        self.pad = pad
        self.opens = 0
        self.scans = 0

    def get_count(self):
        self.scans += 1
        return 1

    def is_controller(self, index):
        return index == 0

    def Controller(self, index):
        self.opens += 1
        return self.pad

    def name_forindex(self, _index):
        return "Synthetic pad"

    def quit(self):
        pass


def reader_for(clock, pad=None, *, already_connected=True):
    pad = pad or Pad(pressed=True)
    reader = GamepadReader(clock=clock)
    reader.api = API(pad)
    reader.pygame = SimpleNamespace(event=SimpleNamespace(
        pump=Mock(), get=Mock(return_value=[])
    ))
    reader._sdl_constant = lambda name: name
    if already_connected:
        reader.controller = pad
        reader.name = "Synthetic pad"
    return reader, pad


class Flag:
    def __init__(self, initial):
        self.value = initial

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class GamepadClockRecoveryTests(unittest.TestCase):
    def test_invalid_clock_values_release_held_input_without_device_teardown(self):
        values = (None, float("nan"), float("inf"), -1, True, "clock",
                  10**500)
        for value in values:
            with self.subTest(value=str(value)[:40]):
                reader, pad = reader_for(lambda: value)
                reader.physical_buttons = frozenset({"A"})
                reader._active_axes = frozenset({"LEFT_STICK_RIGHT"})
                reader._active_triggers = frozenset({"LEFT_TRIGGER"})
                held, status = reader.poll("gba")
                self.assertEqual(held, frozenset())
                self.assertEqual(reader.physical_buttons, frozenset())
                self.assertEqual(reader._active_axes, frozenset())
                self.assertEqual(reader._active_triggers, frozenset())
                self.assertTrue(reader._clock_release_pending)
                self.assertIn("Retrying", status)
                self.assertIs(reader.controller, pad)
                self.assertEqual(pad.close_count, 0)
                reader.pygame.event.pump.assert_not_called()

    def test_clock_exception_does_not_surface_private_exception(self):
        def broken():
            raise RuntimeError("PRIVATE /Users/person/gamecube.iso")
        reader, pad = reader_for(broken)
        held, status = reader.poll("gba")
        self.assertFalse(held)
        self.assertIn("timing unavailable", status)
        self.assertNotIn("PRIVATE", status)
        self.assertNotIn("/Users/", status)
        self.assertIs(reader.controller, pad)

    def test_clock_is_sampled_once_per_normal_poll_even_on_sdl_failure(self):
        calls = [0]

        def read_clock():
            calls[0] += 1
            if calls[0] != 1:
                raise OSError("clock called a second time")
            return 10.0

        reader, pad = reader_for(read_clock, Pad(fail_read=True))
        held, status = reader.poll("gba")
        self.assertEqual(held, frozenset())
        self.assertIn("Retrying", status)
        self.assertEqual(calls[0], 1)
        self.assertTrue(pad.closed)
        self.assertEqual(reader.retry_after, 10.0 + SCAN_INTERVAL)

    def test_outage_keeps_physically_held_button_blocked_until_neutral(self):
        now = [10.0]
        reader, pad = reader_for(lambda: now[0])
        self.assertEqual(reader.poll("gba")[0], frozenset({"A"}))

        now[0] = float("nan")
        self.assertEqual(reader.poll("gba")[0], frozenset())
        self.assertTrue(reader._clock_release_pending)
        now[0] = 11.0
        held, status = reader.poll("gba")
        self.assertEqual(held, frozenset())
        self.assertIn("Release controller inputs", status)
        self.assertEqual(reader.physical_buttons, frozenset({"A"}))
        pad.pressed = False
        self.assertFalse(reader.poll("gba")[0])
        self.assertFalse(reader._clock_release_pending)
        pad.pressed = True
        self.assertEqual(reader.poll("gba")[0], frozenset({"A"}))

    def test_backward_clock_resets_future_retry_without_replaying_held_input(self):
        now = [100.0]
        old = Pad(pressed=True)
        new = Pad(pressed=True)
        reader, _ = reader_for(lambda: now[0], old)
        self.assertEqual(reader.poll("gba")[0], frozenset({"A"}))
        reader.pygame.event.pump.side_effect = OSError("SDL unplugged")
        now[0] = 101.0
        self.assertEqual(reader.poll("gba")[0], frozenset())
        self.assertEqual(reader.retry_after, 101.0 + SCAN_INTERVAL)
        self.assertTrue(old.closed)

        reader.pygame.event.pump.side_effect = None
        reader.api.pad = new
        now[0] = 0.0
        held, status = reader.poll("gba")
        self.assertFalse(held)
        self.assertIn("Release controller inputs", status)
        self.assertEqual(reader.retry_after, float("-inf"))
        self.assertEqual(reader.api.opens, 1)
        new.pressed = False
        now[0] = 0.1
        self.assertFalse(reader.poll("gba")[0])
        new.pressed = True
        now[0] = 0.2
        self.assertEqual(reader.poll("gba")[0], frozenset({"A"}))

    def test_manual_refresh_and_shutdown_clear_clock_recovery_latches(self):
        reader, _ = reader_for(lambda: None)
        reader.poll("gba")
        self.assertTrue(reader._clock_release_pending)
        reader.refresh()
        self.assertFalse(reader._clock_release_pending)
        self.assertIsNone(reader._last_valid_clock)
        self.assertEqual(reader.retry_after, float("-inf"))
        reader.poll("gba")
        reader.stop()
        self.assertFalse(reader._clock_release_pending)
        self.assertIsNone(reader._last_valid_clock)
        self.assertIsNone(reader.api)

    def test_ui_tick_does_not_persistently_disable_controller_on_clock_outage(self):
        now = [1.0]
        reader, pad = reader_for(lambda: now[0])
        class Harness(GamepadMixin):
            pass
        app = Harness()
        app._closing = False
        app._gamepad = reader
        app.gamepad_enabled = Flag(True)
        app.system_key = Flag("gba")
        app._gamepad_bindings = {}
        app.gamepad_status = Flag("")
        app._controller_capture = None
        app._controller_capture_release_pending = False
        app.root = Mock()
        app.root.focus_get.return_value = object()
        app.emu = Mock()
        app.emu.running = True
        app.uses_embedded_emulator = Mock(return_value=True)
        app.refresh_controller_artwork = Mock()
        app._refresh_gamepad_live_input = Mock()
        app.save_preferences = Mock()
        app.gamepad_tick()
        app.emu.set_gamepad_buttons.assert_called_with(frozenset({"A"}))
        now[0] = None
        app.gamepad_tick()
        app.emu.set_gamepad_buttons.assert_called_with(frozenset())
        self.assertTrue(app.gamepad_enabled.get())
        self.assertIs(reader.controller, pad)
        self.assertIn("timing unavailable", app.gamepad_status.get())
        app.save_preferences.assert_not_called()
        now[0] = 2.0
        app.gamepad_tick()
        app.emu.set_gamepad_buttons.assert_called_with(frozenset())
        pad.pressed = False
        app.gamepad_tick()
        pad.pressed = True
        app.gamepad_tick()
        app.emu.set_gamepad_buttons.assert_called_with(frozenset({"A"}))
        self.assertTrue(app.gamepad_enabled.get())
        self.assertFalse(reader._clock_release_pending)


if __name__ == "__main__":
    unittest.main()
