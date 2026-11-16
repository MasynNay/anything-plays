"""3.1 stream capture composition and settings, without real camera or ROMs."""
from __future__ import annotations

import inspect
import unittest

from PIL import Image

from anything_plays.ui_stream import (
    DEFAULT_STREAM, FRAME_RATES, LAYOUTS, StreamMixin, compose_stream_output,
    stream_panel_boxes, stream_render_delay_ms, StreamCadenceTracker,
    StreamPanelResizeCache, _contained,
    stream_camera_snapshot_due, validate_stream_settings,
)
from anything_plays.ui_theme import ThemeMixin


THEMES = ThemeMixin.THEMES


def sample(image, box):
    """Center of the actual content, below the optional header rail."""
    x0, y0, x1, y1 = box
    return image.getpixel(((x0+x1)//2, (y0+y1)//2 + 12))


class StreamModeContracts(unittest.TestCase):
    def test_stream_defaults_and_sanitization_are_isolated_from_main_theme(self):
        for name in THEMES:
            with self.subTest(theme=name):
                config = validate_stream_settings(None, THEMES, name)
                self.assertEqual(config["theme"], name)
                self.assertEqual(config["layout"], "DS stacked")
                self.assertEqual(config["frame_rate"], "24 FPS")
                self.assertEqual(config["border_color"], "")
                self.assertTrue(config["show_labels"])
                self.assertFalse(config["swap_screens"])
        invalid = {
            "theme": ["not a string"],
            "layout": "impossible",
            "frame_rate": "60 FPS",
            "border_color": "red; exec",
            "border_width": "100000",
            "game_size": "NaN",
            "swap_screens": "yes",
            "show_labels": 0,
        }
        cleaned = validate_stream_settings(invalid, THEMES, "Ocean Dark")
        self.assertEqual(cleaned["theme"], "Ocean Dark")
        self.assertEqual(cleaned["layout"], "DS stacked")
        self.assertEqual(cleaned["frame_rate"], "24 FPS")
        self.assertEqual(cleaned["border_color"], "")
        self.assertEqual(cleaned["border_width"], 16)
        self.assertEqual(cleaned["game_size"], DEFAULT_STREAM["game_size"])
        self.assertFalse(cleaned["swap_screens"])
        self.assertTrue(cleaned["show_labels"])
        good = validate_stream_settings({
            "theme": "Plum Dark", "layout": "Side by side",
            "frame_rate": "30 FPS",
            "border_color": "#Ab76Fc", "border_width": 7.7,
            "game_size": 64.3, "swap_screens": True, "show_labels": False,
        }, THEMES)
        self.assertEqual(good["border_color"], "#ab76fc")
        self.assertEqual(good["border_width"], 7)
        self.assertEqual(good["game_size"], 64)
        self.assertEqual(good["layout"], "Side by side")
        self.assertEqual(good["frame_rate"], "30 FPS")
        self.assertTrue(good["swap_screens"])
        self.assertFalse(good["show_labels"])

    def test_stream_refresh_interval_compensates_render_cost_without_spin(self):
        # The timer is based on the start of composition, not the end.
        self.assertEqual(stream_render_delay_ms(67, 0.020), 47)
        self.assertEqual(stream_render_delay_ms(42, 0.010), 32)
        self.assertEqual(stream_render_delay_ms(33, 0.040), 8)
        self.assertEqual(stream_render_delay_ms(33, 999), 8)
        self.assertEqual(stream_render_delay_ms(42, -1), 42)
        self.assertEqual(stream_render_delay_ms(42, float("nan")), 42)
        self.assertEqual(stream_render_delay_ms(42, None), 42)

    def test_render_tick_accounts_for_composition_time(self):
        from types import SimpleNamespace
        from unittest.mock import Mock, patch

        class Harness(StreamMixin):
            pass

        app = Harness()
        app._stream_output_window = object()
        app._closing = False
        app._stream_options = dict(DEFAULT_STREAM)
        app._stream_render_tick = StreamMixin._stream_render_tick.__get__(app)
        app._render_stream_frame = Mock()
        app._stream_diagnostic = Mock()
        app.root = Mock()
        with patch("anything_plays.ui_stream.time.perf_counter",
                   side_effect=(10.0, 10.020)):
            app._stream_render_tick()
        app.root.after.assert_called_once_with(22, app._stream_render_tick)
        app._render_stream_frame.assert_called_once_with()
        self.assertIsNotNone(app._stream_frame_job)

    def test_stream_render_failure_redacts_driver_device_and_private_paths(self):
        from unittest.mock import Mock, patch

        class Harness(StreamMixin):
            pass

        app = Harness()
        app._stream_output_window = object()
        app._closing = False
        app._stream_options = dict(DEFAULT_STREAM)
        app._stream_last_render = {}
        app._stream_diagnostic = Mock()
        app._stream_cadence = StreamCadenceTracker()
        app.root = Mock()
        app._render_stream_frame = Mock(side_effect=RuntimeError(
            "GPU /home/private/ROMs/secret.iso camera SERIAL-123"
        ))
        with patch("anything_plays.ui_stream.time.perf_counter",
                   return_value=10.0):
            app._stream_render_tick()
        status = app._stream_diagnostic.set.call_args.args[0]
        self.assertIn("RuntimeError", status)
        self.assertNotIn("/home/", status)
        self.assertNotIn("secret.iso", status)
        self.assertNotIn("SERIAL-123", status)
        app.root.after.assert_called_once_with(
            1000, app._stream_render_tick
        )
        self.assertEqual(
            app._stream_cadence.snapshot()["stream_failed_ticks"], 1
        )

    def test_stream_render_failure_keeps_backoff(self):
        from unittest.mock import Mock, patch

        class Harness(StreamMixin):
            pass

        app = Harness()
        app._stream_output_window = object()
        app._closing = False
        app._stream_options = dict(DEFAULT_STREAM)
        app._render_stream_frame = Mock(side_effect=RuntimeError("broken preview"))
        app._stream_diagnostic = Mock()
        app.root = Mock()
        with patch("anything_plays.ui_stream.time.perf_counter",
                   return_value=10.0):
            app._stream_render_tick()
        app.root.after.assert_called_once_with(1000, app._stream_render_tick)
        self.assertEqual(app._stream_last_render, None)

    def test_stream_camera_preview_conversion_is_rate_bounded(self):
        import cv2
        import numpy as np
        from types import SimpleNamespace
        from unittest.mock import Mock, patch

        class Harness(StreamMixin):
            THEMES = THEMES

        app = Harness()
        app.theme_name = SimpleNamespace(get=lambda: "Ocean Dark")
        app.initialize_stream_mode({})
        app._stream_output_window = Mock()
        app.root = Mock()
        app.save_preferences = Mock()
        frame = np.zeros((20, 25, 3), dtype=np.uint8)
        original_convert = cv2.cvtColor

        # 24 FPS Stream Mode needs at most one optional RGB/PIL snapshot
        # per ~42ms, even if tracking sends camera frames at 100 FPS.
        with (
            patch("anything_plays.ui_stream.time.monotonic",
                  side_effect=(0.0, 0.010, 0.035, 0.042, 0.045, 0.047)),
            patch.object(cv2, "cvtColor", wraps=original_convert) as convert,
        ):
            app.stream_camera_snapshot(frame)
            self.assertEqual(app._stream_camera_serial, 1)
            first_image = app._stream_camera_frame
            app.stream_camera_snapshot(frame)
            app.stream_camera_snapshot(frame)
            self.assertEqual(app._stream_camera_serial, 1)
            self.assertIs(app._stream_camera_frame, first_image)

            app.stream_camera_snapshot(frame)
            self.assertEqual(app._stream_camera_serial, 2)
            self.assertIsNot(app._stream_camera_frame, first_image)

            # A changed FPS setting must immediately use the next source
            # frame, not wait for the prior 24 FPS throttle timestamp.
            app._stream_options["frame_rate"] = "30 FPS"
            app._stream_options_updated()
            app.stream_camera_snapshot(frame)
            self.assertEqual(app._stream_camera_serial, 3)

            # Camera-off must erase the last image even within the
            # throttling interval, and permit an immediate reconnect.
            app.stream_clear_camera()
            self.assertIsNone(app._stream_camera_frame)
            self.assertIsNone(app._stream_camera_last_snapshot)
            self.assertEqual(app._stream_camera_serial, 4)
            app.stream_camera_snapshot(frame)
            self.assertEqual(app._stream_camera_serial, 5)
        self.assertEqual(convert.call_count, 4)
        self.assertEqual(app._stream_camera_frame.size, (25, 20))
        app.close_stream_mode()
        self.assertIsNone(app._stream_camera_frame)
        self.assertIsNone(app._stream_camera_last_snapshot)

    def test_stream_camera_conversion_failure_clears_old_image_and_recovers(self):
        """Optional PIL/OpenCV preview failures must be bounded and private."""
        from types import SimpleNamespace
        from unittest.mock import Mock, patch
        import cv2
        import numpy as np

        class Harness(StreamMixin):
            THEMES = THEMES

        app = Harness()
        app.theme_name = SimpleNamespace(get=lambda: "Ocean Dark")
        app.initialize_stream_mode({})
        app._stream_output_window = object()
        app._stream_last_render = ("old camera",)
        old = Image.new("RGB", (24, 18), "#ff00aa")
        app._stream_camera_frame = old
        app._stream_camera_serial = 7
        image = np.zeros((18, 24, 3), dtype=np.uint8)
        original_convert = cv2.cvtColor
        broken = [True]

        def occasionally_broken(pixels, conversion):
            if broken[0]:
                raise cv2.error(
                    "OpenCV failed on private /home/user/secret-camera-id"
                )
            return original_convert(pixels, conversion)

        with (
            patch("anything_plays.ui_stream.time.monotonic",
                  side_effect=(1.0, 1.010, 1.050)),
            patch.object(cv2, "cvtColor",
                         side_effect=occasionally_broken) as convert,
        ):
            app.stream_camera_snapshot(image)
            self.assertIsNone(app._stream_camera_frame)
            self.assertIsNone(app._stream_last_render)
            self.assertEqual(app._stream_camera_serial, 8)
            self.assertEqual(app._stream_camera_last_snapshot, 1.0)
            app.stream_camera_snapshot(image)
            self.assertEqual(convert.call_count, 1,
                             "failed optional preview must obey FPS backoff")
            broken[0] = False
            app.stream_camera_snapshot(image)
        self.assertEqual(convert.call_count, 2)
        self.assertEqual(app._stream_camera_serial, 9)
        self.assertEqual(app._stream_camera_frame.size, (24, 18))
        self.assertEqual(app._stream_camera_last_snapshot, 1.050)

    def test_native_preview_failures_do_not_escape_or_freeze_old_camera(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        import cv2
        import numpy as np

        class Harness(StreamMixin):
            THEMES = THEMES

        source = np.zeros((18, 24, 3), dtype=np.uint8)
        native_convert = cv2.cvtColor
        for problem in (RuntimeError("private device /home/rom"),
                        AttributeError("bad frame wrapper"),
                        MemoryError("allocation failed"),
                        OverflowError("native dimensions overflow")):
            with self.subTest(problem=type(problem).__name__):
                app = Harness()
                app.theme_name = SimpleNamespace(get=lambda: "Ocean Dark")
                app.initialize_stream_mode({})
                app._stream_output_window = object()
                app._stream_camera_frame = Image.new("RGB", (24, 18))
                app._stream_camera_serial = 4
                app._stream_last_render = ("stale",)
                calls = [0]

                def convert(*args):
                    calls[0] += 1
                    if calls[0] == 1:
                        raise problem
                    return native_convert(*args)

                with (
                    patch("anything_plays.ui_stream.time.monotonic",
                          side_effect=(1.0, 1.01, 1.05)),
                    patch.object(cv2, "cvtColor", side_effect=convert),
                ):
                    app.stream_camera_snapshot(source)
                    self.assertIsNone(app._stream_camera_frame)
                    self.assertIsNone(app._stream_last_render)
                    self.assertEqual(app._stream_camera_serial, 5)
                    app.stream_camera_snapshot(source)
                    self.assertEqual(calls[0], 1)
                    app.stream_camera_snapshot(source)
                self.assertEqual(calls[0], 2)
                self.assertEqual(app._stream_camera_serial, 6)
                self.assertEqual(app._stream_camera_frame.size, (24, 18))

    def test_stream_camera_snapshot_rate_policy_handles_all_three_targets(self):
        for rate in FRAME_RATES:
            target = int(rate.split()[0])
            with self.subTest(target=target):
                self.assertTrue(stream_camera_snapshot_due(None, 1.0, rate))
                self.assertFalse(stream_camera_snapshot_due(
                    1.0, 1.0 + 0.4 / target, rate
                ))
                self.assertTrue(stream_camera_snapshot_due(
                    1.0, 1.0 + 1 / target, rate
                ))
                self.assertTrue(stream_camera_snapshot_due(
                    2.0, 0.1, rate
                ))
        self.assertTrue(stream_camera_snapshot_due(None, 0.0, "invalid"))

    def test_stream_cadence_separates_refresh_ticks_from_changed_images(self):
        for target in (15, 24, 30):
            with self.subTest(target=target):
                tracker = StreamCadenceTracker()
                mode = f"{target} FPS"
                for i in range(7):
                    tracker.record_tick(
                        1.0 + i / target, mode, published=(i % 2 == 0)
                    )
                snapshot = tracker.snapshot()
                self.assertEqual(snapshot["stream_target_refresh_fps"], target)
                self.assertEqual(snapshot["stream_refresh_intervals"], 6)
                self.assertAlmostEqual(
                    snapshot["stream_observed_refresh_fps"], target, places=2
                )
                self.assertEqual(snapshot["stream_published_images"], 4)
                self.assertEqual(snapshot["stream_unchanged_ticks"], 3)
                self.assertAlmostEqual(
                    snapshot["stream_observed_publication_fps"],
                    target / 2, places=2,
                )
                self.assertNotIn("last_tick", snapshot)
                self.assertNotIn("last_published", snapshot)

    def test_stream_rate_change_resets_cadence_and_invalid_clocks_are_ignored(self):
        tracker = StreamCadenceTracker()
        tracker.record_tick(1.0, "24 FPS", published=True)
        tracker.record_tick(1.05, "24 FPS", failed=True)
        self.assertEqual(tracker.snapshot()["stream_failed_ticks"], 1)
        self.assertEqual(tracker.snapshot()["stream_publication_intervals"], 0)
        tracker.reset_for("30 FPS")
        self.assertEqual(tracker.snapshot()["stream_target_refresh_fps"], 30)
        self.assertEqual(tracker.snapshot()["stream_failed_ticks"], 0)
        self.assertEqual(tracker.snapshot()["stream_refresh_intervals"], 0)
        for value in (float("nan"), float("inf"), None, "device",
                      10**1000, -1):
            tracker.record_tick(value, "30 FPS", published=True)
        self.assertEqual(tracker.snapshot()["stream_published_images"], 0)
        tracker.record_tick(10.0, "30 FPS", published=True)
        tracker.record_tick(9.0, "30 FPS", published=True)
        self.assertEqual(tracker.snapshot()["stream_refresh_intervals"], 0)
        self.assertEqual(tracker.snapshot()["stream_published_images"], 1)
        # A suspended Tk window may resume hours later. Treat that jump
        # as a new observation segment instead of a fabricated low rate.
        tracker.record_tick(10000.0, "30 FPS", published=True)
        self.assertEqual(tracker.snapshot()["stream_refresh_intervals"], 0)
        self.assertEqual(tracker.snapshot()["stream_published_images"], 1)
        for i in range(10000):
            tracker.record_tick(10.0 + i / 30, "30 FPS", published=i % 2 == 0)
        self.assertEqual(tracker.snapshot()["stream_refresh_intervals"], 9999)
        self.assertLessEqual(len(vars(tracker)), 17)

    def test_stream_composition_p95_detects_stutter_without_trace_history(self):
        tracker = StreamCadenceTracker()
        self.assertEqual(tracker.snapshot()["stream_render_p95_bucket_code"], -1)
        for i in range(20):
            tracker.record_tick(1.0 + i / 30, "30 FPS",
                                published=i % 2 == 0, render_seconds=0.008)
        tracker.record_tick(2.0, "30 FPS", published=True,
                            render_seconds=0.600)
        m = tracker.snapshot()
        self.assertEqual(m["stream_render_samples"], 21)
        self.assertEqual(m["stream_render_p95_bucket_code"], 1)  # 5–10ms
        self.assertEqual(m["stream_render_over_budget_ticks"], 1)
        self.assertEqual(m["stream_render_max_ms"], 600)
        self.assertEqual(sum(tracker.render_histogram), 21)
        self.assertNotIn("render_histogram", m)
        tracker.record_tick(2.05, "30 FPS", published=True,
                            render_seconds=0.600)
        m = tracker.snapshot()
        self.assertEqual(m["stream_render_p95_bucket_code"], 10)  # >500ms
        self.assertEqual(m["stream_render_over_budget_ticks"], 2)
        self.assertEqual(len(tracker.render_histogram), 11)

    def test_stream_render_cost_resets_on_mode_change_and_rejects_bad_data(self):
        tracker = StreamCadenceTracker()
        tracker.record_tick(1.0, "24 FPS", render_seconds=0.050, failed=True)
        snap = tracker.snapshot()
        self.assertEqual(snap["stream_render_samples"], 1)
        self.assertEqual(snap["stream_render_over_budget_ticks"], 1)
        self.assertEqual(snap["stream_failed_ticks"], 1)
        tracker.reset_for("15 FPS")
        self.assertEqual(tracker.snapshot()["stream_render_samples"], 0)
        self.assertEqual(tracker.snapshot()["stream_render_p95_bucket_code"], -1)
        for i, bad in enumerate((
            None, -1, float("nan"), float("inf"), 10**1000, True, "secret"
        )):
            tracker.record_tick(2.0 + i / 15, "15 FPS", render_seconds=bad)
        self.assertEqual(tracker.snapshot()["stream_render_samples"], 0)
        tracker.record_tick(3.0, "15 FPS", render_seconds=0.050)
        self.assertEqual(tracker.snapshot()["stream_render_over_budget_ticks"], 0)
        self.assertEqual(tracker.snapshot()["stream_render_samples"], 1)
        self.assertEqual(tracker.snapshot()["stream_render_p95_bucket_code"], 5)

    def test_stream_tick_measures_actual_changed_image_publication(self):
        from unittest.mock import Mock, patch, call

        class Harness(StreamMixin):
            pass

        app = Harness()
        app._stream_output_window = object()
        app._closing = False
        app._stream_options = dict(DEFAULT_STREAM)
        app.root = Mock()
        app._stream_diagnostic = Mock()
        app._stream_cadence = StreamCadenceTracker()
        app._render_stream_frame = Mock(side_effect=(True, False, True))
        with patch("anything_plays.ui_stream.time.perf_counter",
                   side_effect=(1.0, 1.010, 1.040, 1.052, 1.080, 1.090)):
            for _ in range(3):
                app._stream_render_tick()
        m = app.stream_performance_snapshot()["metrics"]
        self.assertEqual(m["stream_target_refresh_fps"], 24)
        self.assertAlmostEqual(m["stream_observed_refresh_fps"], 25)
        self.assertEqual(m["stream_published_images"], 2)
        self.assertEqual(m["stream_unchanged_ticks"], 1)
        self.assertEqual(m["stream_publication_intervals"], 1)
        self.assertAlmostEqual(m["stream_observed_publication_fps"], 12.5)
        self.assertEqual(m["stream_render_samples"], 3)
        self.assertEqual(m["stream_render_over_budget_ticks"], 0)
        self.assertEqual(m["stream_render_max_ms"], 12.0)
        self.assertEqual(m["stream_render_p95_bucket_code"], 2)
        app.root.after.assert_has_calls([
            call(32, app._stream_render_tick),
            call(30, app._stream_render_tick),
            call(32, app._stream_render_tick),
        ])
        app._stream_output_window = None
        self.assertIsNone(app.stream_performance_snapshot())

    def test_pure_stacked_and_side_by_side_geometry_never_overlaps(self):
        for size, layout in (
            ((720, 1080), "DS stacked"),
            ((1280, 720), "Side by side"),
            ((360, 440), "DS stacked"),
            ((420, 500), "Side by side"),
        ):
            for share in (30, 53, 70):
                with self.subTest(size=size, layout=layout, share=share):
                    first, second = stream_panel_boxes(size, layout, share)
                    for x0, y0, x1, y1 in (first, second):
                        self.assertGreaterEqual(x0, 0)
                        self.assertGreaterEqual(y0, 0)
                        self.assertLessEqual(x1, size[0])
                        self.assertLessEqual(y1, size[1])
                        self.assertGreater(x1-x0, 95)
                        self.assertGreater(y1-y0, 90)
                    if layout == "DS stacked":
                        self.assertLess(first[3], second[1])
                    else:
                        self.assertLess(first[2], second[0])

    def test_live_game_is_on_top_and_camera_below_or_swapped(self):
        game = Image.new("RGB", (640, 480), "#e92b38")
        camera = Image.new("RGB", (640, 480), "#22d875")
        config = dict(DEFAULT_STREAM)
        output = compose_stream_output(
            game, camera, size=(720, 1080), settings=config, themes=THEMES,
            game_active=True, camera_active=True,
        )
        first, second = stream_panel_boxes(output.size)
        self.assertEqual(sample(output, first), (233, 43, 56))
        self.assertEqual(sample(output, second), (34, 216, 117))
        self.assertEqual(game.getpixel((0, 0)), (233, 43, 56))
        self.assertEqual(camera.getpixel((0, 0)), (34, 216, 117))
        config["swap_screens"] = True
        swapped = compose_stream_output(
            game, camera, size=(720, 1080), settings=config, themes=THEMES,
            game_active=True, camera_active=True,
        )
        self.assertEqual(sample(swapped, first), (34, 216, 117))
        self.assertEqual(sample(swapped, second), (233, 43, 56))

    def test_horizontal_stream_theme_and_custom_border_color(self):
        game = Image.new("RGB", (160, 144), "#e92b38")
        camera = Image.new("RGB", (320, 240), "#22d875")
        for theme in THEMES:
            with self.subTest(theme=theme):
                settings = {
                    **DEFAULT_STREAM, "layout": "Side by side",
                    "theme": theme, "border_color": "#fc9631",
                    "border_width": 10, "show_labels": False,
                }
                output = compose_stream_output(
                    game, camera, size=(1280, 720), settings=settings,
                    themes=THEMES, game_active=True, camera_active=True,
                )
                self.assertEqual(output.size, (1280, 720))
                self.assertEqual(output.getpixel((0, 0)),
                                 tuple(bytes.fromhex(THEMES[theme][0][1:])))
                first, second = stream_panel_boxes(
                    output.size, "Side by side", 53,
                )
                self.assertEqual(sample(output, first), (233, 43, 56))
                self.assertEqual(sample(output, second), (34, 216, 117))
                middle_x = (first[0] + first[2]) // 2
                self.assertEqual(output.getpixel((middle_x, first[1])),
                                 (252, 150, 49))

    def test_stream_resize_cache_preserves_pixels_and_skips_unchanged_source(self):
        from PIL import ImageChops
        from unittest.mock import patch

        game = Image.new("RGB", (160, 144), "#c3341a")
        camera = Image.new("RGB", (640, 480), "#29d492")
        camera.putpixel((310, 220), (255, 0, 0))
        cache = StreamPanelResizeCache()
        settings = dict(DEFAULT_STREAM)
        size = (720, 1080)

        def compose(g, cam, *, options=settings, cache_enabled=True,
                    active_game=True, active_camera=True):
            return compose_stream_output(
                g, cam, size=size, settings=options, themes=THEMES,
                game_active=active_game, camera_active=active_camera,
                resize_cache=cache if cache_enabled else None,
            )

        with patch("anything_plays.ui_stream._contained", wraps=_contained) as fit:
            first = compose(game, camera)
            self.assertEqual(fit.call_count, 2)
            self.assertIsNone(ImageChops.difference(
                first, compose(game, camera, cache_enabled=False)
            ).getbbox())
            self.assertEqual(fit.call_count, 4)  # uncached comparison
            same = compose(game, camera)
            self.assertEqual(fit.call_count, 4, "both fitted sources were reused")
            self.assertIsNone(ImageChops.difference(first, same).getbbox())
            new_camera = camera.copy()
            new_camera.putpixel((300, 200), (18, 70, 255))
            changed = compose(game, new_camera)
            self.assertEqual(fit.call_count, 5, "only new camera was resized")
            self.assertIsNone(ImageChops.difference(
                changed, compose(game, new_camera, cache_enabled=False)
            ).getbbox())
            self.assertEqual(fit.call_count, 7)
            # Changing colors, not panel geometry, can reuse fitted pixels.
            recolor = {**settings, "border_color": "#9a6611"}
            compose(game, new_camera, options=recolor)
            self.assertEqual(fit.call_count, 7)
            # A new panel arrangement invalidates fits, not the raw sources.
            swapped = {**settings, "swap_screens": True}
            alternate = compose(game, new_camera, options=swapped)
            self.assertEqual(fit.call_count, 9)
            self.assertIsNone(ImageChops.difference(
                alternate, compose(
                    game, new_camera, options=swapped, cache_enabled=False
                )
            ).getbbox())
        self.assertEqual(set(cache._entries), {"GAME", "CAMERA"})
        self.assertEqual(len(cache._entries), 2)
        counts = cache.snapshot()
        self.assertGreaterEqual(counts["stream_resize_cache_hits"], 5)
        self.assertEqual(counts["stream_resize_cache_misses"], 5)
        self.assertNotIn("frame", str(counts).lower())

    def test_resize_cache_clears_private_camera_when_disconnected(self):
        cache = StreamPanelResizeCache()
        game = Image.new("RGB", (80, 72), "#ba0234")
        private = Image.new("RGB", (160, 120), "#123456")
        bounds = (12, 17, 180, 200)
        cache.contained("GAME", game, bounds, nearest=True)
        cache.contained("CAMERA", private, bounds)
        self.assertIs(cache._entries["CAMERA"][0], private)
        self.assertIsNone(cache.contained("CAMERA", None, bounds))
        self.assertNotIn("CAMERA", cache._entries)
        self.assertIn("GAME", cache._entries)
        cache.clear()
        self.assertEqual(len(cache._entries), 0)

    def test_resize_cache_is_constant_memory_for_thousands_of_source_frames(self):
        cache = StreamPanelResizeCache()
        for i in range(3000):
            pixels = Image.new("RGB", (16, 12), (i % 256, 60, 180))
            cache.contained(
                "CAMERA", pixels, (5, 5, 80, 90), nearest=False
            )
            self.assertLessEqual(len(cache._entries), 1)
        summary = cache.snapshot()
        self.assertEqual(summary["stream_resize_cache_misses"], 3000)
        self.assertEqual(summary["stream_resize_cache_hits"], 0)
        self.assertEqual(len(cache._entries), 1)
        self.assertIs(cache._entries["CAMERA"][0], pixels)

    def test_camera_off_and_game_off_never_show_stale_frames(self):
        game = Image.new("RGB", (320, 240), "#e92b38")
        camera = Image.new("RGB", (320, 240), "#22d875")
        settings = dict(DEFAULT_STREAM)
        image = compose_stream_output(
            game, camera, size=(720, 1080), settings=settings,
            themes=THEMES, game_active=False, camera_active=False,
            camera_reference=False,
        )
        first, second = stream_panel_boxes(image.size)
        self.assertNotEqual(sample(image, first), (233, 43, 56))
        self.assertNotEqual(sample(image, second), (34, 216, 117))
        reference = compose_stream_output(
            None, camera, size=(720, 1080), settings=settings,
            themes=THEMES, game_active=False, camera_active=False,
            camera_reference=True,
        )
        self.assertEqual(sample(reference, second), (34, 216, 117))
        self.assertNotEqual(sample(reference, first), (233, 43, 56))

    def test_failed_camera_probe_clears_private_snapshot_without_stopping_game(self):
        """A broken/closed webcam must not freeze its last image in OBS."""
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch
        import cv2

        for problem in ("closed", "opencv", "os", "runtime"):
            with self.subTest(problem=problem):
                class Harness(StreamMixin):
                    THEMES = THEMES

                    def uses_embedded_emulator(self):
                        return False

                app = Harness()
                app.theme_name = SimpleNamespace(get=lambda: "Ocean Dark")
                app.initialize_stream_mode({})
                app.emu = SimpleNamespace(running=False)
                app.cap = MagicMock()
                if problem == "closed":
                    app.cap.isOpened.return_value = False
                else:
                    app.cap.isOpened.side_effect = {
                        "opencv": cv2.error("webcam disconnected"),
                        "os": OSError("device removed"),
                        "runtime": RuntimeError("driver failure"),
                    }[problem]
                app.reference_image = False
                app.frame = None
                app._stream_output_window = object()
                app._stream_canvas = MagicMock()
                app._stream_canvas.winfo_exists.return_value = True
                app._stream_canvas.winfo_width.return_value = 760
                app._stream_canvas.winfo_height.return_value = 980
                app._stream_canvas.create_image.return_value = 11
                app._stream_camera_frame = Image.new("RGB", (32, 32), "#ff00ff")
                app._stream_camera_serial = 4

                with (
                    patch("anything_plays.ui_stream.compose_stream_output",
                          return_value=Image.new("RGB", (760, 980))) as compose,
                    patch("anything_plays.ui_stream.ImageTk.PhotoImage"),
                ):
                    app._render_stream_frame()

                self.assertIsNone(app._stream_camera_frame)
                self.assertEqual(app._stream_camera_serial, 5)
                self.assertFalse(compose.call_args.kwargs["camera_active"])
                self.assertIsNone(compose.call_args.args[1])
                self.assertEqual(tuple(app._stream_canvas.find_all()), ())
                self.assertEqual(app._stream_canvas.create_image.call_count, 1)

    def test_stream_pil_conversion_releases_native_frame_lock(self):
        """PIL conversion must never hold up Libretro's native producer."""
        import numpy as np
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch

        class ObservedLock:
            held = False

            def __enter__(self):
                assert not self.held
                self.held = True

            def __exit__(self, exc_type, exc, tb):
                self.held = False

        lock = ObservedLock()
        source_pixels = np.full((24, 32, 3), 71, dtype=np.uint8)

        class LockedFrame:
            def __getitem__(self, key):
                assert lock.held, "native pixels must be read under lock"
                assert key == (slice(None), slice(None), slice(None, 3))
                return self

            def copy(self):
                assert lock.held, "snapshot must be copied under lock"
                return source_pixels.copy()

        class Harness(StreamMixin):
            THEMES = THEMES

            def uses_embedded_emulator(self):
                return True

        app = Harness()
        app.theme_name = SimpleNamespace(get=lambda: "Ocean Dark")
        app.initialize_stream_mode({})
        app.emu = SimpleNamespace(
            running=True, lock=lock, frame_serial=3, frame=LockedFrame(),
        )
        app._stream_output_window = object()
        app._stream_canvas = MagicMock()
        app._stream_canvas.winfo_exists.return_value = True
        app._stream_canvas.winfo_width.return_value = 760
        app._stream_canvas.winfo_height.return_value = 980
        app._stream_canvas.create_image.return_value = 11
        app.cap = None
        app.reference_image = False
        app.frame = None
        real_fromarray = Image.fromarray
        conversions = []

        def convert_without_native_lock(pixels):
            self.assertFalse(lock.held, "PIL conversion must not block core")
            self.assertFalse(np.shares_memory(pixels, source_pixels))
            conversions.append(pixels.copy())
            return real_fromarray(pixels)

        with (
            patch("anything_plays.ui_stream.Image.fromarray",
                  side_effect=convert_without_native_lock),
            patch("anything_plays.ui_stream.ImageTk.PhotoImage"),
            patch("anything_plays.ui_stream.compose_stream_output",
                  return_value=Image.new("RGB", (760, 980))),
        ):
            app._render_stream_frame()
            self.assertEqual(len(conversions), 1)
            self.assertEqual(app._stream_game_serial, 3)
            self.assertFalse(lock.held)
            # An unchanged native frame must not repeat the conversion.
            app._render_stream_frame()
            self.assertEqual(len(conversions), 1)
            app.emu.frame_serial = 4
            app._render_stream_frame()
            self.assertEqual(len(conversions), 2)
            self.assertEqual(app._stream_game_serial, 4)
        self.assertFalse(lock.held)

    def test_reference_image_remains_visible_when_no_camera_is_connected(self):
        """An intentionally selected reference image is not a stale webcam."""
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch

        class Harness(StreamMixin):
            THEMES = THEMES

            def uses_embedded_emulator(self):
                return False

        app = Harness()
        app.theme_name = SimpleNamespace(get=lambda: "Ocean Dark")
        app.initialize_stream_mode({})
        app.emu = SimpleNamespace(running=False)
        app.cap = None
        app.reference_image = True
        app.frame = object()
        app._stream_output_window = object()
        app._stream_canvas = MagicMock()
        app._stream_canvas.winfo_exists.return_value = True
        app._stream_canvas.winfo_width.return_value = 760
        app._stream_canvas.winfo_height.return_value = 980
        app._stream_canvas.create_image.return_value = 9
        reference = Image.new("RGB", (32, 32), "#32cc66")
        app._stream_camera_frame = reference
        app._stream_camera_serial = 4
        with (
            patch("anything_plays.ui_stream.compose_stream_output",
                  return_value=Image.new("RGB", (760, 980))) as compose,
            patch("anything_plays.ui_stream.ImageTk.PhotoImage"),
        ):
            app._render_stream_frame()
        self.assertIs(app._stream_camera_frame, reference)
        self.assertEqual(app._stream_camera_serial, 4)
        self.assertTrue(compose.call_args.kwargs["camera_reference"])
        self.assertFalse(compose.call_args.kwargs["camera_active"])
        self.assertIs(compose.call_args.args[1], reference)

    def test_stream_does_not_open_new_devices_or_redirect_manual_input(self):
        source = inspect.getsource(StreamMixin)
        self.assertNotIn("VideoCapture(", source)
        self.assertNotIn("Emulator(", source)
        self.assertNotIn("open_rom(", source)
        self.assertNotIn("press_button(", source)
        self.assertNotIn("activate_manual(", source)
        self.assertNotIn("start_camera(", source)
        self.assertIn("self.emu.lock", source)
        self.assertIn("self._stream_photo", source)
        self.assertIn("photo.paste(frame)", source)
        self.assertIn("self.root.after_cancel(job)", source)
        self.assertIn('self._stream_options["frame_rate"].split()[0]', source)
        self.assertIn("self.root.after(interval, self._stream_render_tick)", source)

    def test_long_session_font_caching_stays_bounded(self):
        from anything_plays.ui_stream import _font
        _font.cache_clear()
        for _ in range(100):
            _font(13, bold=True)
            _font(11)
            _font(10)
        self.assertLessEqual(_font.cache_info().currsize, 3)
        self.assertEqual(_font.cache_info().maxsize, 48)


if __name__ == "__main__":
    unittest.main()
