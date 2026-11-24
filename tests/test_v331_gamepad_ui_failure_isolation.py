"""3.3.1: a damaged optional controller UI must not disable gamepad input.

Headless synthetic SDL snapshots, native input stubs, and Tk status widgets.
No game ROM, camera, controller, keyboard hook, settings file, or window.
"""
import unittest
from unittest.mock import Mock

from anything_plays.ui_gamepad import GamepadMixin


class Flag:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class BrokenStatus(Flag):
    def __init__(self, *, break_get=False, break_set=False):
        super().__init__("")
        self.break_get = break_get
        self.break_set = break_set

    def get(self):
        if self.break_get:
            raise RuntimeError("PRIVATE destroyed Tk status label")
        return super().get()

    def set(self, value):
        if self.break_set:
            raise RuntimeError("PRIVATE destroyed Tk status label")
        super().set(value)


def app_with_active_pad():
    app = GamepadMixin()
    app._closing = False
    app.root = Mock()
    app.root.focus_get.return_value = object()
    app.root.after.return_value = "synthetic-next-poll"
    app.gamepad_enabled = Flag(True)
    app.gamepad_status = Flag("")
    app.system_key = Flag("gba")
    app._gamepad_bindings = {"gba": {}}
    app._gamepad = Mock()
    app._gamepad.api = object()
    app._gamepad.controller = object()
    app._gamepad.physical_buttons = frozenset({"A"})
    app._gamepad.poll.return_value = (
        frozenset({"A"}), "Local gamepad connected"
    )
    app.emu = Mock()
    app.emu.running = True
    app.uses_embedded_emulator = lambda: True
    app._controller_capture_tick = Mock()
    app._cancel_controller_capture = Mock()
    app._refresh_gamepad_live_input = Mock()
    app.refresh_controller_artwork = Mock()
    app.save_preferences = Mock()
    return app


class OptionalUIIsolationTests(unittest.TestCase):
    def assert_healthy_tick(self, app):
        self.assertTrue(app.gamepad_enabled.get())
        app._gamepad.stop.assert_not_called()
        app.emu.release_gamepad.assert_not_called()
        app.emu.set_gamepad_buttons.assert_called_once_with(
            frozenset({"A"})
        )
        app.save_preferences.assert_not_called()
        app.root.after.assert_called_once_with(65, app.gamepad_tick)

    def test_broken_controller_artwork_cannot_disable_physical_input(self):
        app = app_with_active_pad()
        app.refresh_controller_artwork.side_effect = RuntimeError(
            "PRIVATE destroyed Tk canvas /Users/person"
        )
        app.gamepad_tick()
        self.assert_healthy_tick(app)
        self.assertEqual(
            app._last_controller_art_snapshot,
            (True, frozenset({"A"})),
        )
        self.assertEqual(app.gamepad_status.get(), "Local gamepad connected")

    def test_no_repeated_artwork_faults_on_steady_input_snapshot(self):
        app = app_with_active_pad()
        app.refresh_controller_artwork.side_effect = OSError(
            "PRIVATE canvas backend"
        )
        app.gamepad_tick()
        app.emu.set_gamepad_buttons.reset_mock()
        app.root.after.reset_mock()
        app.gamepad_tick()
        self.assert_healthy_tick(app)
        app.refresh_controller_artwork.assert_called_once()

    def test_new_physical_press_retries_artwork_after_old_failure(self):
        app = app_with_active_pad()
        app.refresh_controller_artwork.side_effect = RuntimeError("old canvas")
        app.gamepad_tick()
        app._gamepad.physical_buttons = frozenset({"B"})
        app._gamepad.poll.return_value = (
            frozenset({"B"}), "Local gamepad connected"
        )
        app.gamepad_tick()
        self.assertEqual(app.refresh_controller_artwork.call_count, 2)
        self.assertEqual(
            app._last_controller_art_snapshot,
            (True, frozenset({"B"})),
        )
        self.assertTrue(app.gamepad_enabled.get())
        app.save_preferences.assert_not_called()

    def test_failed_live_input_label_does_not_turn_off_controller(self):
        app = app_with_active_pad()
        app._refresh_gamepad_live_input.side_effect = RuntimeError(
            "PRIVATE removed widget"
        )
        app.gamepad_tick()
        self.assert_healthy_tick(app)
        app.refresh_controller_artwork.assert_called_once()

    def test_destroyed_status_get_is_not_an_sdl_failure(self):
        app = app_with_active_pad()
        app.gamepad_status = BrokenStatus(break_get=True)
        app.gamepad_tick()
        self.assert_healthy_tick(app)
        app.refresh_controller_artwork.assert_called_once()

    def test_destroyed_status_set_is_not_an_sdl_failure(self):
        app = app_with_active_pad()
        app.gamepad_status = BrokenStatus(break_set=True)
        app.gamepad_tick()
        self.assert_healthy_tick(app)
        app.refresh_controller_artwork.assert_called_once()

    def test_multiple_optional_widget_failures_still_poll_controller(self):
        app = app_with_active_pad()
        app.gamepad_status = BrokenStatus(break_get=True)
        app._refresh_gamepad_live_input.side_effect = RuntimeError(
            "PRIVATE text unavailable"
        )
        app.refresh_controller_artwork.side_effect = RuntimeError(
            "PRIVATE art unavailable"
        )
        app.gamepad_tick()
        self.assert_healthy_tick(app)

    def test_real_sdl_poll_failure_still_disarms_and_disables_reader(self):
        app = app_with_active_pad()
        app._gamepad.poll.side_effect = OSError("physical SDL unplug")
        app.gamepad_tick()
        self.assertFalse(app.gamepad_enabled.get())
        app._gamepad.stop.assert_called_once()
        app.emu.release_gamepad.assert_called_once()
        app.save_preferences.assert_called_once()
        self.assertIn("Controller disconnected", app.gamepad_status.get())
        app.emu.set_gamepad_buttons.assert_not_called()
        app.root.after.assert_called_once_with(65, app.gamepad_tick)


if __name__ == "__main__":
    unittest.main()
