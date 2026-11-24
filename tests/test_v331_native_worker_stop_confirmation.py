"""3.3.1: a timed-out Libretro worker must block ROM/console transitions.

Synthetic workers and fake Tk hosts. No real core, ROM, gamepad, camera,
personal settings, network, audio process or device access.
"""
from threading import Event, Lock
import unittest
from unittest.mock import Mock, patch

from anything_plays.gba_emulator import Emulator
from anything_plays.ui_library import LibraryMixin
from anything_plays.ui_profiles import ProfilesMixin


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class VideoHost:
    def __init__(self):
        self.emu = Mock()
        self.emu.lock = Lock()
        self.emu.frame = object()
        self.emu.frame_serial = 100
        self.emu.running = True
        self.emu.launching = False
        self.emu.core_path = "/synthetic/prior-core.so"
        self.emu.rom = "/synthetic/prior-game.gba"
        self.emu.find_system_core.return_value = "/synthetic/next-core.so"
        self.emu.stop.return_value = False
        self.current_rom = "/synthetic/prior-game.gba"
        self._core_install_busy = False
        self.root = Mock()
        self.game_status = Value("Playing prior game")
        self.status = Value("")
        self.game_bezel = Mock()
        self.game_canvas = Mock()
        self._game_only_canvas = Mock()
        self._stream_canvas = Mock()
        self._stream_resize_cache = Mock()
        self.game_photo = object()
        self._last_game_render = object()
        self._stream_game_frame = object()
        self._stream_photo = object()
        self._stream_camera_frame = object()
        self._stream_camera_serial = 16
        self.stop_external_emulator = Mock()
        self.deactivate_manual = Mock()
        self.stop_controls = Mock()
        self.prepare_gamepad_for_game_transition = Mock()
        self.show_library = Mock()
        self.show_playing_info = Mock()
        self.system_key = Value("gba")
        self.uses_embedded_emulator = lambda system=None: True


class NativeStopAcknowledgementTests(unittest.TestCase):
    def make_native(self):
        emulator = Emulator.__new__(Emulator)
        emulator.inputs = Mock()
        emulator.stop_event = Event()
        emulator.running = True
        emulator.launching = True
        emulator.armed = True
        emulator.thread = Mock()
        return emulator

    def test_stop_timeout_retains_live_worker_and_reports_incomplete(self):
        emu = self.make_native()
        emu.thread.is_alive.return_value = True
        worker = emu.thread
        self.assertIs(Emulator.stop(emu), False)
        self.assertIs(emu.thread, worker)
        self.assertTrue(emu.running)
        self.assertTrue(emu.launching)
        self.assertFalse(emu.armed)
        self.assertTrue(emu.stop_event.is_set())
        worker.join.assert_called_once_with(timeout=4)
        emu.inputs.release_manual.assert_called_once()
        emu.inputs.release_gamepad.assert_called_once()
        emu.inputs.disarm.assert_called_once()

    def test_finished_worker_reports_success_and_retires_live_flags(self):
        emu = self.make_native()
        emu.thread.is_alive.return_value = False
        self.assertIs(Emulator.stop(emu), True)
        self.assertIsNone(emu.thread)
        self.assertFalse(emu.running)
        self.assertFalse(emu.launching)
        self.assertTrue(emu.stop_event.is_set())
        emu.thread is None
        emu.inputs.disarm.assert_called()

    def test_stop_retry_retires_worker_only_after_real_exit(self):
        emu = self.make_native()
        emu.thread.is_alive.side_effect = [True, True, True, False]
        self.assertIs(Emulator.stop(emu), False)
        self.assertIsNotNone(emu.thread)
        self.assertIs(Emulator.stop(emu), True)
        self.assertIsNone(emu.thread)
        self.assertFalse(emu.running)
        self.assertFalse(emu.launching)

    def test_idle_stop_returns_success_without_any_worker(self):
        emu = self.make_native()
        emu.thread = None
        self.assertIs(Emulator.stop(emu), True)
        self.assertFalse(emu.running)
        self.assertFalse(emu.launching)

class UnloadHost(VideoHost, LibraryMixin):
    pass


class UnloadWaitTests(unittest.TestCase):
    def test_unload_timeout_does_not_clear_pixels_or_discard_previous_rom(self):
        app = UnloadHost()
        old_frame, camera = app.emu.frame, app._stream_camera_frame
        self.assertIs(app.unload_rom(), False)
        self.assertEqual(app.current_rom, "/synthetic/prior-game.gba")
        self.assertIs(app.emu.frame, old_frame)
        self.assertIs(app._stream_camera_frame, camera)
        self.assertEqual(app._stream_camera_serial, 16)
        self.assertIn("still shutting down", app.game_status.get())
        app.emu.stop.assert_called_once()
        app.stop_controls.assert_called_once()
        app.prepare_gamepad_for_game_transition.assert_called_once()
        app.show_library.assert_not_called()
        app.game_canvas.delete.assert_not_called()
        app._stream_resize_cache.clear.assert_not_called()

    def test_repeated_unload_after_worker_exit_clears_only_game_source(self):
        app = UnloadHost()
        camera = app._stream_camera_frame
        self.assertIs(app.unload_rom(), False)
        app.emu.stop.return_value = True
        self.assertIs(app.unload_rom(), True)
        self.assertIsNone(app.current_rom)
        self.assertIsNone(app.emu.frame)
        self.assertEqual(app.emu.frame_serial, 101)
        self.assertIsNone(app._stream_game_frame)
        self.assertIsNone(app._stream_photo)
        self.assertIs(app._stream_camera_frame, camera)
        self.assertEqual(app._stream_camera_serial, 16)
        app._stream_resize_cache.clear.assert_called_once_with("GAME")
        app.show_library.assert_called_once()

