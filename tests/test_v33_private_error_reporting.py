"""3.3: driver error messages must never leak local paths into Tk status."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from anything_plays.ui_gameplay import GameplayMixin, safe_gui_failure_class


class PrivateErrorMessageTests(unittest.TestCase):
    def test_only_fixed_error_categories_are_exposed(self):
        for error in (
            OSError("/home/owner/private-camera serial 123"),
            RuntimeError("/Users/owner/ROMs/private-game.iso"),
            MemoryError("private graphics allocation"),
            ValueError("usb device ID SECRET-DEVICE"),
        ):
            with self.subTest(category=type(error).__name__):
                category = safe_gui_failure_class(error)
                self.assertEqual(category, type(error).__name__)
                self.assertNotIn("/", category)
                self.assertNotIn("private", category)
        class PrivateDeviceName(Exception):
            pass
        self.assertEqual(
            safe_gui_failure_class(PrivateDeviceName("secret-serial")),
            "UnexpectedError",
        )

    def test_camera_tracking_error_redacts_driver_details_and_reschedules(self):
        app = GameplayMixin()
        app._closing = False
        app.cap = object()
        app.frame = None
        app.reference_image = False
        app.stop_camera = Mock()
        app.stop_controls = Mock()
        app.status = Mock()
        app.root = Mock()
        with patch.object(
            GameplayMixin, "_camera_is_open",
            side_effect=(
                RuntimeError("USB serial XYZ /Users/owner/private-frame"),
                False,
            ),
        ):
            app.tick()
        message = app.status.set.call_args.args[0]
        self.assertIn("Tracking error (RuntimeError)", message)
        for secret in ("/Users/", "XYZ", "USB serial", "private-frame"):
            self.assertNotIn(secret, message)
        app.stop_controls.assert_called_once()
        app.stop_camera.assert_called_once()
        app.root.after.assert_called_once_with(200, app.tick)

    def test_game_render_retry_redacts_rom_path_and_keeps_250ms_pacing(self):
        app = GameplayMixin()
        app._closing = False
        app.emu = SimpleNamespace(running=False)
        app.root = Mock()
        app.draw_game = Mock(side_effect=OSError(
            "/home/private/ROMs/game.iso GPU serial SECRET-123"
        ))
        app.game_status = Mock()
        with patch("anything_plays.ui_gameplay.time.monotonic",
                   return_value=10.0):
            app.game_render_tick()
        message = app.game_status.set.call_args.args[0]
        self.assertEqual(message, "Display error (retrying: OSError).")
        for secret in ("/home/", "game.iso", "SECRET-123"):
            self.assertNotIn(secret, message)
        app.root.after.assert_called_once_with(250, app.game_render_tick)
        self.assertEqual(app._game_render_retry_at, 12.0)


if __name__ == "__main__":
    unittest.main()
