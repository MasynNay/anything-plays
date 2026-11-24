"""3.3.1: ROM and console transitions must survive failed native pad release.

Only mock core facades and Tk canvas objects are used. No real controller,
camera, personal settings, native core, or ROM file is accessed.
"""
from threading import Lock
import unittest
from unittest.mock import Mock

from anything_plays.ui_gamepad import GamepadMixin
from anything_plays.ui_library import LibraryMixin


class Flag:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class TransitionHost(GamepadMixin, LibraryMixin):
    def __init__(self, enabled=True):
        self.gamepad_enabled = Flag(enabled)
        self._gamepad_game_resume_release_pending = False
        self.emu = Mock()
        self.emu.lock = Lock()
        self.emu.frame = object()
        self.emu.frame_serial = 21
        self.emu.release_gamepad.side_effect = OSError(
            "PRIVATE core unavailable /home/user/device"
        )
        self.game_canvas = Mock()
        self._game_only_canvas = Mock()
        self._stream_canvas = Mock()
        self._stream_resize_cache = Mock()
        self._stream_camera_frame = object()
        self._stream_camera_serial = 12
        self._stream_game_frame = object()
        self._stream_photo = object()
        self.game_photo = object()
        self._last_game_render = object()
        self.current_rom = "/synthetic/old.gba"
        self.game_status = Mock()
        self.show_library = Mock()
        self.stop_external_emulator = Mock()
        self.deactivate_manual = Mock()
        self.stop_controls = Mock()


class GamepadTransitionReleaseTests(unittest.TestCase):
    def test_active_pad_transition_uses_input_buffer_if_facade_fails(self):
        app = TransitionHost()
        app.prepare_gamepad_for_game_transition()
        self.assertTrue(app._gamepad_game_resume_release_pending)
        app.emu.release_gamepad.assert_called_once()
        app.emu.inputs.release_gamepad.assert_called_once()

    def test_disabled_pad_also_clears_stale_emulator_input(self):
        app = TransitionHost(enabled=False)
        app.prepare_gamepad_for_game_transition()
        self.assertFalse(app._gamepad_game_resume_release_pending)
        app.emu.inputs.release_gamepad.assert_called_once()

    def test_transition_cannot_be_blocked_by_both_native_release_faults(self):
        app = TransitionHost()
        app.emu.inputs.release_gamepad.side_effect = RuntimeError(
            "PRIVATE native teardown failure"
        )
        app.prepare_gamepad_for_game_transition()
        app.emu.inputs.release_gamepad.assert_called_once()
        self.assertTrue(app._gamepad_game_resume_release_pending)

    def test_normal_facade_release_does_not_duplicate_native_release(self):
        app = TransitionHost()
        app.emu.release_gamepad.side_effect = None
        app.prepare_gamepad_for_game_transition()
        app.emu.release_gamepad.assert_called_once()
        app.emu.inputs.release_gamepad.assert_not_called()
        self.assertTrue(app._gamepad_game_resume_release_pending)

    def test_rom_unload_stops_old_game_even_when_release_hook_throws(self):
        app = TransitionHost()
        camera = app._stream_camera_frame
        app.unload_rom()
        app.emu.release_gamepad.assert_called_once()
        app.emu.inputs.release_gamepad.assert_called_once()
        app.emu.stop.assert_called_once()
        app.stop_controls.assert_called_once()
        app.deactivate_manual.assert_called_once()
        app.stop_external_emulator.assert_called_once()
        app.show_library.assert_called_once()
        self.assertIsNone(app.current_rom)
        self.assertIsNone(app.emu.frame)
        self.assertEqual(app.emu.frame_serial, 22)
        self.assertIsNone(app._stream_game_frame)
        self.assertIsNone(app._stream_photo)
        self.assertIs(app._stream_camera_frame, camera)
        self.assertEqual(app._stream_camera_serial, 12)
        app._stream_resize_cache.clear.assert_called_once_with("GAME")
        app.game_canvas.delete.assert_called_once_with("all")

    def test_gamepad_fallback_releases_even_without_input_buffer(self):
        app = TransitionHost()
        app.emu.inputs = None
        app.prepare_gamepad_for_game_transition()
        self.assertTrue(app._gamepad_game_resume_release_pending)
        app.emu.release_gamepad.assert_called_once()


if __name__ == "__main__":
    unittest.main()
