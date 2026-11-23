"""3.3.1 explicit gamepad Disable/Rescan must fail safe during SDL teardown.

All objects are synthetic; no SDL, input device, Tk window, ROM or native core.
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


def app_with_controller(*, enabled=True):
    app = GamepadMixin()
    app._gamepad = Mock()
    app.gamepad_enabled = Flag(enabled)
    app.gamepad_status = Flag("")
    app._gamepad_last_controller = object()
    app._gamepad_seen_controller = True
    app._gamepad_reconnect_release_pending = False
    app._gamepad_game_resume_release_pending = False
    app._controller_capture = None
    app._controller_capture_release_pending = False
    app.emu = Mock()
    app.save_preferences = Mock()
    app._refresh_gamepad_live_input = Mock()
    app.refresh_controller_artwork = Mock()
    return app


class ExplicitGamepadCleanupTests(unittest.TestCase):
    def test_disable_is_safe_when_both_native_release_hooks_raise(self):
        app = app_with_controller(enabled=False)
        app.emu.release_gamepad.side_effect = OSError(
            "PRIVATE USB input /dev/input/serial"
        )
        app._gamepad.stop.side_effect = RuntimeError(
            "PRIVATE SDL native destructor"
        )
        app.toggle_gamepad()
        app.emu.inputs.release_gamepad.assert_called_once()
        app._gamepad.stop.assert_called_once()
        self.assertEqual(app.gamepad_status.get(), "Controller disabled")
        self.assertFalse(app.gamepad_enabled.get())
        self.assertIsNone(app._gamepad_last_controller)
        self.assertFalse(app._gamepad_seen_controller)
        self.assertFalse(app._gamepad_reconnect_release_pending)
        app.save_preferences.assert_called_once()
        self.assertNotIn("PRIVATE", app.gamepad_status.get())

    def test_normal_disable_stops_reader_and_releases_gamepad_immediately(self):
        app = app_with_controller(enabled=False)
        app.toggle_gamepad()
        app.emu.release_gamepad.assert_called_once()
        app.emu.inputs.release_gamepad.assert_not_called()
        app._gamepad.stop.assert_called_once()
        self.assertEqual(app.gamepad_status.get(), "Controller disabled")

    def test_rescan_sets_release_gate_and_clears_native_input(self):
        app = app_with_controller()
        app.refresh_gamepad()
        app.emu.release_gamepad.assert_called_once()
        app._gamepad.refresh.assert_called_once()
        app._gamepad.stop.assert_not_called()
        self.assertTrue(app._gamepad_reconnect_release_pending)
        self.assertTrue(app._gamepad_seen_controller)
        self.assertIsNone(app._gamepad_last_controller)
        self.assertIn("Looking for a controller", app.gamepad_status.get())
        app.save_preferences.assert_not_called()

    def test_rescan_survives_failed_native_release_using_input_buffer(self):
        app = app_with_controller()
        app.emu.release_gamepad.side_effect = OSError("PRIVATE detached core")
        app.refresh_gamepad()
        app.emu.inputs.release_gamepad.assert_called_once()
        app._gamepad.refresh.assert_called_once()
        self.assertTrue(app.gamepad_enabled.get())
        self.assertTrue(app._gamepad_reconnect_release_pending)
        app.save_preferences.assert_not_called()
        self.assertNotIn("PRIVATE", app.gamepad_status.get())

    def test_failed_native_rescan_revokes_old_device_and_disables_setting(self):
        app = app_with_controller()
        app._gamepad.refresh.side_effect = OSError(
            "PRIVATE Bluetooth hardware address /Users/owner"
        )
        app.refresh_gamepad()
        app._gamepad.stop.assert_called_once()
        self.assertFalse(app.gamepad_enabled.get())
        self.assertFalse(app._gamepad_reconnect_release_pending)
        self.assertIn("Controller unavailable", app.gamepad_status.get())
        self.assertNotIn("PRIVATE", app.gamepad_status.get())
        app.emu.release_gamepad.assert_called()
        app.save_preferences.assert_called_once()
        app._refresh_gamepad_live_input.assert_called_once()
        app.refresh_controller_artwork.assert_called_once()

    def test_destroyed_remap_status_does_not_prevent_rescan_release(self):
        app = app_with_controller()
        status = Mock()
        status.set.side_effect = RuntimeError("PRIVATE destroyed Tk widget")
        app._controller_capture = {"status": status}
        app.refresh_gamepad()
        self.assertIsNone(app._controller_capture)
        self.assertTrue(app._controller_capture_release_pending)
        app.emu.release_gamepad.assert_called_once()
        app._gamepad.refresh.assert_called_once()
        self.assertNotIn("PRIVATE", app.gamepad_status.get())

    def test_rescan_when_disabled_never_opens_sdl(self):
        app = app_with_controller(enabled=False)
        app.refresh_gamepad()
        app.emu.release_gamepad.assert_called_once()
        app._gamepad.refresh.assert_not_called()
        app._gamepad.stop.assert_not_called()
        self.assertFalse(app._gamepad_reconnect_release_pending)
        self.assertEqual(
            app.gamepad_status.get(), "Enable controller input to scan"
        )


if __name__ == "__main__":
    unittest.main()
