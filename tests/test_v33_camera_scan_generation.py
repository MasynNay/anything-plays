"""Generation-fenced webcam discovery on the real CameraMixin.

No physical camera, ROM, Tk window or background thread is created.
Manual callbacks reproduce delayed discovery, cancellation and UI teardown.
"""
import unittest
from unittest.mock import Mock, patch

from anything_plays.ui_camera import CameraMixin


class ManualThread:
    pending = []

    def __init__(self, *, target, daemon, name):
        self.target = target
        self.daemon = daemon
        self.name = name
        ManualThread.pending.append(self)

    def start(self):
        pass


class ScanHarness(CameraMixin):
    def __init__(self):
        self.camera_scanning = False
        self._closing = False
        self._camera_scan_results = None
        self._camera_scan_generation = 0
        self.status = Mock()
        self.stop_camera = Mock()
        self.camera_name = Mock()
        self.camera_name.get.return_value = ""
        self.camera_options = {}
        self.camera_combo = {}
        self.root = Mock()
        self.timers = []

        def after(delay, action):
            self.timers.append((delay, action))
            return f"scan-{len(self.timers)}"

        self.root.after.side_effect = after


class ScanOwnershipTests(unittest.TestCase):
    def setUp(self):
        ManualThread.pending = []

    def _scan(self, app):
        with patch("anything_plays.ui_camera.threading.Thread", ManualThread):
            app.scan_cameras()

    def test_finished_discovery_publishes_only_to_current_window(self):
        app = ScanHarness()
        self._scan(app)
        self.assertTrue(app.camera_scanning)
        app.stop_camera.assert_called_once()
        self.assertEqual(app.timers[0][0], 80)
        with patch("anything_plays.ui_camera.discover",
                   return_value=[(2, "Desk webcam")]):
            ManualThread.pending[0].target()
        app.timers.pop(0)[1]()
        self.assertFalse(app.camera_scanning)
        self.assertIsNone(app._camera_scan_results)
        self.assertEqual(app.camera_options, {"Desk webcam (device 2)": 2})
        self.assertEqual(app.camera_combo["values"],
                         ["Desk webcam (device 2)"])

    def test_delayed_old_callback_cannot_consume_new_results(self):
        app = ScanHarness()
        self._scan(app)
        old_callback = app.timers[0][1]
        with patch("anything_plays.ui_camera.discover",
                   return_value=[(0, "First")]):
            ManualThread.pending[0].target()
        old_callback()
        self.assertFalse(app.camera_scanning)
        self._scan(app)
        new_callback = app.timers[-1][1]
        with patch("anything_plays.ui_camera.discover",
                   return_value=[(1, "Second")]):
            ManualThread.pending[1].target()
        old_callback()
        self.assertTrue(app.camera_scanning)
        self.assertEqual(app.camera_combo["values"], ["First (device 0)"])
        new_callback()
        self.assertEqual(app.camera_combo["values"], ["Second (device 1)"])
        self.assertFalse(app.camera_scanning)

    def test_stale_worker_finishing_late_cannot_replace_newer_scan(self):
        app = ScanHarness()
        self._scan(app)
        old_thread, old_callback = ManualThread.pending[0], app.timers[0][1]
        app._retire_camera_scan(
            app._camera_scan_generation, app._camera_scan_results
        )
        self._scan(app)
        new_callback = app.timers[-1][1]
        with patch("anything_plays.ui_camera.discover",
                   return_value=[(8, "Stale USB")]):
            old_thread.target()
        with patch("anything_plays.ui_camera.discover",
                   return_value=[(3, "Fresh USB")]):
            ManualThread.pending[1].target()
        old_callback()
        new_callback()
        self.assertEqual(app.camera_combo["values"], ["Fresh USB (device 3)"])
        self.assertFalse(app.camera_scanning)

    def test_tk_schedule_failure_releases_stuck_scan_flag(self):
        app = ScanHarness()
        app.root.after.side_effect = RuntimeError(
            "private destroyed Tk /Users/owner/camera"
        )
        self._scan(app)
        self.assertFalse(app.camera_scanning)
        self.assertIsNone(app._camera_scan_results)
        self.assertIn("interrupted", app.status.set.call_args.args[0])
        self.assertNotIn("/Users/", app.status.set.call_args.args[0])
        app.root.after.side_effect = lambda delay, fn: app.timers.append(
            (delay, fn)
        )
        self._scan(app)
        self.assertTrue(app.camera_scanning)

    def test_repeated_empty_poll_schedule_failure_is_recoverable(self):
        app = ScanHarness()
        self._scan(app)
        app.root.after.side_effect = OSError("/home/private/tk-destroyed")
        app.timers.pop(0)[1]()
        self.assertFalse(app.camera_scanning)
        self.assertIsNone(app._camera_scan_results)
        self.assertNotIn("/home/", app.status.set.call_args.args[0])

    def test_native_thread_start_failure_allows_new_discovery(self):
        app = ScanHarness()

        class FailedThread(ManualThread):
            def start(self):
                raise RuntimeError("PRIVATE thread limit /dev/video")

        with patch("anything_plays.ui_camera.threading.Thread", FailedThread):
            app.scan_cameras()
        self.assertFalse(app.camera_scanning)
        self.assertIsNone(app._camera_scan_results)
        self._scan(app)
        self.assertTrue(app.camera_scanning)

    def test_closed_window_retires_its_pending_scan(self):
        app = ScanHarness()
        self._scan(app)
        app._closing = True
        app.timers.pop(0)[1]()
        self.assertFalse(app.camera_scanning)
        self.assertIsNone(app._camera_scan_results)
        self.assertEqual(app.camera_combo, {})
        app.status.set.assert_called_once_with(
            "Searching for available webcams…"
        )

    def test_unexpected_finish_error_does_not_leave_scan_stuck(self):
        app = ScanHarness()
        self._scan(app)
        with patch("anything_plays.ui_camera.discover",
                   return_value=[(3, "USB webcam")]):
            ManualThread.pending[0].target()
        app.finish_scan = Mock(side_effect=RuntimeError(
            "PRIVATE /home/operator/camera"
        ))
        app.timers.pop(0)[1]()
        self.assertFalse(app.camera_scanning)
        self.assertIsNone(app._camera_scan_results)
        self.assertIn("could not be shown", app.status.set.call_args.args[0])
        self.assertNotIn("/home/operator", app.status.set.call_args.args[0])


    def test_hung_driver_search_times_out_after_bounded_tk_polls(self):
        app = ScanHarness()
        self._scan(app)
        # The native worker has never returned, as with an unplugged
        # webcam whose driver blocks inside VideoCapture construction.
        with patch("anything_plays.ui_camera.CAMERA_SCAN_MAX_POLLS", 3):
            for _ in range(3):
                app.timers.pop(0)[1]()
        self.assertFalse(app.camera_scanning)
        self.assertIsNone(app._camera_scan_results)
        self.assertEqual(app._camera_scan_poll_count, 0)
        self.assertIn("interrupted", app.status.set.call_args.args[0])
        self.assertFalse(app._camera_scan_workers[0].is_set())
        # Retry is possible with one orphaned worker still outstanding.
        self._scan(app)
        self.assertTrue(app.camera_scanning)

    def test_late_hung_worker_cannot_replace_results_of_retried_search(self):
        app = ScanHarness()
        self._scan(app)
        expired_callback = app.timers[0][1]
        with patch("anything_plays.ui_camera.CAMERA_SCAN_MAX_POLLS", 1):
            expired_callback()
        self._scan(app)
        with patch("anything_plays.ui_camera.discover",
                   return_value=[(9, "Old camera")]):
            ManualThread.pending[0].target()
        expired_callback()
        with patch("anything_plays.ui_camera.discover",
                   return_value=[(2, "Current camera")]):
            ManualThread.pending[1].target()
        app.timers[-1][1]()
        self.assertEqual(
            app.camera_combo["values"], ["Current camera (device 2)"]
        )
        self.assertFalse(app.camera_scanning)

    def test_two_hung_driver_threads_cap_retries_without_disarming_live_game(self):
        app = ScanHarness()
        self._scan(app)
        with patch("anything_plays.ui_camera.CAMERA_SCAN_MAX_POLLS", 1):
            app.timers[-1][1]()
        self._scan(app)
        with patch("anything_plays.ui_camera.CAMERA_SCAN_MAX_POLLS", 1):
            app.timers[-1][1]()
        self.assertEqual(len(ManualThread.pending), 2)
        app.stop_camera.reset_mock()
        self._scan(app)
        self.assertEqual(len(ManualThread.pending), 2)
        app.stop_camera.assert_not_called()
        self.assertFalse(app.camera_scanning)
        self.assertIn("still busy", app.status.set.call_args.args[0])
        # Finishing one old worker releases its one budget slot.
        with patch("anything_plays.ui_camera.discover",
                   return_value=[]):
            ManualThread.pending[0].target()
        self._scan(app)
        self.assertEqual(len(ManualThread.pending), 3)
        self.assertTrue(app.camera_scanning)

    def test_failed_worker_start_does_not_consume_stuck_worker_budget(self):
        app = ScanHarness()
        class BadStart(ManualThread):
            def start(self):
                raise OSError("Private /dev/video fake driver")
        for _ in range(3):
            with patch("anything_plays.ui_camera.threading.Thread", BadStart):
                app.scan_cameras()
            self.assertFalse(app.camera_scanning)
            self.assertIsNone(app._camera_scan_results)
        self._scan(app)
        self.assertTrue(app.camera_scanning)

    def test_unexpected_results_queue_error_is_recoverable(self):
        app = ScanHarness()
        self._scan(app)
        app._camera_scan_results.get_nowait = Mock(
            side_effect=RuntimeError("Private /Users/owner/camera path")
        )
        app.timers[-1][1]()
        self.assertFalse(app.camera_scanning)
        self.assertIsNone(app._camera_scan_results)
        self.assertNotIn("/Users/owner", app.status.set.call_args.args[0])
        self._scan(app)
        self.assertTrue(app.camera_scanning)

if __name__ == "__main__":
    unittest.main()
