"""3.1 stream capture composition and settings, without real camera or ROMs."""
from __future__ import annotations

import inspect
import unittest

from PIL import Image

from anything_plays.ui_stream import (
    DEFAULT_STREAM, LAYOUTS, StreamMixin, compose_stream_output,
    stream_panel_boxes, validate_stream_settings,
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
