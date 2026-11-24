"""3.3.1: Stop and ROM unload must clear camera input after native faults.

All hosts, native queues, Tk buttons, webcams and external gamepads are mocks.
No physical capture, game ROM, network, settings, core or real window is used.
"""
from threading import Lock
import unittest
from unittest.mock import Mock

from anything_plays.ui_gameplay import GameplayMixin
from anything_plays.ui_library import LibraryMixin


class Flag:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class Host(GameplayMixin, LibraryMixin):
    def __init__(self):
        self._pending_object_controls = True
        self.armed = True
        self.system_key = Flag("gba")
        self.uses_embedded_emulator = lambda: True
        self.emu = Mock()
        self.emu.armed = True
        self.emu.lock = Lock()
        self.emu.frame = object()
        self.emu.frame_serial = 17
        self.external_input = Mock()
        self._last_camera_pulses = {(0, "A"): 12.0, (1, "B"): 12.0}
        self.arm_button = Mock()
        self.action = Mock()

        self.current_rom = "/synthetic/old-game.gba"
        self.stop_external_emulator = Mock()
        self.deactivate_manual = Mock()
        self.game_canvas = Mock()
        self._game_only_canvas = Mock()
        self._stream_canvas = Mock()
        self._stream_resize_cache = Mock()
        self._stream_game_frame = object()
        self._stream_photo = object()
        self._stream_camera_frame = object()
        self.game_photo = object()
        self._last_game_render = object()
        self.game_status = Mock()
        self.show_library = Mock()

    def assert_stopped(self, testcase):
        testcase.assertFalse(self.armed)
        testcase.assertFalse(self._pending_object_controls)
        testcase.assertEqual(self._last_camera_pulses, {})
        self.external_input.release_camera.assert_called_once()
        self.action.set.assert_called_with(
            "PREVIEW ONLY — no keyboard events are sent"
        )
        self.arm_button.config.assert_called_once_with(
            text="Enable object controls"
        )


class CameraStopFaultIsolationTests(unittest.TestCase):
    def test_regular_stop_clears_camera_state_and_external_bridge(self):
        app = Host()
        app.stop_controls()
        app.emu.disarm.assert_called_once()
        app.emu.inputs.disarm.assert_not_called()
        app.assert_stopped(self)

    def test_failed_facade_uses_native_input_buffer_fallback(self):
        app = Host()
        app.emu.disarm.side_effect = OSError(
            "PRIVATE USB serial /home/person/video"
        )
        app.stop_controls()
        app.emu.disarm.assert_called_once()
        app.emu.inputs.disarm.assert_called_once()
        self.assertFalse(app.emu.armed)
        app.assert_stopped(self)

    def test_both_native_disarm_hooks_throw_but_stop_continues(self):
        app = Host()
        app.emu.disarm.side_effect = RuntimeError(
            "PRIVATE native emulator hook failed"
        )
        app.emu.inputs.disarm.side_effect = RuntimeError(
            "PRIVATE Libretro InputBuffer failed"
        )
        app.stop_controls()
        app.emu.inputs.disarm.assert_called_once()
        app.assert_stopped(self)

    def test_external_bridge_unplug_does_not_block_ui_stop(self):
        app = Host()
        app.external_input.release_camera.side_effect = BrokenPipeError(
            "PRIVATE disconnected Dolphin pipe"
        )
        app.stop_controls()
        app.emu.disarm.assert_called_once()
        app.assert_stopped(self)

    def test_destroyed_arm_button_does_not_block_action_status(self):
        app = Host()
        app.arm_button.config.side_effect = RuntimeError(
            "PRIVATE deleted Tk widget"
        )
        app.stop_controls()
        app.emu.disarm.assert_called_once()
        app.action.set.assert_called_once()
        self.assertFalse(app.armed)

    def test_destroyed_status_variable_does_not_rearm_camera(self):
        app = Host()
        app.action.set.side_effect = RuntimeError(
            "PRIVATE Tk variable destroyed"
        )
        app.stop_controls()
        app.emu.disarm.assert_called_once()
        app.external_input.release_camera.assert_called_once()
        self.assertFalse(app.armed)
        self.assertFalse(app._pending_object_controls)

    def test_broken_pulse_cache_does_not_block_external_camera_release(self):
        app = Host()
        pulse_cache = Mock()
        pulse_cache.clear.side_effect = RuntimeError("cache extension failed")
        app._last_camera_pulses = pulse_cache
        app.stop_controls()
        pulse_cache.clear.assert_called_once()
        self.assertEqual(app._last_camera_pulses, {})
        app.external_input.release_camera.assert_called_once()

    def test_no_external_bridge_or_optional_widgets_is_also_safe(self):
        app = Host()
        app.external_input = None
        del app.arm_button
        del app.action
        app.stop_controls()
        app.emu.disarm.assert_called_once()
        self.assertFalse(app.armed)
        self.assertEqual(app._last_camera_pulses, {})

    def test_missing_input_buffer_does_not_block_stop_cleanup(self):
        app = Host()
        app.emu.disarm.side_effect = RuntimeError("detached extension")
        app.emu.inputs = None
        app.stop_controls()
        self.assertFalse(app.emu.armed)
        app.assert_stopped(self)

    def test_rom_unload_stops_native_even_if_disarm_and_bridge_fail(self):
        app = Host()
        camera = app._stream_camera_frame
        app.emu.disarm.side_effect = RuntimeError("native hook offline")
        app.external_input.release_camera.side_effect = OSError(
            "PRIVATE missing pipe"
        )
        app.unload_rom()
        self.assertFalse(app.armed)
        self.assertFalse(app.emu.armed)
        app.emu.inputs.disarm.assert_called_once()
        app.emu.stop.assert_called_once()
        app.stop_external_emulator.assert_called_once()
        app.deactivate_manual.assert_called_once()
        self.assertIsNone(app.current_rom)
        self.assertIsNone(app.emu.frame)
        self.assertEqual(app.emu.frame_serial, 18)
        self.assertIsNone(app._stream_game_frame)
        self.assertIsNone(app._stream_photo)
        self.assertIs(app._stream_camera_frame, camera)
        app._stream_resize_cache.clear.assert_called_once_with("GAME")
        app.show_library.assert_called_once()


if __name__ == "__main__":
    unittest.main()
