"""3.2 exit guard: failed profile saves require explicit player consent.

Uses a synthetic app and disposable mocks; no Tk display, camera, joystick,
game library or native emulator is opened. Existing driver-shutdown tests
separately prove cleanup remains robust after a successful save.
"""
from threading import Lock
from unittest.mock import Mock, patch
import unittest

from app import App


def fake_app():
    app = App.__new__(App)
    app.root = Mock()
    app._closing = False
    app.cancel_camera_reconnect = Mock()
    app.persist_on_exit = Mock()
    app.status = Mock()
    app.deactivate_manual = Mock()
    app.stop_controls = Mock()
    app.stop_external_emulator = Mock()
    app.close_stream_mode = Mock()
    app.close_gamepad = Mock()
    app.cap = Mock()
    app.emu = Mock()
    app.emu.lock = Lock()
    app.emu.frame = object()
    app._zone_thumbnail_cache = {"preview": object()}
    app.library_images = [object()]
    app.frame = object()
    app.game_photo = object()
    app.camera_photo = object()
    app._zone_art = object()
    return app


class ShutdownSaveGuardTests(unittest.TestCase):
    def test_failed_save_and_declined_exit_leave_app_and_devices_intact(self):
        app = fake_app()
        old_cap = app.cap
        app.persist_on_exit.side_effect = OSError("secret disk location")
        with patch("app.messagebox.askyesno", return_value=False) as prompt:
            self.assertFalse(app.close())
        prompt.assert_called_once()
        self.assertIn("Exit without saving?", prompt.call_args.args[1])
        self.assertNotIn("secret disk", str(prompt.call_args))
        self.assertFalse(app._closing)
        self.assertIs(app.cap, old_cap)
        app.root.destroy.assert_not_called()
        app.stop_controls.assert_not_called()
        app.emu.stop.assert_not_called()
        app.cancel_camera_reconnect.assert_not_called()
        app.status.set.assert_called_once()
        self.assertIn("Exit canceled", app.status.set.call_args.args[0])

        # Once the storage problem is resolved, closing again should succeed
        # without another prompt, and release all resources exactly once.
        app.persist_on_exit.side_effect = None
        with patch("app.messagebox.askyesno") as prompt:
            self.assertTrue(app.close())
        prompt.assert_not_called()
        self.assertTrue(app._closing)
        app.root.destroy.assert_called_once()
        app.emu.stop.assert_called_once()
        app.cancel_camera_reconnect.assert_called_once()

    def test_failed_save_and_explicit_approval_exit_with_normal_cleanup(self):
        app = fake_app()
        app.persist_on_exit.side_effect = OSError("simulated failed write")
        with patch("app.messagebox.askyesno", return_value=True) as prompt:
            self.assertTrue(app.close())
        prompt.assert_called_once()
        self.assertTrue(app._closing)
        app.root.destroy.assert_called_once()
        app.cap.release.assert_called_once()
        app.emu.stop.assert_called_once()

    def test_dialog_failure_does_not_silently_discard_editor(self):
        app = fake_app()
        app.persist_on_exit.side_effect = ValueError("invalid field")
        with patch("app.messagebox.askyesno",
                   side_effect=RuntimeError("destroyed window")):
            self.assertFalse(app.close())
        self.assertFalse(app._closing)
        app.root.destroy.assert_not_called()
        app.emu.stop.assert_not_called()

    def test_successful_save_does_not_show_close_prompt(self):
        app = fake_app()
        with patch("app.messagebox.askyesno") as prompt:
            self.assertTrue(app.close())
        prompt.assert_not_called()
        app.persist_on_exit.assert_called_once()
        app.root.destroy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
