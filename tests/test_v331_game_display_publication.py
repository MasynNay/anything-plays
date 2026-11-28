"""3.3.1: native game images cannot republish after Stop, ROM replacement or view switch.

PIL frames and Tk objects are synthetic. Does not load a ROM, launch a
native core, open a webcam, play sound or capture the user's screen.
"""
import threading
import unittest
from unittest.mock import Mock, patch

import numpy as np

from anything_plays.ui_gameplay import GameplayMixin


class FakeGameDisplay(GameplayMixin):
    def __init__(self):
        self.emu = Mock()
        self.emu.lock = threading.Lock()
        self.emu.frame = np.full((4, 6, 3), 41, dtype=np.uint8)
        self.emu.frame_serial = 11
        self.emu.session_generation = 5
        self.emu.running = True
        self.emu.launching = False
        self.emu.stop_event = threading.Event()
        self._closing = False
        self.game_canvas = self.make_canvas()
        self._game_only_canvas = None
        self.game_photo = None
        self._last_game_render = None
        self._game_image_item = None
        self._game_image_canvas = None

    @staticmethod
    def make_canvas():
        c = Mock()
        c.winfo_width.return_value = 320
        c.winfo_height.return_value = 240
        c.create_image.return_value = 32
        c.type.return_value = "image"
        return c

    def stop_native(self):
        self.emu.stop_event.set()
        with self.emu.lock:
            self.emu.running = False
            self.emu.frame = None
            self.emu.frame_serial += 1
        self.game_photo = None
        self._last_game_render = None
        self._game_image_item = None
        self._game_image_canvas = None

    def restart_native(self):
        with self.emu.lock:
            self.emu.session_generation += 1
            self.emu.frame_serial += 1
            self.emu.frame = np.full((4, 6, 3), 97, dtype=np.uint8)
            self.emu.running = True
            self.emu.launching = False
        self.emu.stop_event.clear()
        self.game_photo = None
        self._last_game_render = None
        self._game_image_item = None
        self._game_image_canvas = None


