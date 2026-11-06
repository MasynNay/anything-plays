"""The GUI must exit even when USB and native emulator drivers misbehave."""
from threading import Lock
from unittest.mock import Mock
import unittest

from app import App


class ShutdownSafetyTests(unittest.TestCase):
    def test_device_release_failures_do_not_block_window_destruction(self):
        app = App.__new__(App)
        app.root = Mock()
        app._closing = False
        app.cancel_camera_reconnect = Mock()
        app.persist_system_profile = Mock()
        app.deactivate_manual = Mock()
        app.stop_controls = Mock()
        app.stop_external_emulator = Mock(
            side_effect=OSError("Dolphin pipe disappeared")
        )
        app.cap = Mock()
        app.cap.release.side_effect = RuntimeError("USB device unplugged")
        app.emu = Mock()
        app.emu.lock = Lock()
        app.emu.frame = object()
        app.emu.stop.side_effect = RuntimeError("Core already ended")
        app._zone_thumbnail_cache = {"old": object()}
        app.library_images = [object()]
        app.frame = object()
        app.game_photo = object()
        app.camera_photo = object()
        app._zone_art = object()

        app.close()

        self.assertTrue(app._closing)
        self.assertIsNone(app.cap)
        self.assertIsNone(app.emu.frame)
        self.assertIsNone(app.frame)
        self.assertIsNone(app.camera_photo)
        self.assertIsNone(app.game_photo)
        self.assertFalse(app.library_images)
        self.assertFalse(app._zone_thumbnail_cache)
        app.cap  # No accidental reuse of the released capture.
        app.emu.stop.assert_called_once()
        app.stop_external_emulator.assert_called_once()
        app.root.destroy.assert_called_once()
        # Closing twice must not destroy widgets or release native handles twice.
        app.close()
        app.root.destroy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
