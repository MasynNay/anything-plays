"""Controller driver failures never leak device paths or strand input.

All tests are isolated, use fake SDL and clipboard hooks and no hardware,
emulator, camera, GUI display, serial number or ROM.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from anything_plays.ui_gamepad import GamepadMixin


class Flag:
    def __init__(self, initial):
        self.value = initial

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def failing_app():
    app = GamepadMixin()
    app._closing = False
    app._gamepad = Mock()
    app._gamepad.api = object()
    app._gamepad.controller = object()
    app._gamepad.poll.side_effect = RuntimeError(
        "private SDL device /Users/owner/Bluetooth/serial-1234"
    )
    app._controller_capture = None
    app._controller_capture_release_pending = False
    app.gamepad_enabled = Flag(True)
    app.gamepad_status = Flag("")
    app.gamepad_diagnostics_status = Flag("")
    app.emu = Mock()
    app.root = Mock()
    app.save_preferences = Mock()
    app._refresh_gamepad_live_input = Mock()
    app.refresh_controller_artwork = Mock()
    return app


class ControllerFailureIsolationTests(unittest.TestCase):
    def test_tick_failure_releases_controller_and_redacts_native_exception(self):
        app = failing_app()
        app.gamepad_tick()
        app.emu.release_gamepad.assert_called_once()
        app._gamepad.stop.assert_called_once()
        self.assertFalse(app.gamepad_enabled.get())
        self.assertIn("Reconnect and retry", app.gamepad_status.get())
        self.assertNotIn("/Users/", app.gamepad_status.get())
        app.root.after.assert_called_once()
        self.assertEqual(app.root.after.call_args.args[0], 65)

    def test_tick_cleanup_continues_after_both_native_release_hooks_fail(self):
        app = failing_app()
        app.emu.release_gamepad.side_effect = OSError(
            "private native /dev/input"
        )
        app.emu.inputs.release_gamepad = Mock()
        app._gamepad.stop.side_effect = RuntimeError(
            "private SDL HID /home/user"
        )
        app.save_preferences.side_effect = ValueError(
            "private /Users/preferences.json"
        )
        app.gamepad_tick()
        app.emu.inputs.release_gamepad.assert_called_once()
        app._gamepad.stop.assert_called_once()
        self.assertFalse(app.gamepad_enabled.get())
        self.assertIn("unavailable", app.gamepad_status.get())
        self.assertNotIn("private", app.gamepad_status.get().lower())
        app.root.after.assert_called_once()

    def test_tk_shutdown_does_not_raise_from_pending_controller_poll(self):
        app = failing_app()
        app.root.after.side_effect = RuntimeError(
            "private Tcl command .tk/Users/profile"
        )
        app.gamepad_tick()
        self.assertIsNone(app._gamepad_tick_job)
        self.assertFalse(app.gamepad_enabled.get())

    def test_toggle_error_message_is_fixed_and_stops_sdl(self):
        app = failing_app()
        app._gamepad.start.side_effect = RuntimeError(
            "private controller driver /Users/owner"
        )
        app.toggle_gamepad()
        self.assertFalse(app.gamepad_enabled.get())
        self.assertIn("Check the connection", app.gamepad_status.get())
        self.assertNotIn("/Users/", app.gamepad_status.get())
        app.emu.release_gamepad.assert_called_once()
        app._gamepad.stop.assert_called_once()

    def test_clipboard_failure_never_displays_paths_from_driver(self):
        app = failing_app()
        app.system_key = Flag("gba")
        app._gamepad_bindings = {}
        app.armed = False
        app.emu.running = False
        app.root.clipboard_clear.side_effect = OSError(
            "private clipboard /home/user/secret-game.iso"
        )
        # Let the real report builder run so the failure is at clipboard.
        app._gamepad.physical_buttons = frozenset()
        app._gamepad.pygame = None
        self.assertFalse(app.copy_gamepad_diagnostics())
        status = app.gamepad_diagnostics_status.get()
        self.assertIn("Could not copy controller diagnostics", status)
        self.assertNotIn("/home/", status)
        self.assertNotIn("private", status)

    def test_close_does_not_abort_if_optional_controller_window_was_destroyed(self):
        app = failing_app()
        app._controller_guide_close = Mock(
            side_effect=RuntimeError("private destroyed Tcl widget")
        )
        app.emu.release_gamepad.side_effect = RuntimeError(
            "/Users/owner/native-port"
        )
        app._gamepad.stop.side_effect = OSError(
            "/home/owner/hid-driver"
        )
        app.close_gamepad()
        self.assertFalse(app._gamepad_reconnect_release_pending)
        app.emu.inputs.release_gamepad.assert_called_once()
        app._gamepad.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
