"""Game stop cleanup uses the same data path for unload and console switch."""

import threading
import unittest
from unittest.mock import Mock, patch

from anything_plays.game_display_lifecycle import clear_game_video
from anything_plays.ui_library import LibraryMixin


class VideoHost:
    def __init__(self):
        self.emu = Mock()
        self.emu.lock = threading.Lock()
        self.emu.frame = object()
        self.emu.frame_serial = 12
        self.game_canvas = Mock()
        self._game_only_canvas = Mock()
        self._stream_canvas = Mock()
        self.game_photo = object()
        self._last_game_render = (12, "canvas")
        self._game_image_item = 7
        self._game_image_canvas = object()
        self._stream_game_frame = object()
        self._stream_game_serial = 12
        self._stream_last_render = ("prior",)
        self._stream_canvas_item = 11
        self._stream_photo = object()
        self._stream_camera_frame = object()
        self._stream_camera_serial = 4
        self.game_bezel = Mock()


class LibraryHost(VideoHost, LibraryMixin):
    def __init__(self):
        super().__init__()
        self.current_rom = "/synthetic/previous-game.gba"
        self.stop_external_emulator = Mock()
        self.deactivate_manual = Mock()
        self.stop_controls = Mock()
        self.game_status = Mock()
        self.show_library = Mock()
        self.show_playing_info = Mock()
        self.uses_embedded_emulator = lambda: True
        self.system_key = Mock()
        self.system_key.get.return_value = "gba"
        self.prepare_gamepad_for_game_transition = Mock()
        self.emu.find_system_core.return_value = "/synthetic/test-core.so"
        self.root = Mock()