class LaunchWaitTests(unittest.TestCase):
    def test_stuck_prior_worker_prevents_new_core_path_or_rom_start(self):
        app = UnloadHost()
        old_frame = app.emu.frame
        old_game = app._stream_game_frame
        with patch("anything_plays.preview_storage.is_v32_preview",
                   return_value=False):
            self.assertIs(app.start_rom("/synthetic/next-game.gba"), False)
        self.assertEqual(app.current_rom, "/synthetic/prior-game.gba")
        self.assertEqual(app.emu.core_path, "/synthetic/prior-core.so")
        self.assertIs(app.emu.frame, old_frame)
        self.assertIs(app._stream_game_frame, old_game)
        self.assertIn("still shutting down", app.game_status.get())
        app.emu.start.assert_not_called()
        app.stop_controls.assert_called_once()
        app._stream_resize_cache.clear.assert_not_called()
        app.game_canvas.delete.assert_not_called()

    def test_worker_completes_then_new_rom_can_start_without_stale_frame(self):
        app = UnloadHost()
        camera = app._stream_camera_frame
        with patch("anything_plays.preview_storage.is_v32_preview",
                   return_value=False):
            self.assertIs(app.start_rom("/synthetic/next-game.gba"), False)
            app.emu.stop.return_value = True
            app.start_rom("/synthetic/next-game.gba")
        self.assertEqual(app.current_rom, "/synthetic/next-game.gba")
        self.assertEqual(app.emu.core_path, "/synthetic/next-core.so")
        app.emu.start.assert_called_once_with("/synthetic/next-game.gba")
        self.assertIsNone(app.emu.frame)
        self.assertIsNone(app._stream_game_frame)
        self.assertIs(app._stream_camera_frame, camera)
        app.show_playing_info.assert_called_once()

class SwitchHost(VideoHost, ProfilesMixin):
    def __init__(self):
        super().__init__()
        self.system_key = Value("snes")
        self._active_profile_system = "gba"
        self._calibration_window = None
        self._zone_label_save_job = None
        self.cfg = {"tolerance": 12}
        self.profile_store = Mock()
        self.profile_store.get.return_value = {"tolerance": 20}
        self.read_settings = Mock()
        self.refresh_settings = Mock()
        self.refresh_system_buttons = Mock()
        self.view_mode = Value("Game only")
        self.uses_embedded_emulator = lambda system=None: False
        self.set_view_mode = Mock()
        self.rom_directories = {"gba": "/synthetic/old", "snes": "/synthetic/new"}
        self.rom_directory = "/synthetic/old"
        self.system_description = Mock()
        self.update_external_setup = Mock()
        self.refresh_selected_emulator_state = Mock()
        self.show_external_placeholder = Mock()
        self.populate_inline_library = Mock()
        self.save_preferences = Mock()


class ConsoleWaitTests(unittest.TestCase):
    def test_blocked_worker_reverts_picker_and_keeps_old_system_video(self):
        app = SwitchHost()
        old_frame, camera = app.emu.frame, app._stream_camera_frame
        self.assertIs(ProfilesMixin.switch_system(app), False)
        self.assertEqual(app.system_key.get(), "gba")
        self.assertEqual(app._active_profile_system, "gba")
        self.assertEqual(app.cfg["tolerance"], 12)
        self.assertEqual(app.current_rom, "/synthetic/prior-game.gba")
        self.assertEqual(app.emu.core_path, "/synthetic/prior-core.so")
        self.assertIs(app.emu.frame, old_frame)
        self.assertIs(app._stream_camera_frame, camera)
        self.assertIn("still shutting down", app.status.get())
        app.stop_controls.assert_called_once()
        app.prepare_gamepad_for_game_transition.assert_called_once()
        app.deactivate_manual.assert_called_once()
        app.emu.stop.assert_called_once()
        app.set_view_mode.assert_not_called()
        app.show_library.assert_not_called()
        app.save_preferences.assert_not_called()

    def test_finished_worker_allows_full_console_switch(self):
        app = SwitchHost()
        camera = app._stream_camera_frame
        app.emu.stop.return_value = True
        self.assertIs(ProfilesMixin.switch_system(app), True)
        self.assertEqual(app.system_key.get(), "snes")
        self.assertEqual(app._active_profile_system, "snes")
        self.assertEqual(app.emu.system, "snes")
        self.assertEqual(app.current_rom, None)
        self.assertEqual(app.rom_directory, "/synthetic/new")
        self.assertIsNone(app.emu.frame)
        self.assertIs(app._stream_camera_frame, camera)
        app.set_view_mode.assert_called_once_with("Windowed")
        app.save_preferences.assert_called_once()


if __name__ == "__main__":
    unittest.main()
