"""3.3.1: a late Tk input update must never revive a stopped native session.

Synthetic real InputBuffer with no ROM, core, camera, SDL device, Tk window,
OS keyboard hook or personal settings. Tests original facade methods.
"""
from threading import Event
from unittest import TestCase
from unittest.mock import Mock

from anything_plays.gba_emulator import Emulator
from anything_plays.libretro_input import InputBuffer


def facade():
    app = Emulator.__new__(Emulator)
    app.stop_event = Event()
    app.inputs = InputBuffer()
    app.thread = None
    app.running = False
    app.launching = False
    app.armed = False
    return app


class NativeStopInputFenceTests(TestCase):
    def test_gamepad_snapshot_is_allowed_before_stop(self):
        emu = facade()
        emu.set_gamepad_buttons(("A", "B"))
        self.assertEqual(emu.inputs.gamepad_buttons, {"A", "B"})

    def test_gamepad_pressed_after_stop_is_rejected_and_clears_old_hold(self):
        emu = facade()
        emu.set_gamepad_buttons(("A",))
        emu.stop_event.set()
        emu.set_gamepad_buttons(("A", "B"))
        self.assertEqual(emu.inputs.gamepad_buttons, set())

    def test_neutral_and_held_repeated_ticks_during_stop_remain_neutral(self):
        emu = facade()
        emu.stop_event.set()
        for sample in (("A",), ("B", "START"), (), ("A",)):
            emu.set_gamepad_buttons(sample)
            self.assertEqual(emu.inputs.gamepad_buttons, set())

    def test_native_running_flag_cannot_bypass_stop_event(self):
        emu = facade()
        emu.running = True  # Native retro_run() may be stuck.
        emu.launching = True
        emu.stop_event.set()
        emu.set_gamepad_buttons(("A",))
        emu.set_manual("B", True)
        self.assertEqual(emu.inputs.gamepad_buttons, set())
        self.assertEqual(emu.inputs.manual_buttons, set())

    def test_manual_keyboard_press_after_stop_clears_stale_latch(self):
        emu = facade()
        emu.set_manual("A", True)
        self.assertEqual(emu.inputs.manual_buttons, {"A"})
        emu.stop_event.set()
        emu.set_manual("B", True)
        self.assertEqual(emu.inputs.manual_buttons, set())

    def test_key_release_during_stop_never_rearms_manual_input(self):
        emu = facade()
        emu.stop_event.set()
        emu.set_manual("B", False)
        self.assertEqual(emu.inputs.manual_buttons, set())

    def test_stopping_gamepad_does_not_release_unrelated_manual_channel(self):
        emu = facade()
        emu.set_manual("A", True)
        emu.stop_event.set()
        emu.set_gamepad_buttons(("B",))
        self.assertEqual(emu.inputs.gamepad_buttons, set())
        self.assertEqual(emu.inputs.manual_buttons, {"A"})
        # Manual input is independently released on keyboard update/Stop.
        emu.set_manual("A", True)
        self.assertEqual(emu.inputs.manual_buttons, set())

    def test_stopping_manual_does_not_release_unrelated_gamepad_channel(self):
        emu = facade()
        emu.set_gamepad_buttons(("B",))
        emu.stop_event.set()
        emu.set_manual("A", True)
        self.assertEqual(emu.inputs.manual_buttons, set())
        self.assertEqual(emu.inputs.gamepad_buttons, {"B"})
        emu.set_gamepad_buttons(("B",))
        self.assertEqual(emu.inputs.gamepad_buttons, set())

    def test_new_session_accepts_fresh_input_after_stop_event_cleared(self):
        emu = facade()
        emu.stop_event.set()
        emu.set_manual("A", True)
        emu.set_gamepad_buttons(("B",))
        self.assertEqual(emu.inputs.manual_buttons, set())
        self.assertEqual(emu.inputs.gamepad_buttons, set())
        # This is the normal lifecycle in Emulator.start().
        emu.stop_event.clear()
        emu.set_gamepad_buttons(("B",))
        emu.set_manual("A", True)
        self.assertEqual(emu.inputs.gamepad_buttons, {"B"})
        self.assertEqual(emu.inputs.manual_buttons, {"A"})

    def test_real_facade_stop_disarms_before_late_tk_input_delivery(self):
        emu = facade()
        emu.running = True
        emu.thread = Mock()
        emu.thread.is_alive.return_value = True
        emu.set_manual("A", True)
        emu.set_gamepad_buttons(("B",))
        emu.stop()
        self.assertTrue(emu.stop_event.is_set())
        self.assertEqual(emu.inputs.manual_buttons, set())
        self.assertEqual(emu.inputs.gamepad_buttons, set())
        emu.set_gamepad_buttons(("B",))
        emu.set_manual("A", True)
        self.assertEqual(emu.inputs.gamepad_buttons, set())
        self.assertEqual(emu.inputs.manual_buttons, set())
        self.assertIsNotNone(emu.thread)
        emu.thread.join.assert_called_once_with(timeout=4)


if __name__ == "__main__":
    from unittest import main
    main()
