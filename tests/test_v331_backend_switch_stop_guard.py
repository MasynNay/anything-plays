"""3.3.1: renderer selection must not commit after timed-out native ROM Stop.

Fake preferences, game pixels, settings and Tk button variables only. No
emulator, ROM, GPU, Dolphin/RetroArch process or real files are accessed.
"""
import unittest
from unittest.mock import Mock

from anything_plays.ui_external import ExternalBackendMixin


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class BackendHost(ExternalBackendMixin):
    def __init__(self, system="gamecube", *, selected=False, fallback=True,
                 unload_success=False):
        self.system_key = Value(system)
        self.external_fallback_enabled = fallback
        self.n64_embedded = Value(True)
        self.gamecube_embedded = Value(True)
        target = self.n64_embedded if system == "n64" else self.gamecube_embedded
        target.set(selected)  # Tk Checkbutton has already toggled the value.
        self.unload_rom = Mock(return_value=unload_success)
        self.stop_controls = Mock()
        self.game_canvas = Mock()
        self.view_mode = Value("Game only")
        self.set_view_mode = Mock()
        self.save_preferences = Mock()
        self.update_external_setup = Mock()
        self.show_external_placeholder = Mock()
        self.game_status = Value("Playing old core")
        self.current_rom = "/synthetic/old-game.iso"
        self.emu = Mock()
        self.emu.running = True
        self.emu.frame = object()
        self.uses_embedded_emulator = lambda: (
            self.n64_embedded.get() if self.system_key.get() == "n64"
            else self.gamecube_embedded.get()
        )

    def assert_previous_game_untouched(self, testcase, old_frame):
        testcase.assertIs(self.emu.frame, old_frame)
        testcase.assertEqual(self.current_rom, "/synthetic/old-game.iso")
        self.save_preferences.assert_not_called()
        self.update_external_setup.assert_not_called()
        self.show_external_placeholder.assert_not_called()
        self.set_view_mode.assert_not_called()
        self.game_canvas.delete.assert_not_called()
        self.stop_controls.assert_called_once()
        self.unload_rom.assert_called_once()


class BackendSwitchStopTests(unittest.TestCase):
    def test_gamecube_timeout_does_not_switch_renderer_or_clear_pixels(self):
        app = BackendHost()
        frame = app.emu.frame
        self.assertIs(app._switch_3d_backend("gamecube"), False)
        self.assertTrue(app.gamecube_embedded.get())
        self.assertIn("finish shutting down", app.game_status.get())
        app.assert_previous_game_untouched(self, frame)

    def test_n64_timeout_does_not_persist_external_fallback(self):
        app = BackendHost(system="n64")
        frame = app.emu.frame
        self.assertIs(app._switch_3d_backend("n64"), False)
        self.assertTrue(app.n64_embedded.get())
        self.assertIn("Backend switch canceled", app.game_status.get())
        app.assert_previous_game_untouched(self, frame)

    def test_timeout_when_toggling_back_to_embedded_restores_external_mode(self):
        app = BackendHost(selected=True, unload_success=False)
        frame = app.emu.frame
        self.assertIs(app._switch_3d_backend("gamecube"), False)
        self.assertFalse(app.gamecube_embedded.get())
        app.assert_previous_game_untouched(self, frame)

    def test_unload_error_cannot_leak_private_path_or_commit_renderer(self):
        app = BackendHost()
        app.unload_rom.side_effect = OSError(
            "PRIVATE /Users/person/library/game.iso"
        )
        frame = app.emu.frame
        self.assertIs(app._switch_3d_backend("gamecube"), False)
        self.assertTrue(app.gamecube_embedded.get())
        self.assertNotIn("PRIVATE", app.game_status.get())
        self.assertNotIn("/Users/", app.game_status.get())
        app.assert_previous_game_untouched(self, frame)

    def test_successful_external_gamecube_switch_updates_mode_and_config(self):
        app = BackendHost(unload_success=True)
        self.assertIs(app._switch_3d_backend("gamecube"), True)
        self.assertFalse(app.gamecube_embedded.get())
        app.unload_rom.assert_called_once()
        app.save_preferences.assert_called_once()
        app.set_view_mode.assert_called_once_with("Windowed")
        app.game_canvas.delete.assert_called_once_with("all")
        app.show_external_placeholder.assert_called_once()
        self.assertIn("external developer fallback", app.game_status.get())

    def test_successful_embedded_n64_switch_preserves_game_only_mode(self):
        app = BackendHost(system="n64", selected=True, unload_success=True)
        self.assertIs(app._switch_3d_backend("n64"), True)
        app.set_view_mode.assert_not_called()
        app.save_preferences.assert_called_once()
        self.assertIn("N64 software graphics", app.game_status.get())

    def test_external_fallback_disabled_forces_bundled_backend_on_success(self):
        app = BackendHost(fallback=False, selected=False, unload_success=True)
        app.n64_embedded.set(False)
        self.assertIs(app._switch_3d_backend("gamecube"), True)
        self.assertTrue(app.gamecube_embedded.get())
        self.assertTrue(app.n64_embedded.get())
        app.save_preferences.assert_called_once()
        app.set_view_mode.assert_not_called()

    def test_external_fallback_disabled_does_not_clear_game_on_stop_failure(self):
        app = BackendHost(fallback=False, selected=False, unload_success=False)
        frame = app.emu.frame
        self.assertIs(app._switch_3d_backend("gamecube"), False)
        self.assertTrue(app.gamecube_embedded.get())
        app.assert_previous_game_untouched(self, frame)

    def test_different_console_ignores_unrelated_backend_toggle(self):
        app = BackendHost(system="gamecube")
        self.assertIs(app._switch_3d_backend("n64"), False)
        app.stop_controls.assert_not_called()
        app.unload_rom.assert_not_called()
        app.save_preferences.assert_not_called()
        self.assertEqual(app.game_status.get(), "Playing old core")


if __name__ == "__main__":
    unittest.main()
