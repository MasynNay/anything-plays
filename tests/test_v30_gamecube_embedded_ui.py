"""GameCube normal GUI controls launch in the canvas, never through Dolphin.app."""
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from anything_plays.ui_library import LibraryMixin


class GameCubeEmbeddedGuiTests(TestCase):
    def fake_panel(self, core=None):
        panel = LibraryMixin()
        panel._core_install_busy = False
        panel.root = Mock()
        panel.system_key = Mock()
        panel.system_key.get.return_value = "gamecube"
        panel.uses_embedded_emulator = Mock(return_value=True)
        panel.deactivate_manual = Mock()
        panel.stop_controls = Mock()
        panel.stop_external_emulator = Mock()
        panel.start_external_rom = Mock()
        panel.emu = Mock()
        panel.emu.find_system_core.return_value = core
        panel.show_playing_info = Mock()
        panel.game_status = Mock()
        return panel

    def test_gamecube_uses_embedded_worker_not_external_dolphin(self):
        panel = self.fake_panel("/library/dolphin_libretro.so")
        with patch("anything_plays.ui_library.messagebox.showerror") as error:
            panel.start_rom(Path("/home/user/gamecube/Original-Homebrew.dol"))
        panel.emu.start.assert_called_once_with(
            "/home/user/gamecube/Original-Homebrew.dol"
        )
        self.assertEqual(panel.emu.core_path, "/library/dolphin_libretro.so")
        panel.start_external_rom.assert_not_called()
        panel.stop_external_emulator.assert_called_once()
        panel.show_playing_info.assert_called_once()
        error.assert_not_called()

    def test_missing_gamecube_requests_in_app_download_not_external_install(self):
        panel = self.fake_panel(core=None)
        with patch("anything_plays.ui_library.messagebox.showerror") as err:
            panel.start_rom(Path("/home/user/gamecube/Original-Homebrew.dol"))
        panel.start_external_rom.assert_not_called()
        panel.emu.start.assert_not_called()
        err.assert_called_once()
        self.assertIn("Download emulator", err.call_args.args[1])
        self.assertIn("required system files", err.call_args.args[1])

    def test_staging_core_blocks_native_launch(self):
        panel = self.fake_panel("/library/dolphin_libretro.so")
        panel._core_install_busy = True
        with patch("anything_plays.ui_library.messagebox.showwarning") as msg:
            panel.start_rom(Path("/home/user/gamecube/Original-Homebrew.dol"))
        panel.emu.start.assert_not_called()
        panel.start_external_rom.assert_not_called()
        msg.assert_called_once()