class GameVideoLifecycleTests(unittest.TestCase):
    def check_cleared(self, app):
        self.assertIsNone(app.emu.frame)
        self.assertEqual(app.emu.frame_serial, 13)
        self.assertIsNone(app.game_photo)
        self.assertIsNone(app._last_game_render)
        self.assertIsNone(app._game_image_item)
        self.assertIsNone(app._game_image_canvas)
        self.assertIsNone(app._stream_game_frame)
        self.assertIsNone(app._stream_game_serial)
        self.assertIsNone(app._stream_last_render)
        self.assertIsNone(app._stream_canvas_item)
        self.assertIsNone(app._stream_photo)
        app.game_canvas.delete.assert_called_once_with("all")
        app._game_only_canvas.delete.assert_called_once_with("all")
        app._stream_canvas.delete.assert_called_once_with("all")
        app.game_bezel.set_active.assert_called_once_with(False)
        self.assertIsNotNone(app._stream_camera_frame)
        self.assertEqual(app._stream_camera_serial, 4)

    def test_shared_cleanup_clears_every_game_surface(self):
        app = VideoHost()
        clear_game_video(app)
        self.check_cleared(app)

    def test_real_library_unload_invokes_shared_cleanup_after_stop(self):
        app = LibraryHost()
        app.emu.stop.side_effect = lambda: None
        app.unload_rom()
        self.check_cleared(app)
        self.assertIsNone(app.current_rom)
        app.emu.stop.assert_called_once()
        app.stop_controls.assert_called_once()
        app.deactivate_manual.assert_called_once()
        app.show_library.assert_called_once()

    def test_repeated_same_console_rom_switches_prepare_gamepad_first(self):
        app = LibraryHost()
        paths = [f"/synthetic/test-{number}.gba" for number in range(8)]
        for number, path in enumerate(paths, 1):
            app.start_rom(path)
            self.assertEqual(app.current_rom, path)
            self.assertEqual(app.prepare_gamepad_for_game_transition.call_count,
                             number)
            self.assertEqual(app.emu.start.call_count, number)
            self.assertEqual(app.emu.start.call_args.args, (path,))
            app.stop_controls.assert_called()
        self.assertEqual(app.show_playing_info.call_count, len(paths))

    def test_first_launch_does_not_clear_nonexistent_render(self):
        app = LibraryHost()
        app.game_photo = None
        app._last_game_render = None
        app._stream_game_frame = None
        app._stream_photo = None
        app.start_rom("/synthetic/first.gba")
        app.emu.start.assert_called_once_with("/synthetic/first.gba")
        app.game_canvas.delete.assert_not_called()
        self.assertEqual(
            [call.args for call in app.game_bezel.set_active.call_args_list],
            [(False,), (True,)],
        )

    def test_rom_replacement_clears_old_frame_before_native_start(self):
        app = LibraryHost()
        app.emu.running = True
        camera = app._stream_camera_frame
        order = []
        app.emu.stop.side_effect = lambda: order.append("native stop")

        def start_new(path):
            order.append("native start")
            self.assertEqual(path, "/synthetic/replacement.gba")
            self.assertIsNone(app.emu.frame)
            self.assertIsNone(app.game_photo)
            self.assertIsNone(app._stream_game_frame)
            self.assertIsNone(app._stream_photo)
            self.assertIs(app._stream_camera_frame, camera)

        app.emu.start.side_effect = start_new
        app.start_rom("/synthetic/replacement.gba")
        self.assertEqual(order, ["native stop", "native start"])
        self.assertEqual(app.emu.frame_serial, 13)
        app.game_canvas.delete.assert_called_with("all")
        app._stream_canvas.delete.assert_called_with("all")

    def test_repeated_rom_replacement_does_not_retain_prior_pixels(self):
        app = LibraryHost()
        for index in range(6):
            app.emu.running = True
            app.emu.frame = object()
            app.game_photo = object()
            app._stream_game_frame = object()
            app._stream_photo = object()
            app.start_rom(f"/synthetic/replacement-{index}.gba")
            self.assertIsNone(app.emu.frame)
            self.assertIsNone(app.game_photo)
            self.assertIsNone(app._stream_game_frame)
            self.assertIsNone(app._stream_photo)
        self.assertEqual(app.emu.frame_serial, 18)
        self.assertEqual(app.emu.stop.call_count, 6)
        self.assertEqual(app._stream_canvas.delete.call_count, 6)

    def test_fresh_launch_survives_destroyed_cosmetic_bezel(self):
        """Bezel failures cannot turn a valid native launch into an error."""
        class NativeBezelFailure(Exception):
            pass

        app = LibraryHost()
        app.game_photo = None
        app._last_game_render = None
        app._stream_game_frame = None
        app._stream_photo = None
        app.game_bezel.set_active.side_effect = NativeBezelFailure("expired")
        app.start_rom("/synthetic/new-first.gba")
        app.emu.start.assert_called_once_with("/synthetic/new-first.gba")
        app.show_playing_info.assert_called_once()
        self.assertEqual(app.current_rom, "/synthetic/new-first.gba")
        self.assertIn("Starting", app.game_status.set.call_args.args[0])

    def test_stable_missing_core_keeps_prior_game_intact(self):
        app = LibraryHost()
        app.emu.running = True
        frame = app.emu.frame
        previous_stream = app._stream_game_frame
        app.emu.find_system_core.return_value = None
        with patch("anything_plays.preview_storage.is_v32_preview",
                   return_value=False), patch(
                       "anything_plays.ui_library.messagebox.showerror"
                   ):
            app.start_rom("/synthetic/missing-core.gba")
        # A failed lookup must not stop a still-playing title. The separate
        # limited-preview missing-core path still unloads as before.
        self.assertIs(app.emu.frame, frame)
        self.assertIs(app._stream_game_frame, previous_stream)
        app.emu.stop.assert_not_called()
        app.emu.start.assert_not_called()
        self.assertIn("A bundled emulator core is missing",
                      app.game_status.set.call_args.args[0])

    def test_rom_unload_disarms_gamepad_before_stop(self):
        app = LibraryHost()
        sequence = []
        app.prepare_gamepad_for_game_transition.side_effect = (
            lambda: sequence.append("controller release")
        )
        app.emu.stop.side_effect = lambda: sequence.append("native stop")
        app.unload_rom()
        self.assertEqual(sequence, ["controller release", "native stop"])

    def test_closed_secondary_windows_do_not_prevent_unloading(self):
        import tkinter as tk

        app = LibraryHost()
        app._game_only_canvas.delete.side_effect = tk.TclError("destroyed")
        app._stream_canvas.delete.side_effect = tk.TclError("destroyed")
        app.unload_rom()
        self.assertIsNone(app.current_rom)
        self.assertIsNone(app.emu.frame)
        self.assertIsNone(app._stream_game_frame)
        app.game_canvas.delete.assert_called_once_with("all")

    def test_rom_cleanup_evicts_only_old_game_resize_cache_pixels(self):
        """No hidden PIL cache keeps private ROM frames after game unload."""
        from PIL import Image
        from anything_plays.ui_stream import StreamPanelResizeCache

        app = VideoHost()
        cache = StreamPanelResizeCache()
        game = Image.new("RGB", (24, 18), "#b50018")
        camera = Image.new("RGB", (24, 18), "#0bb59c")
        cache.contained("GAME", game, (0, 0, 72, 48))
        cache.contained("CAMERA", camera, (0, 0, 72, 48))
        self.assertEqual(set(cache._entries), {"GAME", "CAMERA"})
        app._stream_resize_cache = cache

        clear_game_video(app)
        self.assertIs(app._stream_resize_cache, cache)
        self.assertNotIn("GAME", cache._entries)
        self.assertIn("CAMERA", cache._entries)
        self.assertIs(cache._entries["CAMERA"][0], camera)
        self.assertIsNone(app._stream_game_frame)
        self.assertIsNone(app._stream_photo)

    def test_faulty_resize_cache_drops_all_entries_but_preserves_live_camera(self):
        """A misbehaving optional cache must not retain old game pixels."""
        app = VideoHost()
        live_camera = app._stream_camera_frame
        app._stream_resize_cache = Mock()
        app._stream_resize_cache.clear.side_effect = RuntimeError(
            "driver private path /home/user/rom-name"
        )
        clear_game_video(app)
        self.assertIsNone(app._stream_resize_cache)
        self.assertIs(app._stream_camera_frame, live_camera)
        self.assertIsNone(app._stream_game_frame)
        self.assertIsNone(app._stream_photo)
        app._stream_canvas.delete.assert_called_once_with("all")

    def test_destroyed_main_canvas_does_not_leave_private_stream_frame(self):
        """Main Tk destruction must not stop clearing OBS and other views."""
        import tkinter as tk

        app = VideoHost()
        retained_camera = app._stream_camera_frame
        app.game_canvas.delete.side_effect = tk.TclError("main destroyed")
        clear_game_video(app)
        self.assertIsNone(app.emu.frame)
        self.assertEqual(app.emu.frame_serial, 13)
        self.assertIsNone(app._stream_game_frame)
        self.assertIsNone(app._stream_photo)
        self.assertIsNone(app._stream_last_render)
        app._game_only_canvas.delete.assert_called_once_with("all")
        app._stream_canvas.delete.assert_called_once_with("all")
        self.assertIs(app._stream_camera_frame, retained_camera)
        app.game_bezel.set_active.assert_called_once_with(False)

    def test_optional_widget_failures_are_isolated_before_new_rom_launch(self):
        """No optional widget exception can preserve stopped game pixels."""
        class PrivateNativeWidget(Exception):
            pass

        app = LibraryHost()
        app.emu.running = True
        app.game_canvas.delete.side_effect = PrivateNativeWidget(
            "video device /home/private/serial-ABC"
        )
        app._game_only_canvas.delete.side_effect = RuntimeError("gone")
        app._stream_canvas.delete.side_effect = OSError("window detached")
        app.game_bezel.set_active.side_effect = PrivateNativeWidget("bezel")
        camera = app._stream_camera_frame
        app.emu.stop.side_effect = lambda: None

        def check_new_game(path):
            self.assertEqual(path, "/synthetic/restarted.gba")
            self.assertIsNone(app.emu.frame)
            self.assertIsNone(app.game_photo)
            self.assertIsNone(app._stream_photo)
            self.assertIsNone(app._stream_game_frame)
            self.assertIsNone(app._stream_game_serial)
            self.assertIsNone(app._stream_last_render)
            self.assertIs(app._stream_camera_frame, camera)

        app.emu.start.side_effect = check_new_game
        app.start_rom("/synthetic/restarted.gba")
        app.game_canvas.delete.assert_called_once_with("all")
        app._game_only_canvas.delete.assert_called_once_with("all")
        app._stream_canvas.delete.assert_called_once_with("all")
        app.emu.start.assert_called_once_with("/synthetic/restarted.gba")

    def test_native_and_stream_frames_are_retired_before_any_canvas_deletion(self):
        """Reentrant widget callbacks cannot observe old game image refs."""
        app = VideoHost()
        retained_camera = app._stream_camera_frame
        call_order = []

        def inspect(canvas):
            call_order.append(canvas)
            self.assertIsNone(app.emu.frame)
            self.assertIsNone(app.game_photo)
            self.assertIsNone(app._stream_photo)
            self.assertIsNone(app._stream_game_frame)
            self.assertIsNone(app._stream_game_serial)
            self.assertIsNone(app._stream_last_render)
            self.assertIs(app._stream_camera_frame, retained_camera)

        app.game_canvas.delete.side_effect = lambda *args: inspect("main")
        app._game_only_canvas.delete.side_effect = (
            lambda *args: inspect("game only")
        )
        app._stream_canvas.delete.side_effect = lambda *args: inspect("stream")
        clear_game_video(app)
        self.assertEqual(call_order, ["main", "game only", "stream"])

    def test_double_cleanup_is_idempotent_and_never_touches_camera(self):
        app = VideoHost()
        camera = app._stream_camera_frame
        clear_game_video(app)
        clear_game_video(app)
        self.assertIsNone(app.emu.frame)
        self.assertEqual(app.emu.frame_serial, 14)
        self.assertIs(app._stream_camera_frame, camera)
        self.assertEqual(app._stream_camera_serial, 4)


if __name__ == "__main__":
    unittest.main()
