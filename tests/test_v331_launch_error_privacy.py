"""3.3.1: failed ROM/external launches never disclose private exception data.

All paths and platform names are synthetic. Native emulator, ROM, Dolphin
bridge, dialogs and processes are replaced with test doubles.
"""
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from anything_plays.launch_error_messages import (safe_launch_failure, safe_worker_failure)
from anything_plays.ui_external import ExternalBackendMixin
from anything_plays.ui_library import LibraryMixin
from anything_plays.ui_gameplay import GameplayMixin


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class RomHost(LibraryMixin):
    def __init__(self):
        self.emu = Mock()
        self.emu.running = False
        self.emu.launching = False
        self.emu.thread = None
        self.emu.find_system_core.return_value = "/synthetic/bundled-core.so"
        self.uses_embedded_emulator = lambda: True
        self.current_rom = None
        self.root = Mock()
        self.system_key = Value("gba")
        self.game_status = Value("")
        self.game_bezel = Mock()
        self.stop_external_emulator = Mock()
        self.prepare_gamepad_for_game_transition = Mock()
        self.deactivate_manual = Mock()
        self.stop_controls = Mock()
        self.show_playing_info = Mock()
        self.game_photo = None
        self._last_game_render = None
        self._stream_game_frame = None
        self._stream_photo = None
        self._stream_resize_cache = Mock()


class ExternalHost(ExternalBackendMixin):
    def __init__(self):
        self.system_key = Value("gamecube")
        self.root = Mock()
        self.preferences_path = Path("/synthetic/preferences.json")
        self.external_emulators = {"gamecube": "/synthetic/dolphin"}
        self.n64_core_override = None
        self.view_mode = Value("Windowed")
        self.external_input = None
        self.external_process = None
        self.emu = Mock()
        self.game_status = Value("")
        self.show_external_placeholder = Mock()


class GameHost(GameplayMixin):
    def __init__(self):
        self._closing = False
        self.root = Mock()
        self.cap = None
        self.frame = None
        self.reference_image = None
        self.emu = Mock()
        self.emu.running = False
        self.emu.launching = False
        self.emu.thread = None
        self.emu.save_warning = None
        self.emu.audio_warning = None
        self.emu.resume_info = None
        self.emu.error = None
        self.game_bezel = Mock()
        self.game_status = Value("")
        self.status = Value("")
        self.action = Value("")
        self.armed = False
        self._pending_object_controls = False
        self._calibration_window = None
        self.system_key = Value("gba")
        self.external_input = None
        self.uses_embedded_emulator = lambda: True
        self.stop_controls = Mock()


class PoisonedNativeError(RuntimeError):
    def __str__(self):
        raise AssertionError("Native driver exception text must never be evaluated")

    def __repr__(self):
        raise AssertionError("Native driver repr must never be evaluated")


