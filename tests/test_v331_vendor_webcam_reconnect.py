"""3.3.1: vendor-specific native webcam failures use bounded safe reconnect.

Only synthetic captures and pixels; no physical webcam, Tk window, or ROM.
"""
import unittest
from unittest.mock import Mock, patch

import numpy as np

from anything_plays.ui_camera import CameraMixin
from anything_plays.ui_gameplay import GameplayMixin


class VendorDriverFault(Exception):
    pass


class CameraHarness(CameraMixin, GameplayMixin):
    NAME = "USB webcam (device 0)"

    def __init__(self):
        self._closing = False
        self.root = Mock()
        self.root.after.side_effect = lambda delay, callback: f"job-{delay}"
        self.camera_name = Mock()
        self.camera_name.get.return_value = self.NAME
        self.camera_options = {self.NAME: 0}
        self._active_camera_name = self.NAME
        self._camera_reconnect_job = None
        self._camera_reconnect_name = None
        self._camera_reconnect_attempts = 0
        self.camera_bezel = Mock()
        self.stream_clear_camera = Mock()
        self.canvas = Mock()
        self.status = Mock()
        self.game_status = Mock()
        self.cap = Mock()
        self.cap.isOpened.return_value = True
        self.frame = None
        self.reference_image = False
        self.camera_photo = object()
        self.mirror = Mock()
        self.mirror.get.return_value = False
        self.draw_camera = Mock()
        self.armed = True
        self.emu = Mock()
        self.emu.error = None
        self.emu.save_warning = None
        self.emu.audio_warning = None
        self.emu.resume_info = None
        self.emu.running = False
        self.stop_controls = Mock(side_effect=self.disarm)

    def disarm(self):
        self.armed = False
        self.emu.armed = False


class VendorWebcamFailureTests(unittest.TestCase):
    def assert_bounded_reconnect(self, app):
        old = app.cap
        app.tick()
        self.assertIsNone(app.cap)
        self.assertIsNone(app.frame)
        self.assertIsNone(app.camera_photo)
        self.assertFalse(app.armed)
        self.assertFalse(app.emu.armed)
        old.release.assert_called_once()
        app.stream_clear_camera.assert_called_once()
        app.stop_controls.assert_called_once()
        self.assertEqual(app._camera_reconnect_attempts, 1)
        self.assertEqual(app._camera_reconnect_name, app.NAME)
        self.assertEqual(app._camera_reconnect_job, "job-2000")
        self.assertEqual(
            [call.args[0] for call in app.root.after.call_args_list],
            [2000, 200],
        )
        self.assertNotIn("PRIVATE", app.status.set.call_args.args[0])

    def test_unexpected_isopened_exception_releases_buttons_and_retries(self):
        app = CameraHarness()
        app.cap.isOpened.side_effect = VendorDriverFault(
            "PRIVATE native camera serial 123"
        )
        self.assert_bounded_reconnect(app)
        app.cap = None
        self.assertFalse(app._camera_is_open())

    def test_unexpected_read_exception_releases_buttons_and_retries(self):
        app = CameraHarness()
        app.cap.read.side_effect = VendorDriverFault(
            "PRIVATE unplug at /dev/video5"
        )
        self.assert_bounded_reconnect(app)

    def test_unexpected_mirror_exception_releases_buttons_and_retries(self):
        app = CameraHarness()
        app.mirror.get.return_value = True
        app.cap.read.return_value = (
            True, np.zeros((8, 8, 3), dtype=np.uint8)
        )
        with patch("anything_plays.ui_gameplay.cv2.flip",
                   side_effect=VendorDriverFault("PRIVATE camera ID")):
            self.assert_bounded_reconnect(app)

    def test_unusual_frame_shape_accessor_failure_retries(self):
        class DamagedFrame:
            @property
            def shape(self):
                raise VendorDriverFault("PRIVATE frame token")

        app = CameraHarness()
        app.cap.read.return_value = (True, DamagedFrame())
        self.assert_bounded_reconnect(app)

    def test_changed_camera_selection_never_auto_opens_other_device(self):
        app = CameraHarness()
        app.camera_name.get.return_value = "Other camera (device 1)"
        app.cap.read.side_effect = VendorDriverFault(
            "PRIVATE failed original USB camera"
        )
        old = app.cap
        app.tick()
        self.assertFalse(app.armed)
        self.assertIsNone(app.cap)
        self.assertIsNone(app._camera_reconnect_job)
        self.assertEqual(app._camera_reconnect_attempts, 0)
        old.release.assert_called_once()
        self.assertIn("Click Use camera", app.status.set.call_args.args[0])

    def test_vendor_status_exception_fails_closed_for_arm_button(self):
        app = CameraHarness()
        app.armed = False
        app.cap.isOpened.side_effect = VendorDriverFault(
            "PRIVATE bad camera status"
        )
        # The arm button never enables controls or prints device details.
        app.uses_embedded_emulator = lambda: True
        app.system_key = Mock()
        app.system_key.get.return_value = "gba"
        app.external_input = None
        with patch("anything_plays.ui_gameplay.messagebox.showinfo") as popup:
            app.toggle()
        popup.assert_called_once()
        self.assertEqual(popup.call_args.args[0], "Camera required")
        self.assertFalse(app.armed)
        self.assertNotIn("PRIVATE", str(popup.call_args))


if __name__ == "__main__":
    unittest.main()
