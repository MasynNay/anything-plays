"""3.2: driver read/flip failures must use bounded reconnect, not dead-end Stop.

Only synthetic native capture objects and pixel arrays. No real webcam, Tk
window, emulator, controller, ROM, camera permission or recording is used.
"""

import unittest
from unittest.mock import Mock, patch

import numpy as np

from anything_plays.ui_camera import CameraMixin
from anything_plays.ui_gameplay import GameplayMixin


class CameraHarness(CameraMixin, GameplayMixin):
    def __init__(self):
        self._closing = False
        self.root = Mock()
        self.root.after.side_effect = lambda delay, action: f"timer-{delay}"
        self.camera_name = Mock()
        self.camera_name.get.return_value = "Selected webcam (device 0)"
        self.camera_options = {"Selected webcam (device 0)": 0}
        self._camera_reconnect_job = None
        self._camera_reconnect_attempts = 0
        self._camera_reconnect_name = None
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
        self.stop_controls = Mock(side_effect=self._disarm)

    def _disarm(self):
        self.armed = False
        self.emu.armed = False


class CameraDriverReadRecoveryTests(unittest.TestCase):
    def assert_recovers(self, app, old):
        app.tick()
        self.assertIsNone(app.cap)
        self.assertIsNone(app.frame)
        self.assertIsNone(app.camera_photo)
        self.assertFalse(app.armed)
        old.release.assert_called_once()
        self.assertEqual(app._camera_reconnect_attempts, 1)
        self.assertEqual(app._camera_reconnect_name, "Selected webcam (device 0)")
        self.assertEqual(app._camera_reconnect_job, "timer-2000")
        self.assertIn("remain paused", app.status.set.call_args.args[0])
        intervals = [call.args[0] for call in app.root.after.call_args_list]
        self.assertEqual(intervals, [2000, 200])
        app.draw_camera.assert_not_called()
        app.stream_clear_camera.assert_called_once()

    def test_driver_read_raises_during_unplug(self):
        for error in (OSError("USB disconnected"),
                      RuntimeError("backend fault")):
            with self.subTest(error=repr(error)):
                app = CameraHarness()
                old = app.cap
                old.read.side_effect = error
                self.assert_recovers(app, old)

    def test_backend_reports_success_with_no_pixels_or_empty_image(self):
        for frame in (
            None,
            np.empty((0, 64, 3), dtype=np.uint8),
            np.empty((64, 0, 3), dtype=np.uint8),
            object(),
        ):
            with self.subTest(frame_type=type(frame).__name__):
                app = CameraHarness()
                old = app.cap
                old.read.return_value = (True, frame)
                self.assert_recovers(app, old)

    def test_mirror_failure_also_uses_retry_instead_of_dead_end(self):
        app = CameraHarness()
        old = app.cap
        app.mirror.get.return_value = True
        old.read.return_value = (
            True, np.zeros((8, 8, 3), dtype=np.uint8),
        )
        with patch("anything_plays.ui_gameplay.cv2.flip",
                   side_effect=RuntimeError("mirror native driver fault")):
            self.assert_recovers(app, old)

    def test_healthy_frame_remains_live_without_reconnect(self):
        app = CameraHarness()
        camera = app.cap
        sample = np.zeros((8, 8, 3), dtype=np.uint8)
        camera.read.return_value = (True, sample)
        app.tick()
        self.assertIs(app.cap, camera)
        self.assertIs(app.frame, sample)
        self.assertTrue(app.armed)
        camera.release.assert_not_called()
        app.draw_camera.assert_called_once()
        self.assertIsNone(app._camera_reconnect_job)
        self.assertEqual(app._camera_reconnect_attempts, 0)
        self.assertEqual(
            [c.args[0] for c in app.root.after.call_args_list], [45],
        )

    def test_successful_reconnect_does_not_restore_prior_armed_camera(self):
        app = CameraHarness()
        app.cap.read.side_effect = RuntimeError("USB removed")
        app.tick()
        fresh = Mock()
        fresh.isOpened.return_value = True
        with patch("anything_plays.ui_camera.cv2.VideoCapture",
                   return_value=fresh):
            app._retry_camera("Selected webcam (device 0)")
        self.assertIs(app.cap, fresh)
        self.assertFalse(app.armed)
        self.assertFalse(app.emu.armed)
        self.assertIsNone(app._camera_reconnect_job)
        self.assertEqual(app._camera_reconnect_attempts, 0)
        self.assertIn("reconnected", app.status.set.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
