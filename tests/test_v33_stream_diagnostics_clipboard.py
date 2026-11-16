"""Privacy-guarded user-triggered Stream Mode QA clipboard tests.

These are pure source tests: no webcam, ROM, OBS encoder or OS clipboard.
"""
import json
import unittest
from unittest.mock import Mock

from anything_plays.ui_stream import (
    DEFAULT_STREAM, StreamCadenceTracker, StreamMixin,
    StreamPanelResizeCache, stream_safe_qa_report,
)


class StreamDiagnosticsClipboardTests(unittest.TestCase):
    def app(self):
        class Harness(StreamMixin):
            pass

        app = Harness()
        app.root = Mock()
        app._stream_output_window = object()
        app._stream_options = dict(DEFAULT_STREAM)
        app._stream_cadence = StreamCadenceTracker()
        app._stream_cadence.reset_for("24 FPS")
        app._stream_resize_cache = StreamPanelResizeCache()
        app._stream_session_faults = 2
        app._stream_session_recoveries = 1
        app._stream_stale_camera_clears = 3
        app._stream_recovery_pending = False
        app._stream_diagnostic = Mock()
        app._stream_diagnostic.get.return_value = "Stream output ready"
        return app

    def test_clipboard_copies_tk_only_metrics_without_images_or_paths(self):
        app = self.app()
        self.assertTrue(app._copy_stream_diagnostics())
        app.root.clipboard_clear.assert_called_once_with()
        app.root.clipboard_append.assert_called_once()
        app.root.update_idletasks.assert_called_once_with()
        contents = app.root.clipboard_append.call_args.args[0]
        result = json.loads(contents)
        self.assertEqual(result["format"], "anything-plays-stream-qa-aggregate")
        self.assertEqual(result["metrics"]["stream_target_refresh_fps"], 24)
        self.assertEqual(result["metrics"]["stream_session_faults"], 2)
        self.assertEqual(result["metrics"]["stream_session_recoveries"], 1)
        self.assertEqual(result["metrics"]["stream_stale_camera_clears"], 3)
        for flag in (
            "physical_camera_verified_by_report",
            "native_gamecube_verified_by_report",
            "obs_encoder_verified_by_report",
        ):
            self.assertIs(result[flag], False)
        self.assertNotIn("image", result)
        self.assertNotIn("frame", result)
        self.assertNotIn("path", contents)
        self.assertNotIn("camera_serial", contents)
        app._stream_diagnostic.set.assert_called_with(
            "Copied Tk stream metrics (not OBS or physical-camera FPS)"
        )

    def test_malicious_or_malformed_extra_fields_are_not_exported(self):
        original = {
            "path": "/home/owner/private/ROM-file",
            "camera_serial": "private-webcam-998",
            "frame": object(),
            "settings": {"rom_directory": "/Users/owner/Games"},
            "metrics": {
                "stream_target_refresh_fps": 30,
                "stream_session_faults": 4,
                "stream_recovery_pending": True,
                "stream_render_max_ms": float("inf"),
                "stream_render_mean_ms": float("nan"),
                "stream_render_p95_bucket_code": -1,
                "stream_resize_cache_hits": -10,
                "camera_name": "/dev/video0 private camera",
                "stream_failed_ticks": "private path",
                "stream_published_images": object(),
            },
        }
        result = stream_safe_qa_report(original)
        self.assertIsNotNone(result)
        dumped = json.dumps(result, allow_nan=False)
        self.assertEqual(result["metrics"]["stream_session_faults"], 4)
        self.assertEqual(result["metrics"]["stream_render_p95_bucket_code"], -1)
        self.assertTrue(result["metrics"]["stream_recovery_pending"])
        for word in ("/home", "private", "camera_name", "ROM-file", "frame",
                     "nan", "inf", "resize_cache_hits"):
            self.assertNotIn(word, dumped)
        self.assertIsNone(stream_safe_qa_report(None))
        self.assertIsNone(stream_safe_qa_report({"metrics": []}))
        self.assertIsNone(stream_safe_qa_report({"metrics": {"secret": "path"}}))

    def test_inactive_stream_never_changes_clipboard(self):
        app = self.app()
        app._stream_output_window = None
        self.assertFalse(app._copy_stream_diagnostics())
        app.root.clipboard_clear.assert_not_called()
        app.root.clipboard_append.assert_not_called()
        app._stream_diagnostic.set.assert_called_with(
            "No active stream metrics to copy"
        )

    def test_destroyed_native_clipboard_fails_without_leaking_driver_details(self):
        app = self.app()
        app.root.clipboard_append.side_effect = RuntimeError(
            "/Users/private/camera-serial-73"
        )
        self.assertFalse(app._copy_stream_diagnostics())
        app._stream_diagnostic.set.assert_called_with(
            "Could not copy stream diagnostics"
        )

    def test_broken_perf_snapshot_is_optional_and_fails_closed(self):
        app = self.app()
        app.stream_performance_snapshot = Mock(
            side_effect=OSError("/home/private/webcam-222")
        )
        self.assertFalse(app._copy_stream_diagnostics())
        app.root.clipboard_clear.assert_not_called()
        app._stream_diagnostic.set.assert_called_with(
            "No active stream metrics to copy"
        )


if __name__ == "__main__":
    unittest.main()
