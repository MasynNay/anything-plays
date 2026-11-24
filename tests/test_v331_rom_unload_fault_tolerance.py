"""3.3.1: optional controller/IPC cleanup cannot prevent native ROM Stop.

All ROMs, native workers, cameras, input bridges and Tk windows are mocks.
Never opens files, spawns an emulator, or changes user configuration.
"""
from threading import Lock
from unittest import TestCase
from unittest.mock import Mock

from anything_plays.ui_external import ExternalBackendMixin
from anything_plays.ui_library import LibraryMixin


class FakeHost(LibraryMixin, ExternalBackendMixin):
    def __init__(self):
        self.current_rom = "/synthetic/old.sfc"
        self.emu = Mock()
        self.emu.lock = Lock()
        self.emu.frame = object()
        self.emu.frame_serial = 41
        self.prepare_gamepad_for_game_transition = Mock()
        self.deactivate_manual = Mock()
        self.stop_controls = Mock()
        self.game_status = Mock()
        self.show_library = Mock()

        self.external_input = Mock()
        self.external_process = Mock()
        self.external_process.poll.return_value = None

        self.game_canvas = Mock()
        self._game_only_canvas = Mock()
        self._stream_canvas = Mock()
        self._stream_resize_cache = Mock()
        self.game_photo = object()
        self._last_game_render = object()
        self._stream_game_frame = object()
        self._stream_photo = object()
        self._stream_camera_frame = object()
        self._stream_camera_serial = 8

    def assert_retired(self, testcase):
        self.emu.stop.assert_called_once()
        testcase.assertIsNone(self.current_rom)
        testcase.assertIsNone(self.emu.frame)
        testcase.assertEqual(self.emu.frame_serial, 42)
        testcase.assertIsNone(self.game_photo)
        testcase.assertIsNone(self._stream_game_frame)
        testcase.assertIsNone(self._stream_photo)
        testcase.assertIsNotNone(self._stream_camera_frame)
        testcase.assertEqual(self._stream_camera_serial, 8)
        self._stream_resize_cache.clear.assert_called_once_with("GAME")
        self.game_status.set.assert_called_with("No ROM loaded")
        self.show_library.assert_called_once()


class ExternalProcessShutdownTests(TestCase):
    def test_failed_bridge_close_still_terminates_live_emulator(self):
        app = FakeHost()
        bridge, process = app.external_input, app.external_process
        bridge.close.side_effect = OSError("PRIVATE Dolphin input pipe")
        app.stop_external_emulator()
        bridge.close.assert_called_once()
        process.poll.assert_called_once()
        process.terminate.assert_called_once()
        self.assertIsNone(app.external_input)
        self.assertIsNone(app.external_process)

    def test_finished_process_is_not_terminated_again(self):
        app = FakeHost()
        app.external_process.poll.return_value = 0
        process = app.external_process
        app.stop_external_emulator()
        process.terminate.assert_not_called()

    def test_external_poll_fault_detaches_both_resources_without_raising(self):
        app = FakeHost()
        process = app.external_process
        process.poll.side_effect = RuntimeError("PRIVATE stale handle")
        app.stop_external_emulator()
        process.terminate.assert_not_called()
        self.assertIsNone(app.external_input)
        self.assertIsNone(app.external_process)

    def test_terminate_race_does_not_raise_or_retain_handle(self):
        app = FakeHost()
        process = app.external_process
        process.terminate.side_effect = ProcessLookupError("already exited")
        app.stop_external_emulator()
        process.terminate.assert_called_once()
        self.assertIsNone(app.external_input)
        self.assertIsNone(app.external_process)

    def test_repeated_external_stop_cannot_close_handle_twice(self):
        app = FakeHost()
        bridge, process = app.external_input, app.external_process
        app.stop_external_emulator()
        app.stop_external_emulator()
        bridge.close.assert_called_once()
        process.terminate.assert_called_once()


class NativeUnloadFailureIsolationTests(TestCase):
    def test_normal_handoff_releases_inputs_before_native_stop(self):
        app = FakeHost()
        steps = []
        app.prepare_gamepad_for_game_transition.side_effect = lambda: steps.append("pad")
        app.external_input.close.side_effect = lambda: steps.append("external bridge")
        app.external_process.terminate.side_effect = lambda: steps.append("external process")
        app.deactivate_manual.side_effect = lambda: steps.append("manual")
        app.stop_controls.side_effect = lambda: steps.append("camera")
        app.emu.stop.side_effect = lambda: steps.append("native stop")
        app.unload_rom()
        self.assertEqual(steps, [
            "pad", "external bridge", "external process", "manual", "camera",
            "native stop",
        ])
        app.assert_retired(self)

    def test_every_optional_release_can_fail_without_skipping_native_stop(self):
        app = FakeHost()
        app.prepare_gamepad_for_game_transition.side_effect = RuntimeError("pad")
        app.external_input.close.side_effect = RuntimeError("bridge")
        app.external_process.terminate.side_effect = OSError("external")
        app.deactivate_manual.side_effect = RuntimeError("manual")
        app.stop_controls.side_effect = RuntimeError("camera")
        app.unload_rom()
        app.emu.inputs.release_manual.assert_called_once()
        self.assertIsNone(app.external_process)
        self.assertIsNone(app.external_input)
        app.assert_retired(self)
        app.stop_controls.assert_called_once()
        app.prepare_gamepad_for_game_transition.assert_called_once()

    def test_gamepad_failure_alone_cannot_block_other_input_release(self):
        app = FakeHost()
        app.prepare_gamepad_for_game_transition.side_effect = RuntimeError("SDL")
        app.unload_rom()
        app.deactivate_manual.assert_called_once()
        app.stop_controls.assert_called_once()
        app.assert_retired(self)

    def test_manual_fallback_failure_cannot_block_native_stop(self):
        app = FakeHost()
        app.deactivate_manual.side_effect = RuntimeError("native manual hook")
        app.emu.inputs.release_manual.side_effect = OSError("manual buffer unavailable")
        app.unload_rom()
        app.emu.inputs.release_manual.assert_called_once()
        app.assert_retired(self)

    def test_no_manual_input_buffer_still_unloads_on_hook_failure(self):
        app = FakeHost()
        app.deactivate_manual.side_effect = RuntimeError("stale native wrapper")
        app.emu.inputs = None
        app.unload_rom()
        app.assert_retired(self)

    def test_mandatory_native_stop_failure_is_not_claimed_as_clean_unload(self):
        app = FakeHost()
        app.emu.stop.side_effect = RuntimeError("native session still active")
        frame = app.emu.frame
        with self.assertRaisesRegex(RuntimeError, "native session"):
            app.unload_rom()
        self.assertEqual(app.current_rom, "/synthetic/old.sfc")
        self.assertIs(app.emu.frame, frame)
        app.game_status.set.assert_not_called()
        app.show_library.assert_not_called()
        app.stop_controls.assert_called_once()
        self.assertIsNone(app.external_input)


if __name__ == "__main__":
    from unittest import main
    main()
