"""3.1.1 SDL enumeration must isolate faulty devices, not lose healthy pads.

These tests inject a broken USB index and native handle failures without
claiming real controller pairing or needing a live ROM or SDL installation.
"""
from __future__ import annotations

from types import SimpleNamespace
import unittest

from anything_plays.gamepad import GamepadReader


class FakePad:
    def __init__(self, *, pressed=False, attached=True, attach_error=False,
                 close_error=False):
        self.pressed = pressed
        self.present = attached
        self.attach_error = attach_error
        self.close_error = close_error
        self.closes = 0

    def attached(self):
        if self.attach_error:
            raise RuntimeError("USB removed during attached()")
        return self.present

    def get_button(self, code):
        return self.pressed and code == "CONTROLLER_BUTTON_A"

    def get_axis(self, code):
        return 0

    def quit(self):
        self.closes += 1
        if self.close_error:
            raise OSError("SDL already closed this handle")


class FakeSDL:
    def __init__(self, devices, *, probe_errors=(), open_errors=(),
                 name_errors=()):
        self.devices = list(devices)
        self.probe_errors = set(probe_errors)
        self.open_errors = set(open_errors)
        self.name_errors = set(name_errors)
        self.probed = []
        self.opened = []
        self.closed = False

    def get_count(self):
        return len(self.devices)

    def is_controller(self, index):
        self.probed.append(index)
        if index in self.probe_errors:
            raise RuntimeError("bad controller index")
        return True

    def Controller(self, index):
        self.opened.append(index)
        if index in self.open_errors:
            raise OSError("device disappeared during Controller()")
        return self.devices[index]

    def name_forindex(self, index):
        if index in self.name_errors:
            raise RuntimeError("USB label disappeared")
        return f"Pad {index}"

    def quit(self):
        self.closed = True


def reader_for(api, now):
    reader = GamepadReader(clock=lambda: now[0])
    reader.api = api
    reader.pygame = SimpleNamespace(
        event=SimpleNamespace(pump=lambda: None, get=lambda: [])
    )
    # Only the SDL sampler needs SDL constant lookup. Real pygame imports
    # would defeat the purpose of the headless native-error unit tests.
    reader._sdl_constant = lambda name: name
    return reader


class BadDeviceIsolationTests(unittest.TestCase):
    def test_bad_probe_and_failed_attach_handle_do_not_hide_third_pad(self):
        failed = FakePad(attach_error=True, close_error=True)
        good = FakePad(pressed=True)
        sdl = FakeSDL([None, failed, good], probe_errors={0})
        reader = reader_for(sdl, [0.0])

        held, status = reader.poll("gba")
        self.assertEqual(held, frozenset({"A"}))
        self.assertEqual(status, "Pad 2 connected")
        self.assertEqual(reader.physical_buttons, frozenset({"A"}))
        self.assertEqual(sdl.probed, [0, 1, 2])
        self.assertEqual(sdl.opened, [1, 2])
        self.assertEqual(failed.closes, 1)
        self.assertEqual(good.closes, 0)
        self.assertIs(reader.controller, good)
        reader.refresh()
        self.assertEqual(good.closes, 1)
        self.assertEqual(reader.physical_buttons, frozenset())

    def test_unattached_and_missing_handle_are_released_without_breaking_scan(self):
        stale = FakePad(attached=False, close_error=True)
        good = FakePad(pressed=True)
        sdl = FakeSDL([stale, None, good], name_errors={2})
        reader = reader_for(sdl, [0.0])

        held, status = reader.poll("gba")
        self.assertEqual(held, frozenset({"A"}))
        self.assertEqual(status, "Gamepad connected")
        self.assertEqual(stale.closes, 1)
        self.assertEqual(good.closes, 0)
        self.assertEqual(sdl.probed, [0, 1, 2])
        reader.refresh()
        self.assertEqual(good.closes, 1)

    def test_constructor_exception_is_isolated_to_one_index(self):
        working = FakePad(pressed=True)
        api = FakeSDL([None, working], open_errors={0})
        reader = reader_for(api, [0.0])
        self.assertEqual(reader.poll("gba")[0], frozenset({"A"}))
        self.assertEqual(api.opened, [0, 1])
        self.assertEqual(reader.name, "Pad 1")

    def test_all_devices_disappear_clears_previous_held_inputs(self):
        now = [0.0]
        original = FakePad(pressed=True)
        api = FakeSDL([original])
        reader = reader_for(api, now)
        self.assertEqual(reader.poll("gba")[0], frozenset({"A"}))

        original.present = False
        now[0] = 2.0
        api.devices = [None, None]
        api.probe_errors = {0}
        api.open_errors = {1}
        held, status = reader.poll("gba")
        self.assertEqual(held, frozenset())
        self.assertIn("No compatible controller", status)
        self.assertEqual(reader.physical_buttons, frozenset())
        self.assertEqual(reader._active_axes, frozenset())
        self.assertEqual(reader._active_triggers, frozenset())
        self.assertEqual(original.closes, 1)
        self.assertIsNone(reader.controller)
        self.assertEqual(api.probed[-2:], [0, 1])

    def test_normal_first_pad_stops_scan_at_first_healthy_controller(self):
        first = FakePad(pressed=True)
        second = FakePad(pressed=True)
        api = FakeSDL([first, second])
        reader = reader_for(api, [0.0])
        held, status = reader.poll("gba")
        self.assertEqual(held, frozenset({"A"}))
        self.assertEqual(status, "Pad 0 connected")
        self.assertEqual(api.probed, [0])
        self.assertEqual(api.opened, [0])
        self.assertEqual(first.closes, 0)
        self.assertEqual(second.closes, 0)


if __name__ == "__main__":
    unittest.main()
