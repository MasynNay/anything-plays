"""3.3 late OBS publication fences under reentrant native/UI changes.

No native ROM, webcam, sound card or OBS encoder is opened. PIL and mock Tk
hooks intentionally mutate source generations while a preview is composing.
"""
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import numpy as np
from PIL import Image

from anything_plays.ui_stream import StreamMixin, StreamPanelResizeCache
from anything_plays.ui_theme import ThemeMixin


class StreamPublicationFenceTests(unittest.TestCase):
    def make_app(self, *, game=True, camera=True):
        class Harness(StreamMixin):
            THEMES = ThemeMixin.THEMES

            def uses_embedded_emulator(self):
                return True

        app = Harness()
        app.theme_name = SimpleNamespace(get=lambda: "Dark")
        app.initialize_stream_mode({})
        app.root = Mock()
        app._stream_output_window = Mock()
        app._stream_canvas = MagicMock()
        app._stream_canvas.winfo_exists.return_value = True
        app._stream_canvas.winfo_width.return_value = 760
        app._stream_canvas.winfo_height.return_value = 980
        app._stream_canvas.create_image.return_value = 14
        app.emu = SimpleNamespace(
            running=game, launching=False, frame_serial=7,
            frame=np.full((16, 24, 3), 92, dtype=np.uint8),
            lock=threading.Lock(), stop_event=threading.Event(),
        )
        app._stream_resize_cache = StreamPanelResizeCache()
        app.cap = None
        app.reference_image = camera
        app.frame = object() if camera else None
        cam = Image.new("RGB", (24, 16), "#16c9af")
        if camera:
            app._stream_camera_frame = cam
            app._stream_camera_serial = 4
            app._stream_resize_cache.contained(
                "CAMERA", cam, (0, 0, 60, 48)
            )
        return app

    def test_stop_during_native_pixel_to_pil_conversion_never_reattaches_image(self):
        app = self.make_app()
        old_game = Image.new("RGB", (24, 16), "red")
        with (
            patch("anything_plays.ui_stream.Image.fromarray",
                  side_effect=lambda pixels: self._stop_and_return(app, old_game)),
            patch("anything_plays.ui_stream.compose_stream_output") as compose,
            patch("anything_plays.ui_stream.ImageTk.PhotoImage") as photo,
        ):
            self.assertFalse(app._render_stream_frame())
        self.assertIsNone(app._stream_game_frame)
        self.assertIsNone(app._stream_game_serial)
        self.assertIsNone(app._stream_photo)
        compose.assert_not_called()
        photo.assert_not_called()
        self.assertIsNone(app._stream_last_render)

    def test_stop_during_conversion_blanks_old_obs_photo_immediately(self):
        """Rejecting a late copy must also revoke the prior OBS game photo."""
        app = self.make_app()
        previous_photo = Mock()
        app._stream_photo = previous_photo
        app._stream_canvas_item = 11
        app._stream_last_render = ("old game, still visible in OBS",)
        game = Image.new("RGB", (24, 16), "red")
        app._stream_game_frame = game
        app._stream_game_serial = 6
        app._stream_resize_cache.contained("GAME", game, (0, 0, 72, 56))
        camera = app._stream_camera_frame
        with (
            patch("anything_plays.ui_stream.Image.fromarray",
                  side_effect=lambda pixels: self._stop_and_return(app, game)),
            patch("anything_plays.ui_stream.compose_stream_output") as compose,
        ):
            self.assertFalse(app._render_stream_frame())
        compose.assert_not_called()
        self.assertIsNone(app._stream_photo)
        self.assertIsNone(app._stream_canvas_item)
        app._stream_canvas.delete.assert_called_once_with("all")
        self.assertIsNone(app._stream_game_frame)
        self.assertIsNone(app._stream_game_serial)
        self.assertNotIn("GAME", app._stream_resize_cache._entries)
        self.assertIs(app._stream_resize_cache._entries["CAMERA"][0], camera)
        self.assertIsNone(app._stream_last_render)

    def test_healthy_new_frame_during_conversion_retains_prior_photo(self):
        """A frame-serial change alone is not a Stop or privacy revocation."""
        app = self.make_app(camera=False)
        previous_photo = Mock()
        app._stream_photo = previous_photo
        app._stream_canvas_item = 12
        old_game = Image.new("RGB", (24, 16), "red")
        app._stream_game_frame = old_game
        app._stream_game_serial = 6
        app._stream_resize_cache.contained(
            "GAME", old_game, (0, 0, 72, 56)
        )
        def next_frame(pixels):
            app.emu.frame_serial += 1
            return Image.new("RGB", (24, 16), "green")
        with (
            patch("anything_plays.ui_stream.Image.fromarray",
                  side_effect=next_frame),
            patch("anything_plays.ui_stream.compose_stream_output") as compose,
        ):
            self.assertFalse(app._render_stream_frame())
        compose.assert_not_called()
        self.assertTrue(app.emu.running)
        self.assertIs(app._stream_photo, previous_photo)
        self.assertEqual(app._stream_canvas_item, 12)
        app._stream_canvas.delete.assert_not_called()
        self.assertIs(app._stream_game_frame, old_game)
        self.assertIn("GAME", app._stream_resize_cache._entries)
        self.assertIsNone(app._stream_last_render)

    def test_reopened_window_during_conversion_keeps_new_output_untouched(self):
        """An old PIL conversion cannot poison a newly reopened Stream Mode."""
        app = self.make_app(camera=False)
        new_window = Mock()
        new_canvas = MagicMock()
        new_photo = Mock()
        replacement_game = Image.new("RGB", (24, 16), "blue")
        new_cache = StreamPanelResizeCache()
        new_cache.contained("GAME", replacement_game, (0, 0, 72, 56))

        def close_and_reopen(_pixels):
            app._stream_output_window = new_window
            app._stream_canvas = new_canvas
            app._stream_photo = new_photo
            app._stream_game_frame = replacement_game
            app._stream_game_serial = 7
            app._stream_last_render = ("new output generation",)
            app._stream_resize_cache = new_cache
            return Image.new("RGB", (24, 16), "red")

        with (
            patch("anything_plays.ui_stream.Image.fromarray",
                  side_effect=close_and_reopen),
            patch("anything_plays.ui_stream.compose_stream_output") as compose,
        ):
            self.assertFalse(app._render_stream_frame())
        compose.assert_not_called()
        self.assertIs(app._stream_photo, new_photo)
        self.assertIs(app._stream_game_frame, replacement_game)
        self.assertEqual(app._stream_game_serial, 7)
        self.assertEqual(app._stream_last_render, ("new output generation",))
        self.assertIs(new_cache._entries["GAME"][0], replacement_game)
        new_canvas.delete.assert_not_called()

    @staticmethod
    def _stop_and_return(app, image):
        app.emu.stop_event.set()
        app.emu.running = False
        app.emu.frame_serial += 1
        return image

    def test_stop_during_composition_blanks_output_and_releases_only_game_fit(self):
        app = self.make_app()
        cam = app._stream_camera_frame

        def end_while_composing(*args, **kwargs):
            game_image = args[0]
            app._stream_resize_cache.contained(
                "GAME", game_image, (0, 0, 72, 56)
            )
            app.emu.stop_event.set()
            app.emu.running = False
            app.emu.frame_serial += 1
            return Image.new("RGB", (760, 980), "red")

        with (
            patch("anything_plays.ui_stream.compose_stream_output",
                  side_effect=end_while_composing),
            patch("anything_plays.ui_stream.ImageTk.PhotoImage") as photo,
        ):
            self.assertFalse(app._render_stream_frame())
        photo.assert_not_called()
        app._stream_canvas.delete.assert_called_with("all")
        self.assertIsNone(app._stream_game_frame)
        self.assertIsNone(app._stream_game_serial)
        self.assertNotIn("GAME", app._stream_resize_cache._entries)
        self.assertIs(app._stream_resize_cache._entries["CAMERA"][0], cam)
        self.assertIsNone(app._stream_last_render)
        self.assertIsNone(app._stream_photo)

    def test_disconnect_during_composition_cannot_republish_private_camera(self):
        app = self.make_app(game=False, camera=True)

        def disconnect(*_args, **_kwargs):
            app.stream_clear_camera()
            # A slow compositor could put the now-revoked camera source
            # into its cache after stream_clear_camera() evicted it.
            app._stream_resize_cache.contained(
                "CAMERA", Image.new("RGB", (16, 16), "red"),
                (0, 0, 80, 80)
            )
            return Image.new("RGB", (760, 980), "red")

        with (
            patch("anything_plays.ui_stream.compose_stream_output",
                  side_effect=disconnect),
            patch("anything_plays.ui_stream.ImageTk.PhotoImage") as photo,
        ):
            self.assertFalse(app._render_stream_frame())
        photo.assert_not_called()
        self.assertIsNone(app._stream_camera_frame)
        self.assertNotIn("CAMERA", app._stream_resize_cache._entries)
        self.assertIsNone(app._stream_photo)
        app._stream_canvas.delete.assert_called_with("all")

    def test_window_close_during_composition_cannot_recreate_photo(self):
        app = self.make_app(game=False, camera=False)
        former_window = app._stream_output_window
        with (
            patch("anything_plays.ui_stream.compose_stream_output",
                  side_effect=lambda *_args, **_kw: (
                      app.close_stream_mode(),
                      Image.new("RGB", (760, 980), "black")
                  )[1]),
            patch("anything_plays.ui_stream.ImageTk.PhotoImage") as photo,
        ):
            self.assertFalse(app._render_stream_frame())
        former_window.destroy.assert_called_once()
        photo.assert_not_called()
        self.assertIsNone(app._stream_output_window)
        self.assertIsNone(app._stream_photo)
        self.assertIsNone(app._stream_canvas)

    def test_settings_change_mid_composition_discards_old_layout(self):
        app = self.make_app(game=False, camera=False)
        def restyle(*_args, **_kwargs):
            app._stream_options["swap_screens"] = True
            return Image.new("RGB", (760, 980), "red")
        with (
            patch("anything_plays.ui_stream.compose_stream_output",
                  side_effect=restyle),
            patch("anything_plays.ui_stream.ImageTk.PhotoImage") as photo,
        ):
            self.assertFalse(app._render_stream_frame())
        photo.assert_not_called()
        self.assertIsNone(app._stream_last_render)
        app._stream_canvas.delete.assert_called_with("all")


    def test_camera_disconnect_during_first_conversion_cannot_republish(self):
        """No existing image/serial does not make an in-flight frame safe."""
        app = self.make_app(game=False, camera=False)
        raw = np.full((16, 24, 3), 80, dtype=np.uint8)
        old_serial = app._stream_camera_serial

        def disconnect(_frame, _code):
            app.stream_clear_camera()
            return np.full_like(raw, 180)

        with patch("anything_plays.ui_stream.cv2.cvtColor",
                   side_effect=disconnect):
            app.stream_camera_snapshot(raw)
        self.assertIsNone(app._stream_camera_frame)
        self.assertIsNone(app._stream_camera_last_snapshot)
        self.assertEqual(app._stream_camera_serial, old_serial)
        self.assertEqual(app._stream_camera_epoch, 1)

    def test_camera_disconnect_during_conversion_revokes_previous_photo(self):
        app = self.make_app(game=False, camera=True)
        previous = app._stream_camera_frame
        app._stream_camera_last_snapshot = None
        raw = np.full((16, 24, 3), 80, dtype=np.uint8)

        def disconnect(_frame, _code):
            app.stream_clear_camera()
            return np.full_like(raw, 180)

        with patch("anything_plays.ui_stream.cv2.cvtColor",
                   side_effect=disconnect):
            app.stream_camera_snapshot(raw)
        self.assertIsNone(app._stream_camera_frame)
        self.assertIsNone(app._stream_camera_last_snapshot)
        self.assertEqual(app._stream_camera_serial, 5)
        self.assertNotIn("CAMERA", app._stream_resize_cache._entries)
        self.assertIsNot(app._stream_camera_frame, previous)

    def test_camera_conversion_cannot_overwrite_newer_camera_generation(self):
        app = self.make_app(game=False, camera=True)
        replacement = Image.new("RGB", (24, 16), "blue")
        raw = np.full((16, 24, 3), 80, dtype=np.uint8)

        def newer_frame(_frame, _code):
            app._stream_camera_frame = replacement
            app._stream_camera_serial += 1
            app._stream_camera_last_snapshot = 91.0
            return np.full_like(raw, 180)

        with patch("anything_plays.ui_stream.cv2.cvtColor",
                   side_effect=newer_frame):
            app.stream_camera_snapshot(raw)
        self.assertIs(app._stream_camera_frame, replacement)
        self.assertEqual(app._stream_camera_serial, 5)
        self.assertEqual(app._stream_camera_last_snapshot, 91.0)

    def test_failed_old_camera_conversion_cannot_clear_reopened_output(self):
        app = self.make_app(game=False, camera=True)
        replacement = Image.new("RGB", (24, 16), "blue")
        new_window = Mock()
        raw = np.full((16, 24, 3), 80, dtype=np.uint8)

        def reopen_then_fail(_frame, _code):
            app._stream_output_window = new_window
            app._stream_camera_frame = replacement
            app._stream_camera_serial += 1
            app._stream_camera_last_snapshot = 91.0
            raise ValueError("old conversion failed")

        with patch("anything_plays.ui_stream.cv2.cvtColor",
                   side_effect=reopen_then_fail):
            app.stream_camera_snapshot(raw)
        self.assertIs(app._stream_output_window, new_window)
        self.assertIs(app._stream_camera_frame, replacement)
        self.assertEqual(app._stream_camera_serial, 5)
        self.assertEqual(app._stream_camera_last_snapshot, 91.0)


if __name__ == "__main__":
    unittest.main()
