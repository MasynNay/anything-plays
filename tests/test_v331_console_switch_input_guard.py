"""3.3.1: failed console profile changes must not disarm a live game.

Headless mocks represent an active camera-controlled native game, ROM shelf,
Tk widgets and OBS output. No ROM, device, video or personal settings opened.
"""
from copy import deepcopy
from threading import Lock
from unittest import TestCase
from unittest.mock import Mock

from anything_plays.ui_profiles import ProfilesMixin


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeStore:
    def __init__(self):
        self.calls = []
        self.failure = None

    def get(self, key):
        if self.failure == "load":
            raise OSError("private offline profile path")
        if key == "snes":
            return {"mapping": {"A": "A"}, "tolerance": 30}
        raise AssertionError("wrong destination")

    def put(self, key, value):
        self.calls.append((key, deepcopy(value)))
        if self.failure == "save":
            raise OSError("private full disk")


class Host:
    def __init__(self):
        self._active_profile_system = "gb"
        self.system_key = Value("snes")  # Combobox has already selected SNES.
        self.cfg = {"mapping": {"A": "B"}, "tolerance": 18}
        self.status = Value("Camera object controls active")
        self._calibration_window = None
        self._zone_label_save_job = None
        self.root = Mock()
        self.profile_store = FakeStore()
        self.read_settings = Mock()
        self.refresh_settings = Mock()
        self.refresh_system_buttons = Mock()
        self.stop_controls = Mock()
        self.prepare_gamepad_for_game_transition = Mock()
        self.deactivate_manual = Mock()
        self.close_camera_calibration = Mock()
        self.uses_embedded_emulator = lambda _system: True
        self.view_mode = Value("Windowed")
        self.set_view_mode = Mock()

        self.current_rom = "/synthetic/old.gb"
        self.emu = Mock()
        self.emu.lock = Lock()
        self.emu.frame = object()
        self.emu.frame_serial = 5
        self.emu.system = "gb"
        self.emu.core_path = "/synthetic/old-core.so"
        self.emu.find_system_core.return_value = "/synthetic/new-core.so"
        self.stop_external_emulator = Mock()
        self.game_canvas = Mock()
        self._game_only_canvas = Mock()
        self._stream_canvas = Mock()
        self.game_photo = object()
        self._last_game_render = (5, "old")
        self._stream_game_frame = object()
        self._stream_photo = object()
        self._stream_camera_frame = object()
        self._stream_camera_serial = 11
        self._stream_resize_cache = Mock()
        self.game_bezel = Mock()

        self.rom_directories = {
            "gb": "/synthetic/gb",
            "snes": "/synthetic/snes",
        }
        self.rom_directory = self.rom_directories["gb"]
        self.system_description = Mock()
        self.update_external_setup = Mock()
        self.refresh_selected_emulator_state = Mock()
        self.show_external_placeholder = Mock()
        self.game_status = Value("Playing old game")
        self.show_library = Mock()
        self.populate_inline_library = Mock()
        self.save_preferences = Mock()

    def assert_not_disarmed(self, testcase, previous_frame, previous_camera):
        testcase.assertEqual(self.system_key.get(), "gb")
        testcase.assertEqual(self._active_profile_system, "gb")
        testcase.assertEqual(self.current_rom, "/synthetic/old.gb")
        testcase.assertIs(self.emu.frame, previous_frame)
        testcase.assertIs(self._stream_camera_frame, previous_camera)
        testcase.assertEqual(self.emu.core_path, "/synthetic/old-core.so")
        testcase.assertEqual(self.emu.system, "gb")
        self.stop_controls.assert_not_called()
        self.prepare_gamepad_for_game_transition.assert_not_called()
        self.deactivate_manual.assert_not_called()
        self.emu.stop.assert_not_called()
        self.stop_external_emulator.assert_not_called()
        self._stream_resize_cache.clear.assert_not_called()
        self.game_canvas.delete.assert_not_called()
        self._stream_canvas.delete.assert_not_called()
        self.show_library.assert_not_called()
        self.save_preferences.assert_not_called()