class NativeGameFramePublicationFenceTests(unittest.TestCase):
    def test_normal_main_window_uses_one_image_item_and_no_stale_redraw(self):
        app = FakeGameDisplay()
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage") as make:
            app.draw_game()
            app.draw_game()  # unchanged frame must not churn PIL/Tcl
        make.assert_called_once()
        app.game_canvas.create_image.assert_called_once()
        self.assertEqual(app._last_game_render[0], 11)
        self.assertIs(app.game_photo, make.return_value)

    def test_healthy_next_native_frame_reuses_photo_and_canvas_item(self):
        app = FakeGameDisplay()
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage") as make:
            make.return_value.width.return_value = 320
            make.return_value.height.return_value = 213
            app.draw_game()
            with app.emu.lock:
                app.emu.frame = np.full((4, 6, 3), 72, dtype=np.uint8)
                app.emu.frame_serial += 1
            app.draw_game()
        make.assert_called_once()
        make.return_value.paste.assert_called_once()
        app.game_canvas.create_image.assert_called_once()
        self.assertEqual(app.game_canvas.itemconfigure.call_count, 1)
        self.assertEqual(app._last_game_render[0], 12)

    def test_stop_during_pil_resize_never_creates_native_photo(self):
        app = FakeGameDisplay()
        fake = Mock()
        fake.resize.side_effect = lambda *_a, **_k: (app.stop_native(), fake)[1]
        with (patch("anything_plays.ui_gameplay.Image.fromarray",
                    return_value=fake),
              patch("anything_plays.ui_gameplay.ImageTk.PhotoImage") as make):
            app.draw_game()
        make.assert_not_called()
        app.game_canvas.create_image.assert_not_called()
        self.assertIsNone(app.game_photo)

    def test_canvas_switch_during_resize_does_not_write_old_surface(self):
        app = FakeGameDisplay()
        old = app.game_canvas
        new = app.make_canvas()
        fake = Mock()
        fake.resize.side_effect = lambda *_a, **_k: (
            setattr(app, "_game_only_canvas", new), fake
        )[1]
        with (patch("anything_plays.ui_gameplay.Image.fromarray",
                    return_value=fake),
              patch("anything_plays.ui_gameplay.ImageTk.PhotoImage") as make):
            app.draw_game()
        make.assert_not_called()
        old.create_image.assert_not_called()
        new.create_image.assert_not_called()
        self.assertIsNone(app._last_game_render)

    def test_close_during_resize_does_not_publish(self):
        app = FakeGameDisplay()
        fake = Mock()
        fake.resize.side_effect = lambda *_a, **_k: (
            setattr(app, "_closing", True), fake
        )[1]
        with (patch("anything_plays.ui_gameplay.Image.fromarray",
                    return_value=fake),
              patch("anything_plays.ui_gameplay.ImageTk.PhotoImage") as make):
            app.draw_game()
        make.assert_not_called()
        app.game_canvas.create_image.assert_not_called()

    def test_rom_restart_during_photo_creation_discards_old_pixels(self):
        app = FakeGameDisplay()
        def restart(_frame):
            app.restart_native()
            return Mock()
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage",
                   side_effect=restart):
            app.draw_game()
        app.game_canvas.create_image.assert_not_called()
        self.assertIsNone(app.game_photo)
        self.assertIsNone(app._last_game_render)
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage") as make:
            app.draw_game()
        make.assert_called_once()
        self.assertEqual(app._last_game_render[0], 12)

    def test_healthy_new_frame_during_conversion_allows_owned_snapshot(self):
        app = FakeGameDisplay()
        before = app.emu.frame
        photo = Mock()
        def newer_frame(_frame):
            with app.emu.lock:
                app.emu.frame = np.full((4, 6, 3), 99, dtype=np.uint8)
                app.emu.frame_serial += 1
            return photo
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage",
                   side_effect=newer_frame):
            app.draw_game()
        app.game_canvas.create_image.assert_called_once()
        self.assertIs(app.game_photo, photo)
        self.assertEqual(app._last_game_render[0], 11)
        self.assertEqual(app.emu.frame_serial, 12)
        self.assertIsNot(app.emu.frame, before)

    def test_continuous_native_publication_cannot_starve_preview(self):
        app = FakeGameDisplay()
        photo = Mock()
        photo.width.return_value = 320
        photo.height.return_value = 213

        def advance(*args, **kwargs):
            with app.emu.lock:
                app.emu.frame_serial += 1
                app.emu.frame = np.full((4, 6, 3), 99, dtype=np.uint8)

        def create(_image):
            advance()
            return photo

        photo.paste.side_effect = advance
        app.game_canvas.coords.side_effect = advance
        app.game_canvas.itemconfigure.side_effect = advance
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage",
                   side_effect=create) as make:
            for _ in range(300):
                captured = app.emu.frame_serial
                app.draw_game()
                self.assertEqual(app._last_game_render[0], captured)
                self.assertGreater(app.emu.frame_serial, captured)
            make.assert_called_once()
        app.game_canvas.create_image.assert_called_once()
        self.assertEqual(photo.paste.call_count, 299)
        self.assertEqual(app.game_canvas.itemconfigure.call_count, 299)

    def test_newer_serial_with_different_generation_is_rejected(self):
        app = FakeGameDisplay()
        def switch(_image):
            app.restart_native()
            return Mock()
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage",
                   side_effect=switch):
            app.draw_game()
        app.game_canvas.create_image.assert_not_called()
        self.assertIsNone(app.game_photo)

    def test_backwards_serial_is_rejected_even_with_same_generation(self):
        app = FakeGameDisplay()
        def rewind(_image):
            with app.emu.lock:
                app.emu.frame_serial -= 1
            return Mock()
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage",
                   side_effect=rewind):
            app.draw_game()
        app.game_canvas.create_image.assert_not_called()
        self.assertIsNone(app.game_photo)

    def test_generationless_adapter_keeps_strict_serial_fence(self):
        app = FakeGameDisplay()
        app.emu.session_generation = None
        def advance(_image):
            with app.emu.lock:
                app.emu.frame_serial += 1
            return Mock()
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage",
                   side_effect=advance):
            app.draw_game()
        app.game_canvas.create_image.assert_not_called()
        self.assertIsNone(app.game_photo)

    def test_stop_during_existing_photo_paste_does_not_reattach(self):
        app = FakeGameDisplay()
        current = Mock()
        current.width.return_value = 320
        current.height.return_value = 213
        app.game_photo = current
        current.paste.side_effect = lambda _image: app.stop_native()
        app.draw_game()
        current.paste.assert_called_once()
        app.game_canvas.create_image.assert_not_called()
        app.game_canvas.coords.assert_not_called()
        self.assertIsNone(app.game_photo)

    def test_stop_inside_canvas_type_is_checked_before_deleting(self):
        app = FakeGameDisplay()
        app._game_image_item = 5
        app._game_image_canvas = app.game_canvas
        app.game_canvas.type.side_effect = lambda _id: (
            app.stop_native(), "image"
        )[1]
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage"):
            app.draw_game()
        app.game_canvas.delete.assert_not_called()
        app.game_canvas.coords.assert_not_called()
        self.assertIsNone(app.game_photo)

    def test_stop_inside_canvas_delete_prevents_image_creation(self):
        app = FakeGameDisplay()
        app.game_canvas.delete.side_effect = lambda _which: app.stop_native()
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage"):
            app.draw_game()
        app.game_canvas.create_image.assert_not_called()
        self.assertIsNone(app.game_photo)

    def test_stop_inside_create_image_removes_only_stale_item(self):
        app = FakeGameDisplay()
        app.game_canvas.create_image.side_effect = lambda *_a, **_k: (
            app.stop_native(), 98
        )[1]
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage"):
            app.draw_game()
        self.assertEqual(
            [call.args for call in app.game_canvas.delete.call_args_list],
            [("all",), (98,)],
        )
        self.assertIsNone(app.game_photo)
        self.assertIsNone(app._game_image_item)

    def test_stale_item_cleanup_failure_is_optional(self):
        app = FakeGameDisplay()
        app.game_canvas.create_image.side_effect = lambda *_a, **_k: (
            app.stop_native(), 98
        )[1]
        def reject_item(item):
            if item == 98:
                raise RuntimeError("PRIVATE destroyed Tk canvas path")
        app.game_canvas.delete.side_effect = reject_item
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage"):
            app.draw_game()
        self.assertIsNone(app.game_photo)

    def test_stop_during_canvas_coords_does_not_reconfigure(self):
        app = FakeGameDisplay()
        app._game_image_canvas = app.game_canvas
        app._game_image_item = 8
        app.game_photo = Mock()
        app.game_photo.width.return_value = 320
        app.game_photo.height.return_value = 213
        app.game_canvas.coords.side_effect = lambda *_a: app.stop_native()
        app.draw_game()
        app.game_canvas.itemconfigure.assert_not_called()
        self.assertIsNone(app.game_photo)

    def test_stop_during_canvas_itemconfigure_does_not_commit_revision(self):
        app = FakeGameDisplay()
        app._game_image_canvas = app.game_canvas
        app._game_image_item = 8
        app.game_photo = Mock()
        app.game_photo.width.return_value = 320
        app.game_photo.height.return_value = 213
        app.game_canvas.itemconfigure.side_effect = (
            lambda *_a, **_k: app.stop_native()
        )
        app.draw_game()
        self.assertIsNone(app.game_photo)
        self.assertIsNone(app._last_game_render)

    def test_stop_requested_before_draw_with_running_flag_stale(self):
        app = FakeGameDisplay()
        app.emu.stop_event.set()  # worker still reports running=True
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage") as make:
            app.draw_game()
        make.assert_not_called()
        app.game_canvas.create_image.assert_not_called()

    def test_replaced_game_generation_blocks_pixels_even_if_serial_reused(self):
        app = FakeGameDisplay()
        def replace(_frame):
            with app.emu.lock:
                app.emu.session_generation += 1
                app.emu.frame = np.full((4, 6, 3), 8, dtype=np.uint8)
                # Simulates a third-party test adapter reusing frame serial.
            return Mock()
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage",
                   side_effect=replace):
            app.draw_game()
        self.assertIsNone(app.game_photo)
        app.game_canvas.create_image.assert_not_called()

    def test_game_only_canvas_switch_while_photo_pastes_is_fenced(self):
        app = FakeGameDisplay()
        old = app.make_canvas()
        app._game_only_canvas = old
        app._game_image_canvas = old
        app._game_image_item = 8
        photo = Mock()
        photo.width.return_value = 320
        photo.height.return_value = 213
        app.game_photo = photo
        photo.paste.side_effect = lambda _img: setattr(
            app, "_game_only_canvas", None
        )
        app.draw_game()
        old.coords.assert_not_called()
        old.itemconfigure.assert_not_called()
        app.game_canvas.create_image.assert_not_called()

    def test_500_frame_session_keeps_one_tk_item_and_no_extra_photos(self):
        app = FakeGameDisplay()
        with patch("anything_plays.ui_gameplay.ImageTk.PhotoImage") as make:
            make.return_value.width.return_value = 320
            make.return_value.height.return_value = 213
            for number in range(500):
                with app.emu.lock:
                    app.emu.frame_serial += 1
                app.draw_game()
        self.assertEqual(make.call_count, 1)
        self.assertEqual(app.game_canvas.create_image.call_count, 1)
        self.assertEqual(app.game_canvas.itemconfigure.call_count, 499)
        self.assertEqual(app._last_game_render[0], 511)


if __name__ == "__main__":
    unittest.main()
