"""Camera retry job ownership and native startup fault isolation (3.3.1).

All probes are synthetic: no physical webcams, Tk, user files or emulator.
"""
import unittest
from unittest.mock import Mock, patch

from anything_plays.ui_camera import CameraMixin


class Harness(CameraMixin):
    NAME = "Synthetic camera (device 0)"

    def __init__(self):
        self.root = Mock()
        self.callbacks = {}
        self.counter = 0

        def schedule(delay, callback):
            self.counter += 1
            job = f"retry-{self.counter}"
            self.callbacks[job] = (delay, callback)
            return job

        self.root.after.side_effect = schedule
        self.root.after_cancel.side_effect = self.callbacks.pop
        self._closing = False
        self._camera_reconnect_job = None
        self._camera_reconnect_name = None
        self._camera_reconnect_attempts = 0
        self._camera_retry_generation = 0
        self._active_camera_name = None
        self.camera_name = Mock()
        self.camera_name.get.return_value = self.NAME
        self.camera_options = {self.NAME: 0}
        self.status = Mock()
        self.stop_controls = Mock()
        self.stop_controls.side_effect = lambda: setattr(self, "armed", False)
        self.armed = False
        self.cap = None
        self.frame = None
        self.reference_image = False
        self.camera_photo = None
        self._camera_canvas_item = None
        self.canvas = Mock()
        self.stream_clear_camera = Mock()
        self.camera_bezel = Mock()


class RetrySchedulerSafetyTests(unittest.TestCase):
    def test_failed_after_resets_attempts_and_retry_is_possible(self):
        app = Harness()
        app.root.after.side_effect = RuntimeError(
            "PRIVATE /Users/tester/camera driver"
        )
        self.assertFalse(app._queue_camera_retry(app.NAME))
        self.assertIsNone(app._camera_reconnect_job)
        self.assertIsNone(app._camera_reconnect_name)
        self.assertEqual(app._camera_reconnect_attempts, 0)
        self.assertEqual(app._camera_retry_generation, 2)
        self.assertIn("Automatic camera retry unavailable",
                      app.status.set.call_args.args[0])
        self.assertNotIn("/Users/", app.status.set.call_args.args[0])
        app.root.after.side_effect = lambda delay, callback: "new-job"
        self.assertTrue(app._queue_camera_retry(app.NAME))
        self.assertEqual(app._camera_reconnect_job, "new-job")
        self.assertEqual(app._camera_reconnect_attempts, 1)

    def test_no_timer_handle_does_not_grant_stale_callback_access(self):
        app = Harness()
        leaked = []
        def schedule_without_handle(_delay, fn):
            leaked.append(fn)
            return None
        app.root.after.side_effect = schedule_without_handle
        self.assertFalse(app._queue_camera_retry(app.NAME))
        self.assertIsNone(app._camera_reconnect_job)
        with patch.object(app, "start_camera") as start:
            leaked[0]()
            start.assert_not_called()

    def test_cancel_catches_unexpected_native_tk_error_and_fences_callback(self):
        app = Harness()
        self.assertTrue(app._queue_camera_retry(app.NAME))
        callback = app.callbacks[app._camera_reconnect_job][1]
        app.root.after_cancel.side_effect = ValueError(
            "PRIVATE invalid timer /home/tester"
        )
        app.cancel_camera_reconnect()
        self.assertIsNone(app._camera_reconnect_job)
        self.assertIsNone(app._camera_reconnect_name)
        self.assertEqual(app._camera_reconnect_attempts, 0)
        with patch.object(app, "start_camera") as start:
            callback()
            start.assert_not_called()

    def test_unusual_native_isopened_exception_releases_partial_camera(self):
        app = Harness()
        cap = Mock()
        cap.isOpened.side_effect = ValueError(
            "PRIVATE failed /dev/video0"
        )
        with patch("anything_plays.ui_camera.cv2.VideoCapture",
                   return_value=cap), patch(
                       "anything_plays.ui_camera.messagebox.showerror"
                   ) as popup:
            app.start_camera()
        cap.release.assert_called_once()
        self.assertIsNone(app.cap)
        self.assertIsNone(app._active_camera_name)
        self.assertFalse(app.armed)
        self.assertIsNone(app.frame)
        app.stream_clear_camera.assert_called()
        popup.assert_called_once()
        self.assertNotIn("PRIVATE", str(popup.call_args))

    def test_retry_failure_releases_old_native_capture_before_backoff(self):
        app = Harness()
        self.assertTrue(app._queue_camera_retry(app.NAME))
        retry = app.callbacks.pop(app._camera_reconnect_job)[1]
        cap = Mock()
        app.cap = cap
        app.frame = object()
        app.camera_photo = object()
        app.armed = True
        with patch.object(app, "start_camera",
                          side_effect=RuntimeError(
                              "PRIVATE controller /home/user/device")):
            retry()
        cap.release.assert_called_once()
        self.assertFalse(app.armed)
        self.assertIsNone(app.cap)
        self.assertIsNone(app.frame)
        self.assertIsNone(app.camera_photo)
        self.assertIn("retry-", str(app._camera_reconnect_job))
        self.assertEqual(app._camera_reconnect_attempts, 2)
        self.assertNotIn("PRIVATE", app.status.set.call_args.args[0])

    def test_destroyed_optional_ui_does_not_turn_successful_open_into_failure(self):
        app = Harness()
        cap = Mock()
        cap.isOpened.return_value = True
        app.camera_bezel.set_active.side_effect = RuntimeError(
            "PRIVATE already destroyed bezel"
        )
        app.status.set.side_effect = OSError(
            "PRIVATE invalid Tk label"
        )
        with patch("anything_plays.ui_camera.cv2.VideoCapture",
                   return_value=cap):
            app.start_camera()
        self.assertIs(app.cap, cap)
        self.assertEqual(app._active_camera_name, app.NAME)
        self.assertFalse(app.armed)
        cap.release.assert_not_called()


if __name__ == "__main__":
    unittest.main()