class LaunchErrorPrivacyTests(unittest.TestCase):
    def test_native_error_message_never_uses_exception_text_or_repr(self):
        self.assertIn("RuntimeError", safe_launch_failure(PoisonedNativeError()))
        self.assertNotIn("PRIVATE", safe_launch_failure(
            OSError("/Users/person/Documents/private-rom.gba: USB-123")
        ))

    def test_unknown_exception_type_name_is_not_trusted(self):
        class SecretWorkspaceIdentifier(Exception):
            pass
        text = safe_launch_failure(SecretWorkspaceIdentifier("PRIVATE"))
        self.assertIn("UnexpectedError", text)
        self.assertNotIn("SecretWorkspaceIdentifier", text)

    def test_missing_file_and_permissions_have_actionable_safe_advice(self):
        missing = safe_launch_failure(FileNotFoundError(
            "/Users/person/private-library/game.iso"
        ))
        blocked = safe_launch_failure(PermissionError(
            "/home/person/hidden-space"
        ))
        self.assertIn("FileNotFoundError", missing)
        self.assertIn("PermissionError", blocked)
        self.assertIn("accessible", missing)
        self.assertNotIn("/Users/", missing)
        self.assertNotIn("/home/", blocked)

    def test_timeout_mentions_previous_session_without_native_details(self):
        status = safe_launch_failure(TimeoutError("PRIVATE driver bus 281"))
        self.assertIn("previous session", status)
        self.assertNotIn("281", status)

    def test_external_message_is_fixed_guidance_not_exception_detail(self):
        message = safe_launch_failure(
            OSError("PRIVATE /Users/person/external-dolphin"), external=True
        )
        self.assertIn("configured emulator executable", message)
        self.assertNotIn("PRIVATE", message)
        self.assertNotIn("/Users/", message)

    def test_sync_rom_failure_shows_no_private_path_in_status_or_dialog(self):
        app = RomHost()
        app.emu.start.side_effect = OSError(
            "PRIVATE ROM /Users/person/private-game.gba from camera USB-001"
        )
        with patch("anything_plays.ui_library.messagebox.showerror") as error:
            app.start_rom("/synthetic/game.gba")
        detail = app.game_status.get()
        self.assertIn("Game could not start", detail)
        self.assertNotIn("PRIVATE", detail)
        self.assertNotIn("/Users/", detail)
        self.assertNotIn("USB-001", detail)
        self.assertEqual(error.call_args.args[1], detail)
        self.assertIs(error.call_args.kwargs["parent"], app.root)
        app.show_playing_info.assert_called_once()

    def test_sync_rom_failure_handles_exception_with_broken_str(self):
        app = RomHost()
        app.emu.start.side_effect = PoisonedNativeError()
        with patch("anything_plays.ui_library.messagebox.showerror") as error:
            app.start_rom("/synthetic/game.gba")
        self.assertIn("RuntimeError", app.game_status.get())
        error.assert_called_once()

    def test_external_launch_error_cleans_bridge_and_never_leaks_paths(self):
        app = ExternalHost()
        native_bridge = Mock()
        with patch("anything_plays.ui_external.sys.platform", "linux"), \
             patch("anything_plays.ui_external.DolphinPipeController",
                   return_value=native_bridge), \
             patch("anything_plays.ui_external.launch",
                   side_effect=OSError("PRIVATE /home/person/device")), \
             patch("anything_plays.ui_external.messagebox.showerror") as error:
            self.assertIs(app.start_external_rom("/synthetic/game.iso"), False)
        native_bridge.close.assert_called_once()
        self.assertIsNone(app.external_input)
        self.assertIsNone(app.external_process)
        detail = app.game_status.get()
        self.assertIn("External emulator launch failed", detail)
        self.assertNotIn("PRIVATE", detail)
        self.assertNotIn("/home/", detail)
        self.assertEqual(error.call_args.args[1], detail)

    def test_external_bridge_start_failure_still_terminates_emulator(self):
        app = ExternalHost()
        bridge = Mock()
        bridge.start.side_effect = RuntimeError("PRIVATE missing pipe")
        process = Mock()
        process.poll.return_value = None
        with patch("anything_plays.ui_external.sys.platform", "linux"), \
             patch("anything_plays.ui_external.DolphinPipeController",
                   return_value=bridge), \
             patch("anything_plays.ui_external.launch",
                   return_value=process), \
             patch("anything_plays.ui_external.messagebox.showerror") as error:
            self.assertIs(app.start_external_rom("/synthetic/game.iso"), False)
        bridge.close.assert_called_once()
        process.terminate.assert_called_once()
        self.assertIsNone(app.external_process)
        self.assertIsNone(app.external_input)
        self.assertNotIn("PRIVATE", app.game_status.get())
        error.assert_called_once()

    def test_async_worker_failure_category_never_discloses_rom_or_usb_path(self):
        error = "OSError: PRIVATE /Users/person/game.gba usb-serial-001"
        message = safe_worker_failure(error)
        self.assertIn("Emulator stopped", message)
        self.assertIn("OSError", message)
        self.assertNotIn("PRIVATE", message)
        self.assertNotIn("/Users/", message)
        self.assertNotIn("usb-serial", message)

    def test_known_gamecube_gpu_guidance_remains_actionable(self):
        status = safe_worker_failure(
            "GameCube needs a GPU driver with OpenGL 3.3 or newer. "
            "Install or update the graphics driver and restart Anything Plays."
        )
        self.assertIn("OpenGL 3.3", status)
        readback = safe_worker_failure(
            "GameCube GPU readback failed (RuntimeError)."
        )
        self.assertIn("GPU readback failed", readback)
        self.assertNotIn("UnexpectedError", readback)

    def test_forged_gamecube_worker_details_are_never_echoed(self):
        hostile = (
            "GameCube GPU readback failed (RuntimeError) "
            "PRIVATE /Users/person/private.iso"
        )
        message = safe_worker_failure(hostile)
        self.assertIn("UnexpectedError", message)
        self.assertNotIn("PRIVATE", message)
        self.assertNotIn("/Users/", message)

    def test_worker_error_status_in_camera_tick_is_safe(self):
        app = GameHost()
        app.emu.error = "OSError: PRIVATE /home/person/private-rom.gba"
        GameplayMixin.tick(app)
        self.assertIn("Emulator stopped", app.game_status.get())
        self.assertIn("OSError", app.game_status.get())
        self.assertNotIn("PRIVATE", app.game_status.get())
        app.stop_controls.assert_called_once()
        self.assertIsNone(app.emu.error)
        app.root.after.assert_called_once()
        app.game_bezel.set_active.assert_called_once_with(False)

    def test_camera_arm_launch_warning_does_not_echo_worker_failure(self):
        app = GameHost()
        app.emu.last_error = "FileNotFoundError: PRIVATE /Users/name/game.gba"
        with patch.object(GameplayMixin, "_camera_is_open",
                          return_value=True), patch(
                              "anything_plays.ui_gameplay.messagebox.showwarning"
                          ) as warning:
            GameplayMixin.toggle(app)
        self.assertIn("Emulator launch failed", app.game_status.get())
        self.assertNotIn("PRIVATE", app.game_status.get())
        self.assertNotIn("/Users/", warning.call_args.args[1])
        self.assertIn("Restart game", warning.call_args.args[1])
        warning.assert_called_once()
        app.stop_controls.assert_not_called()

    def test_external_start_waits_for_confirmed_native_stop(self):
        app = ExternalHost()
        app.emu.stop.return_value = False
        with patch("anything_plays.ui_external.launch") as launch, \
             patch("anything_plays.ui_external.DolphinPipeController") as bridge, \
             patch("anything_plays.ui_external.messagebox.showerror") as error:
            self.assertIs(app.start_external_rom("/synthetic/game.iso"), False)
        app.emu.stop.assert_called_once()
        launch.assert_not_called()
        bridge.assert_not_called()
        error.assert_not_called()
        self.assertIsNone(app.external_process)
        self.assertIsNone(app.external_input)
        self.assertIn("still shutting down", app.game_status.get())

    def test_external_launch_after_native_stop_completion_still_works(self):
        app = ExternalHost()
        app.emu.stop.return_value = True
        process, bridge = Mock(), Mock()
        with patch("anything_plays.ui_external.sys.platform", "linux"), \
             patch("anything_plays.ui_external.DolphinPipeController",
                   return_value=bridge), \
             patch("anything_plays.ui_external.launch",
                   return_value=process) as launch, \
             patch("anything_plays.ui_external.messagebox.showerror") as error:
            self.assertTrue(app.start_external_rom("/synthetic/game.iso"))
        launch.assert_called_once()
        bridge.start.assert_called_once()
        error.assert_not_called()
        self.assertIs(app.external_process, process)
        self.assertIs(app.external_input, bridge)
        app.show_external_placeholder.assert_called_once()

    def test_external_native_error_with_broken_str_is_safe(self):
        app = ExternalHost()
        with patch("anything_plays.ui_external.launch",
                   side_effect=PoisonedNativeError()), \
             patch("anything_plays.ui_external.DolphinPipeController"), \
             patch("anything_plays.ui_external.messagebox.showerror") as error:
            self.assertIs(app.start_external_rom("/synthetic/game.iso"), False)
        self.assertIn("RuntimeError", app.game_status.get())
        error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
