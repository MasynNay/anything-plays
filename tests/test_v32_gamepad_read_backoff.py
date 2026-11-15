"""3.2 regression: a broken USB/Bluetooth button read must not spin at 65 ms.

All pads and clocks below are synthetic. This tests input release and
reconnection scheduling; it does not certify any physical controller.
"""
import unittest
from types import SimpleNamespace

from anything_plays.gamepad import GamepadReader, SCAN_INTERVAL


class FakePad:
    def __init__(self, *, fail_on=None, pressed=False):
        self.fail_on = fail_on
        self.pressed = pressed
        self.closed = False
        self.closes = 0

    def attached(self):
        return not self.closed

    def get_button(self, code):
        if self.fail_on == "button":
            raise OSError("controller removed while reading buttons")
        return self.pressed and code == "CONTROLLER_BUTTON_A"

    def get_axis(self, code):
        if self.fail_on == "axis":
            raise RuntimeError("controller removed while reading axis")
        return 0

    def quit(self):
        self.closed = True
        self.closes += 1


class FakeAPI:
    def __init__(self, replacement):
        self.replacement = replacement
        self.opens = 0
        self.scans = 0

    def get_count(self):
        self.scans += 1
        return 1

    def is_controller(self, index):
        return index == 0

    def Controller(self, index):
        self.opens += 1
        return self.replacement

    def name_forindex(self, index):
        return "Recovered gamepad"


class ReadFailureBackoffTests(unittest.TestCase):
    def make_reader(self, failing_pad, healthy_pad=None):
        now = [0.0]
        reader = GamepadReader(clock=lambda: now[0])
        reader.controller = failing_pad
        reader.name = "Original gamepad"
        reader.physical_buttons = frozenset({"A"})
        reader._active_axes = frozenset({"LEFT_STICK_RIGHT"})
        reader._active_triggers = frozenset({"LEFT_TRIGGER"})
        reader.api = FakeAPI(healthy_pad or FakePad(pressed=True))
        reader.pygame = SimpleNamespace(event=SimpleNamespace(
            pump=lambda: None, get=lambda: []
        ))
        reader._sdl_constant = lambda name: name
        return reader, now

    def assert_disarmed(self, reader, failing_pad):
        self.assertIsNone(reader.controller)
        self.assertEqual(reader.physical_buttons, frozenset())
        self.assertEqual(reader._active_axes, frozenset())
        self.assertEqual(reader._active_triggers, frozenset())
        self.assertEqual(failing_pad.closes, 1)

    def test_failed_button_read_releases_all_inputs_and_limits_rescans(self):
        bad = FakePad(fail_on="button")
        good = FakePad(pressed=True)
        reader, now = self.make_reader(bad, good)
        buttons, status = reader.poll("gba")
        self.assertFalse(buttons)
        self.assertIn("Retrying", status)
        self.assert_disarmed(reader, bad)
        self.assertEqual(reader.retry_after, SCAN_INTERVAL)

        # Tk calls the reader roughly 15 times per second; NONE of these
        # callbacks should reopen a faulty native device while cooling down.
        for step in range(1, 15):
            now[0] = step * 0.1
            self.assertEqual(reader.poll("gba")[0], frozenset())
        self.assertEqual(reader.api.opens, 0)
        self.assertEqual(reader.api.scans, 0)

        now[0] = SCAN_INTERVAL
        buttons, status = reader.poll("gba")
        self.assertEqual(buttons, {"A"})
        self.assertEqual(reader.physical_buttons, {"A"})
        self.assertEqual(reader.api.opens, 1)
        self.assertIn("connected", status)
        self.assertEqual(reader.retry_after, float("-inf"))

    def test_axis_failure_uses_same_backoff_without_retaining_hysteresis(self):
        bad = FakePad(fail_on="axis", pressed=True)
        reader, now = self.make_reader(bad)
        buttons, status = reader.poll("gba")
        self.assertEqual(buttons, frozenset())
        self.assertIn("Retrying", status)
        self.assert_disarmed(reader, bad)
        self.assertEqual(reader.retry_after, SCAN_INTERVAL)

        now[0] = 0.5
        self.assertEqual(reader.poll("gba")[0], frozenset())
        self.assertEqual(reader.api.opens, 0)

    def test_manual_rescan_overrides_backoff_and_uses_new_device(self):
        bad = FakePad(fail_on="button")
        good = FakePad(pressed=True)
        reader, now = self.make_reader(bad, good)
        reader.poll("gba")
        now[0] = 0.2
        reader.refresh()
        self.assertEqual(reader.retry_after, float("-inf"))
        self.assertEqual(reader.last_scan, float("-inf"))
        self.assertEqual(reader.poll("gba")[0], {"A"})
        self.assertEqual(reader.api.opens, 1)

    def test_good_pad_read_does_not_enter_backoff(self):
        good = FakePad(pressed=True)
        reader, now = self.make_reader(good)
        for tick in range(4):
            now[0] = tick * 0.1
            self.assertEqual(reader.poll("gba")[0], {"A"})
        self.assertEqual(reader.retry_after, float("-inf"))
        self.assertEqual(good.closes, 0)
        self.assertEqual(reader.api.opens, 0)


if __name__ == "__main__":
    unittest.main()
