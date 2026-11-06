"""Camera hot-unplug recovery without physical webcam or Tk window.

A retry is permitted only for the selected device. An explicit Stop or
application shutdown cancels all pending work. Camera object controls never
reactivate themselves after a reconnection.
"""
import unittest
from unittest.mock import Mock, patch

from anything_plays.ui_camera import CameraMixin
from anything_plays.ui_gameplay import GameplayMixin


class CameraHarness(CameraMixin, GameplayMixin):
    """Minimal UI façade for exercising the real reconnection methods."""

    def __init__(self):
        self.root = Mock()
        self.callbacks = {}
        self.counter = 0

        def after(milliseconds, callback):
            self.counter += 1
            identifier = f"retry-{self.counter}"
            self.callbacks[identifier] = (milliseconds, callback)
            return identifier

        self.root.after.side_effect = after
        self.root.after_cancel.side_effect = self.callbacks.pop
        self.camera_name = Mock()
        self.camera_name.get.return_value = "Camera (device 0)"
        self.camera_options = {"Camera (device 0)": 0}
        self._closing = False
        self.cap = None
        self.frame = None
        self.reference_image = False
        self.camera_photo = None
        self.status = Mock()
        self.canvas = Mock()
        self.canvas.delete = Mock()
        self.armed = True
        self.emu = Mock()
        self.emu.error = None
        self.emu.save_warning = None
        self.emu.running = False

    def stop_controls(self):
        self.armed = False


class CameraRecoveryTests(unittest.TestCase):
    def test_capture_failure_queues_one_bounded_retry(self):
        app = CameraHarness()
        camera = Mock()
        camera.isOpened.return_value = True
        camera.read.return_value = (False, None)
        app.cap = camera
        app.tick()
        self.assertTrue(camera.release.called)
        self.assertIsNone(app.cap)
        self.assertFalse(app.armed)
        self.assertEqual(app._camera_reconnect_attempts, 1)
        self.assertIn("retry", app._camera_reconnect_job)
        self.assertEqual(
            app.callbacks[app._camera_reconnect_job][0], 2000
        )
        app._queue_camera_retry("Camera (device 0)")
        self.assertEqual(app._camera_reconnect_attempts, 1)

    def test_reconnection_keeps_camera_controls_disarmed(self):
        app = CameraHarness()
        app._queue_camera_retry("Camera (device 0)")
        job = app._camera_reconnect_job
        _delay, retry = app.callbacks.pop(job)
        camera = Mock()
        camera.isOpened.return_value = True
        with patch("anything_plays.ui_camera.cv2.VideoCapture",
                   return_value=camera):
            retry()
        self.assertIs(app.cap, camera)
        self.assertFalse(app.armed)
        self.assertIsNone(app._camera_reconnect_job)
        self.assertEqual(app._camera_reconnect_attempts, 0)
        self.assertIn(
            "reconnected", app.status.set.call_args.args[0].lower()
        )

    def test_failed_reconnections_backoff_without_dialogs(self):
        app = CameraHarness()
        app._queue_camera_retry("Camera (device 0)")
        for interval in (4000, 8000, 16000, 30000, 30000):
            job = app._camera_reconnect_job
            _delay, retry = app.callbacks.pop(job)
            camera = Mock()
            camera.isOpened.return_value = False
            with patch("anything_plays.ui_camera.cv2.VideoCapture",
                       return_value=camera), patch(
                           "anything_plays.ui_camera.messagebox.showerror"
                       ) as popup:
                retry()
                popup.assert_not_called()
            self.assertEqual(
                app.callbacks[app._camera_reconnect_job][0], interval
            )
            self.assertFalse(app.armed)

    def test_manual_stop_and_shutdown_cancel_pending_retry(self):
        for closing in (False, True):
            with self.subTest(closing=closing):
                app = CameraHarness()
                app._queue_camera_retry("Camera (device 0)")
                if closing:
                    app._closing = True
                app.stop_camera()
                self.assertIsNone(app._camera_reconnect_job)
                self.assertIsNone(app._camera_reconnect_name)
                self.assertEqual(app._camera_reconnect_attempts, 0)
                self.assertFalse(app.callbacks)
                self.assertFalse(app.armed)

    def test_changed_selected_device_prevents_old_retry(self):
        app = CameraHarness()
        app._queue_camera_retry("Camera (device 0)")
        _delay, retry = app.callbacks.pop(app._camera_reconnect_job)
        app.camera_name.get.return_value = "Different Camera"
        with patch("anything_plays.ui_camera.cv2.VideoCapture") as capture:
            retry()
            capture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