class SwitchInputSafetyTests(TestCase):
    def test_failed_previous_profile_save_leaves_live_inputs_and_video_alone(self):
        app = Host()
        frame, camera = app.emu.frame, app._stream_camera_frame
        app.profile_store.failure = "save"
        self.assertFalse(ProfilesMixin.switch_system(app))
        app.assert_not_disarmed(self, frame, camera)
        self.assertEqual(app.cfg["tolerance"], 18)
        self.assertIn("Switch canceled", app.status.get())
        self.assertNotIn("private", app.status.get())
        self.assertEqual(len(app.profile_store.calls), 1)

    def test_failed_destination_load_does_not_pause_active_game(self):
        app = Host()
        frame, camera = app.emu.frame, app._stream_camera_frame
        app.profile_store.failure = "load"
        self.assertFalse(ProfilesMixin.switch_system(app))
        app.assert_not_disarmed(self, frame, camera)
        self.assertEqual(app.profile_store.calls, [])

    def test_editor_render_failure_does_not_pause_game(self):
        app = Host()
        frame, camera = app.emu.frame, app._stream_camera_frame
        attempts = []

        def refresh():
            attempts.append(app.system_key.get())
            if len(attempts) == 1:
                raise RuntimeError("synthetic broken Tk label")

        app.refresh_settings.side_effect = refresh
        self.assertFalse(ProfilesMixin.switch_system(app))
        app.assert_not_disarmed(self, frame, camera)
        self.assertEqual(attempts, ["snes", "gb"])
        self.assertEqual(app.cfg["tolerance"], 18)

    def test_invalid_old_editor_does_not_disarm_or_persist(self):
        app = Host()
        frame, camera = app.emu.frame, app._stream_camera_frame
        app.read_settings.side_effect = ValueError("invalid prior input")
        self.assertFalse(ProfilesMixin.switch_system(app))
        app.assert_not_disarmed(self, frame, camera)
        self.assertEqual(app.profile_store.calls, [])

    def test_successful_switch_releases_controls_then_stops_native_game(self):
        app = Host()
        camera = app._stream_camera_frame
        sequence = []
        app.stop_controls.side_effect = lambda: sequence.append("camera disarm")
        app.prepare_gamepad_for_game_transition.side_effect = (
            lambda: sequence.append("controller disarm")
        )
        app.deactivate_manual.side_effect = (
            lambda: sequence.append("keyboard release")
        )
        app.emu.stop.side_effect = lambda: sequence.append("native stop")

        self.assertTrue(ProfilesMixin.switch_system(app))
        self.assertEqual(
            sequence,
            ["camera disarm", "controller disarm", "keyboard release", "native stop"],
        )
        self.assertEqual(app.system_key.get(), "snes")
        self.assertEqual(app._active_profile_system, "snes")
        self.assertEqual(app.profile_store.calls[0][0], "gb")
        self.assertEqual(app.cfg["tolerance"], 30)
        self.assertEqual(app.emu.system, "snes")
        self.assertEqual(app.emu.core_path, "/synthetic/new-core.so")
        self.assertIsNone(app.current_rom)
        self.assertIsNone(app.emu.frame)
        self.assertIsNone(app._stream_game_frame)
        self.assertIsNone(app._stream_photo)
        self.assertIs(app._stream_camera_frame, camera)
        self.assertEqual(app._stream_camera_serial, 11)
        self.assertEqual(app.rom_directory, "/synthetic/snes")
        app._stream_resize_cache.clear.assert_called_once_with("GAME")
        app.game_canvas.delete.assert_called_once_with("all")
        app.populate_inline_library.assert_called_once()
        app.save_preferences.assert_called_once()


if __name__ == "__main__":
    from unittest import main
    main()
