"""3.3.1: a missing native core must not retain the old game or OBS pixels.

Only synthetic paths and mock emulator/canvas objects are used. Never opens
a ROM, native library, webcam, controller or real user preference file.
"""
from threading import Lock
import unittest
from unittest.mock import Mock, patch

from anything_plays.ui_library import LibraryMixin


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Host(LibraryMixin):
    def __init__(self, system="gamecube"):
        self.system_key = Value(system)
        self.game_status = Value("Playing old game")
        self.current_rom = "/synthetic/old-game.gba"
        self._core_install_busy = False
        self.root = Mock()
        self.game_bezel = Mock()
        self.emu = Mock()
        self.emu.rom = "/synthetic/old-game.gba"
        self.emu.lock = Lock()
        self.emu.running = False
        self.emu.launching = False
        self.emu.frame = object()
        self.emu.frame_serial = 10
        self.emu.find_system_core.return_value = None
        self.game_canvas = Mock()
        self._game_only_canvas = Mock()
        self._stream_canvas = Mock()
        self.game_photo = object()
        self._last_game_render = (10, "prior")
        self._stream_game_frame = object()
        self._stream_photo = object()
        self._stream_camera_frame = object()
        self._stream_camera_serial = 12
        self._stream_resize_cache = Mock()
        self.uses_embedded_emulator = lambda: True
        self.stop_external_emulator = Mock()
        self.prepare_gamepad_for_game_transition = Mock()
        self.deactivate_manual = Mock()
        self.stop_controls = Mock()
        self.show_library = Mock()
        self.show_playing_info = Mock()


class MissingCoreLaunchCleanupTests(unittest.TestCase):
    def _reject(self, app):
        with patch("anything_plays.preview_storage.is_v32_preview",
                   return_value=False), patch(
                       "anything_plays.ui_library.messagebox.showerror"
                   ) as error:
            app.start_rom("/synthetic/attempted-game.iso")
        error.assert_called_once()
        return error.call_args.args[1]

    def test_missing_gamecube_retires_native_game_and_obs_but_keeps_camera(self):
        app = Host()
        camera = app._stream_camera_frame
        message = self._reject(app)
        self.assertIn("Dolphin system files", message)
        self.assertIn("Repair or reinstall Anything Plays", message)
        self.assertNotIn("/synthetic/", message)
        self.assertIsNone(app.current_rom)
        self.assertTrue(app._retry_requires_rom_selection)
        self.assertIsNone(app.emu.frame)
        self.assertEqual(app.emu.frame_serial, 11)
        self.assertIsNone(app.game_photo)
        self.assertIsNone(app._stream_game_frame)
        self.assertIsNone(app._stream_photo)
        self.assertIs(app._stream_camera_frame, camera)
        self.assertEqual(app._stream_camera_serial, 12)
        app._stream_resize_cache.clear.assert_called_once_with("GAME")
        app.game_canvas.delete.assert_called_once_with("all")
        app._game_only_canvas.delete.assert_called_once_with("all")
        app._stream_canvas.delete.assert_called_once_with("all")
        app.emu.stop.assert_called_once()
        app.stop_controls.assert_called()
        app.show_library.assert_called_once()
        app.show_playing_info.assert_not_called()
        app.emu.start.assert_not_called()

    def test_active_game_keeps_video_controls_and_current_rom(self):
        app = Host("snes")
        app.emu.running = True
        prior_rom = app.current_rom
        prior_frame = app.emu.frame
        camera = app._stream_camera_frame
        prior_core = app.emu.core_path
        message = self._reject(app)
        self.assertIn("bundled emulator core", message)
        self.assertIs(app.emu.frame, prior_frame)
        self.assertIs(app._stream_camera_frame, camera)
        self.assertEqual(app.current_rom, prior_rom)
        self.assertIs(app.emu.core_path, prior_core)
        self.assertFalse(getattr(app, "_retry_requires_rom_selection", False))
        app.emu.stop.assert_not_called()
        app.prepare_gamepad_for_game_transition.assert_not_called()
        app.stop_controls.assert_not_called()
        app.deactivate_manual.assert_not_called()
        app.game_canvas.delete.assert_not_called()
        app._stream_resize_cache.clear.assert_not_called()
        app.show_library.assert_not_called()
        app.emu.start.assert_not_called()

    def test_missing_other_core_has_version_agnostic_repair_guidance(self):
        app = Host("snes")
        message = self._reject(app)
        self.assertIn("all supported console emulators", message)
        self.assertNotIn("Anything Plays 3.0", message)
        self.assertNotIn("/synthetic/", message)
        self.assertIsNone(app.current_rom)
        self.assertIn("Emulator files missing", app.game_status.get())

    def test_restart_cannot_launch_old_native_rom_after_rejected_attempt(self):
        app = Host("gba")
        self._reject(app)
        app.retry_current_rom()
        self.assertEqual(app.game_status.get(),
                         "Choose a game ROM before restarting.")
        self.assertIsNone(app.current_rom)
        app.emu.start.assert_not_called()
        app.emu.find_system_core.assert_called_once()

    def test_explicit_selection_after_repair_rearms_normal_launch(self):
        app = Host("snes")
        self._reject(app)
        app.emu.find_system_core.return_value = "/synthetic/restored-core.so"
        with patch("anything_plays.ui_library.messagebox.showerror") as error:
            app.start_rom("/synthetic/new-game.sfc")
        error.assert_not_called()
        self.assertFalse(app._retry_requires_rom_selection)
        self.assertEqual(app.current_rom, "/synthetic/new-game.sfc")
        app.emu.start.assert_called_once_with("/synthetic/new-game.sfc")
        self.assertEqual(app.emu.core_path, "/synthetic/restored-core.so")
        app.show_playing_info.assert_called_once()

    def test_destroyed_decorative_bezel_does_not_keep_missing_game_active(self):
        app = Host("gamecube")
        app.game_bezel.set_active.side_effect = RuntimeError("Tk destroyed")
        self._reject(app)
        self.assertIsNone(app.current_rom)
        self.assertIsNone(app.emu.frame)
        app.emu.stop.assert_called_once()
        app.show_library.assert_called_once()


if __name__ == "__main__":
    unittest.main()
