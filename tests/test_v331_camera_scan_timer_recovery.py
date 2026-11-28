"""3.3.1: a broken Tk status/timer must never strand webcam discovery.

Only synthetic Thread, Queue, Tk and device names are used. Never opens a real
camera, privacy-sensitive image, ROM, native capture or filesystem path.
"""
import unittest
from unittest.mock import Mock, patch

from anything_plays.ui_camera import CameraMixin


class ManualThread:
    instances = []

    def __init__(self, *, target, daemon, name):
        self.target = target
        self.daemon = daemon
        self.name = name
        ManualThread.instances.append(self)

    def start(self):
        return None


class Host(CameraMixin):
    def __init__(self):
        self.camera_scanning = False
        self._closing = False
        self._camera_scan_results = None
        self._camera_scan_generation = 0
        self._camera_scan_workers = []
        self._camera_scan_poll_count = 0
        self.status = Mock()
        self.stop_camera = Mock()
        self.camera_name = Mock()
        self.camera_name.get.return_value = ""
        self.camera_options = {}
        self.camera_combo = {}
        self.root = Mock()
        self.callbacks = []

        def schedule(_delay, callback):
            self.callbacks.append(callback)
            return "scan-job-" + str(len(self.callbacks))

        self.root.after.side_effect = schedule

    def scan_without_real_thread(self):
        with patch("anything_plays.ui_camera.threading.Thread", ManualThread):
            self.scan_cameras()


class CameraScanTimerRecoveryTests(unittest.TestCase):
    def setUp(self):
        ManualThread.instances.clear()

    def test_damaged_status_label_does_not_prevent_webcam_enumeration(self):
        app = Host()
        app.status.set.side_effect = RuntimeError(
            "PRIVATE destroyed Tk label /Users/owner"
        )
        app.scan_without_real_thread()
        self.assertTrue(app.camera_scanning)
        self.assertEqual(len(ManualThread.instances), 1)
        self.assertEqual(len(app.callbacks), 1)
        self.assertEqual(app.root.after.call_args.args[0], 80)
        with patch("anything_plays.ui_camera.discover",
                   return_value=[(2, "Synthetic webcam")]):
            ManualThread.instances[0].target()
        app.callbacks.pop(0)()
        self.assertFalse(app.camera_scanning)
        self.assertIsNone(app._camera_scan_results)
        self.assertEqual(app.camera_options, {
            "Synthetic webcam (device 2)": 2
        })
        self.assertEqual(app.camera_combo["values"],
                         ["Synthetic webcam (device 2)"])

    def test_first_poll_without_timer_id_retires_scan(self):
        app = Host()
        leaked = []

        def missing_timer(_delay, callback):
            leaked.append(callback)
            return None

        app.root.after.side_effect = missing_timer
        app.scan_without_real_thread()
        self.assertFalse(app.camera_scanning)
        self.assertIsNone(app._camera_scan_results)
        self.assertEqual(app._camera_scan_poll_count, 0)
        self.assertEqual(len(leaked), 1)
        self.assertIn("interrupted", app.status.set.call_args.args[0])
        app.stop_camera.assert_called_once()

        # An adapter could have queued the callback despite not returning
        # an ID. It must not publish stale data after scan retirement.
        with patch.object(app, "finish_scan") as finish:
            leaked[0]()
            finish.assert_not_called()

    def test_failed_first_poll_allows_retry_and_fences_old_result(self):
        app = Host()
        leaked = []
        app.root.after.side_effect = lambda delay, cb: (
            leaked.append(cb) or None
        )
        app.scan_without_real_thread()
        old_callback = leaked[0]
        with patch("anything_plays.ui_camera.discover",
                   return_value=[(0, "Old disconnected USB")]):
            ManualThread.instances[0].target()

        # The completed worker no longer consumes a scan slot.
        app.root.after.side_effect = lambda delay, cb: (
            app.callbacks.append(cb) or "good-timer"
        )
        app.scan_without_real_thread()
        self.assertTrue(app.camera_scanning)
        self.assertEqual(len(ManualThread.instances), 2)
        with patch("anything_plays.ui_camera.discover",
                   return_value=[(1, "New webcam")]):
            ManualThread.instances[1].target()
        old_callback()
        self.assertEqual(app.camera_options, {})
        app.callbacks[0]()
        self.assertFalse(app.camera_scanning)
        self.assertEqual(app.camera_options, {"New webcam (device 1)": 1})

    def test_missing_timer_during_empty_queue_poll_retires_scan(self):
        app = Host()
        app.scan_without_real_thread()
        first_callback = app.callbacks.pop(0)
        late = []

        def missing_timer(_delay, callback):
            late.append(callback)
            return None

        app.root.after.side_effect = missing_timer
        first_callback()  # no worker output yet -> reschedule is rejected
        self.assertFalse(app.camera_scanning)
        self.assertIsNone(app._camera_scan_results)
        self.assertEqual(app._camera_scan_poll_count, 0)
        self.assertEqual(len(late), 1)
        with patch("anything_plays.ui_camera.discover",
                   return_value=[(3, "Late private device")]):
            ManualThread.instances[0].target()
        with patch.object(app, "finish_scan") as finish:
            late[0]()
            finish.assert_not_called()

    def test_second_poll_failure_is_recoverable_on_next_refresh(self):
        app = Host()
        app.scan_without_real_thread()
        app.root.after.side_effect = lambda delay, callback: None
        app.callbacks.pop(0)()
        self.assertFalse(app.camera_scanning)
        app.root.after.side_effect = lambda delay, callback: (
            app.callbacks.append(callback) or "new-id"
        )
        app.scan_without_real_thread()
        self.assertTrue(app.camera_scanning)
        self.assertEqual(app._camera_scan_poll_count, 0)
        with patch("anything_plays.ui_camera.discover",
                   return_value=[(1, "Healthy webcam")]):
            ManualThread.instances[1].target()
        app.callbacks[0]()
        self.assertEqual(app.camera_options, {
            "Healthy webcam (device 1)": 1
        })
        self.assertFalse(app.camera_scanning)

    def test_normal_scan_retains_single_owned_poll_and_results(self):
        app = Host()
        app.scan_without_real_thread()
        self.assertEqual(len(app.callbacks), 1)
        self.assertTrue(app.camera_scanning)
        with patch("anything_plays.ui_camera.discover",
                   return_value=[(0, "Camera")]):
            ManualThread.instances[0].target()
        app.callbacks[0]()
        self.assertEqual(app.camera_options, {"Camera (device 0)": 0})
        self.assertFalse(app.camera_scanning)
        app.stop_camera.assert_called_once()
        self.assertEqual(app.root.after.call_count, 1)


if __name__ == "__main__":
    unittest.main()
