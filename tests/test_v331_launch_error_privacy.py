"""3.3.1: failed ROM/external launches never disclose private exception data.

All paths and platform names are synthetic. Native emulator, ROM, Dolphin
bridge, dialogs and processes are replaced with test doubles.
"""
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from anything_plays.launch_error_messages import safe_launch_failure
from anything_plays.ui_external import ExternalBackendMixin
from anything_plays.ui_library import LibraryMixin


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
