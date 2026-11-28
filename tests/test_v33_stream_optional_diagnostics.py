"""3.3: optional Stream timing must never destroy a healthy OBS picture.

Mocks exercise the actual StreamMixin Tk timer callback, without opening a
webcam, native core, OBS encoder or output window.
"""
import unittest
from unittest.mock import Mock, patch

from anything_plays.ui_stream import (
    DEFAULT_STREAM, StreamCadenceTracker, StreamMixin,
)


def assert_stream_render_scheduled(testcase, app, interval_ms):
    """Verify the timer rate and callable without assuming a bare method.

    Stream Mode binds each timer to the OBS output it belongs to so old
    queued callbacks cannot publish into a reopened capture window.
    """
    testcase.assertEqual(app.root.after.call_count, 1)
    args = app.root.after.call_args.args
    testcase.assertEqual(args[0], interval_ms)
    testcase.assertTrue(callable(args[1]))


class StreamOptionalDiagnosticsTests(unittest.TestCase):
    def make_app(self, *, render=True):
        class Harness(StreamMixin):
            pass
        app = Harness()
        app._closing = False
        app._stream_output_window = object()
        app._stream_options = dict(DEFAULT_STREAM)
        app._stream_cadence = StreamCadenceTracker()
        app._stream_canvas = Mock()
        app._stream_photo = object()
        app._stream_canvas_item = 3
        app._stream_last_render = ("old photo",)
        app.root = Mock()
        app._render_stream_frame = Mock(return_value=render)
        return app

    def test_missing_finish_clock_keeps_valid_obs_image_and_normal_refresh(self):
        app = self.make_app()
        photo = app._stream_photo
        with patch("anything_plays.ui_stream.stream_optional_perf_clock",
                   side_effect=(10.0, None)):
            app._stream_render_tick()
        app._render_stream_frame.assert_called_once_with()
        self.assertIs(app._stream_photo, photo)
        app._stream_canvas.delete.assert_not_called()
        assert_stream_render_scheduled(self, app, 42)
        m = app.stream_performance_snapshot()["metrics"]
        self.assertEqual(m["stream_failed_ticks"], 0)
        self.assertEqual(m["stream_render_samples"], 0)

    def test_reversed_optional_clock_keeps_preview_and_skips_invalid_cost(self):
        app = self.make_app()
        with patch("anything_plays.ui_stream.stream_optional_perf_clock",
                   side_effect=(10.0, 9.0)):
            app._stream_render_tick()
        app._stream_canvas.delete.assert_not_called()
        assert_stream_render_scheduled(self, app, 42)
        m = app.stream_performance_snapshot()["metrics"]
        self.assertEqual(m["stream_failed_ticks"], 0)
        self.assertEqual(m["stream_render_samples"], 0)

    def test_corrupt_success_collector_does_not_blank_a_published_photo(self):
        app = self.make_app()
        photo = app._stream_photo
        app._stream_cadence.record_tick = Mock(side_effect=OSError(
            "PRIVATE USB serial /Users/owner/camera"
        ))
        with patch("anything_plays.ui_stream.stream_optional_perf_clock",
                   side_effect=(10.0, 10.01)):
            app._stream_render_tick()
        app._stream_canvas.delete.assert_not_called()
        self.assertIs(app._stream_photo, photo)
        self.assertIsNone(app._stream_cadence)
        self.assertEqual(getattr(app, "_stream_session_faults", 0), 0)
        assert_stream_render_scheduled(self, app, 32)
        self.assertIsNone(app.stream_performance_snapshot())

    def test_failed_canvas_still_blanks_and_retries_if_counter_throws(self):
        app = self.make_app()
        app._render_stream_frame.side_effect = ValueError(
            "PRIVATE /home/user/device"
        )
        app._stream_cadence.record_tick = Mock(side_effect=RuntimeError(
            "PRIVATE instrumentation failure"
        ))
        with patch("anything_plays.ui_stream.stream_optional_perf_clock",
                   side_effect=(10.0, 10.01)):
            app._stream_render_tick()
        self.assertIsNone(app._stream_photo)
        self.assertIsNone(app._stream_canvas_item)
        self.assertIsNone(app._stream_cadence)
        app._stream_canvas.delete.assert_called_once_with("all")
        assert_stream_render_scheduled(self, app, 1000)
        self.assertEqual(app._stream_session_faults, 1)
        self.assertTrue(app._stream_recovery_pending)

    def test_corrupt_snapshot_is_optional_and_preserves_active_capture(self):
        app = self.make_app()
        app._stream_cadence.snapshot = Mock(
            side_effect=OSError("PRIVATE /Users/owner/game.iso")
        )
        self.assertIsNone(app.stream_performance_snapshot())
        app._stream_cadence.snapshot = Mock(return_value=["PRIVATE"])
        self.assertIsNone(app.stream_performance_snapshot())
        self.assertIsNotNone(app._stream_photo)
        app._stream_canvas.delete.assert_not_called()


    def test_first_party_snapshot_extra_private_fields_are_not_in_setup_report(self):
        app = self.make_app()
        original = app._stream_cadence.snapshot()
        original["PRIVATE /Users/person/ROMs"] = "webcam-device-serial"
        app._stream_cadence.snapshot = Mock(return_value=original)
        result = app.stream_performance_snapshot()
        self.assertEqual(result["metrics"]["stream_target_refresh_fps"], 0)
        self.assertEqual(result["metrics"]["stream_failed_ticks"], 0)
        self.assertNotIn("PRIVATE", str(result))
        self.assertNotIn("webcam-device-serial", str(result))

    def test_bad_timing_counters_do_not_crash_or_leak_into_setup(self):
        app = self.make_app()
        valid = app._stream_cadence.snapshot()
        for key, bad in (
            ("stream_observed_refresh_fps", "/home/user/secret.rom"),
            ("stream_render_max_ms", float("nan")),
            ("stream_refresh_intervals", True),
            ("stream_failed_ticks", -1),
            ("stream_render_p95_bucket_code", 999),
            ("stream_published_images", 10**1000),
        ):
            with self.subTest(key=key):
                invalid = dict(valid)
                invalid[key] = bad
                app._stream_cadence.snapshot = Mock(return_value=invalid)
                self.assertIsNone(app.stream_performance_snapshot())
                self.assertIsNotNone(app._stream_photo)
                app._stream_canvas.delete.assert_not_called()
        app._stream_cadence.snapshot = Mock(return_value={"secret": "serial"})
        self.assertIsNone(app.stream_performance_snapshot())

    def test_only_builtin_cadence_collector_may_generate_setup_report(self):
        app = self.make_app()
        hostile = Mock()
        hostile.snapshot.side_effect = RuntimeError("PRIVATE driver /dev/video0")
        app._stream_cadence = hostile
        self.assertIsNone(app.stream_performance_snapshot())
        hostile.snapshot.assert_not_called()

    def test_builtin_resize_cache_snapshot_strips_private_and_invalid_fields(self):
        from anything_plays.ui_stream import StreamPanelResizeCache
        app = self.make_app()
        app._stream_resize_cache = StreamPanelResizeCache()
        app._stream_resize_cache.snapshot = Mock(return_value={
            "stream_resize_cache_hits": 3,
            "stream_resize_cache_misses": 2,
            "PRIVATE /dev/video0": "serial",
        })
        report = app.stream_performance_snapshot()
        m = report["metrics"]
        self.assertEqual(m["stream_resize_cache_hits"], 3)
        self.assertEqual(m["stream_resize_cache_misses"], 2)
        self.assertNotIn("PRIVATE", str(report))
        app._stream_resize_cache.snapshot = Mock(return_value={
            "stream_resize_cache_hits": "private user path",
            "stream_resize_cache_misses": 2,
        })
        self.assertNotIn(
            "stream_resize_cache_hits",
            app.stream_performance_snapshot()["metrics"],
        )

    def test_session_counters_are_validated_before_setup_displays_them(self):
        app = self.make_app()
        app._stream_session_faults = "private /Users/customer"
        app._stream_session_recoveries = -1
        app._stream_stale_camera_clears = True
        app._stream_recovery_pending = "private camera device"
        metrics = app.stream_performance_snapshot()["metrics"]
        self.assertNotIn("stream_session_faults", metrics)
        self.assertNotIn("stream_session_recoveries", metrics)
        self.assertNotIn("stream_stale_camera_clears", metrics)
        self.assertNotIn("stream_recovery_pending", metrics)
        self.assertNotIn("private", str(metrics))

if __name__ == "__main__":
    unittest.main()
