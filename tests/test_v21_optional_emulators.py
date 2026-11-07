"""3.0 offline-emulator GUI contracts (retained old test filename for CI).

All console cores ship in the installer: no missing-core download button,
no separate application, and no mandatory network connection. Approved
versioned core *updates* are tested independently in test_v21_core_update_ui.
"""
import unittest
from unittest.mock import Mock, patch
from anything_plays.ui_updates import UpdatesMixin


class OfflineEmulatorStatusContracts(unittest.TestCase):
    def panel(self, system="snes"):
        instance=UpdatesMixin()
        instance._closing=False
        instance._updates_busy=False
        instance._core_install_busy=False
        instance.system_key=Mock()
        instance.system_key.get.return_value=system
        instance.root=Mock()
        instance._selected_emulator_status=Mock()
        instance._emulator_update_status=Mock()
        instance.emu=Mock()
        instance.emu.running=False
        instance.emu.thread=None
        instance.current_rom=None
        instance.external_process=None
        return instance

    def test_all_gameboy_family_members_reuse_bundled_mgba(self):
        for name in ("gb","gbc","gba"):
            self.assertEqual(self.panel(name)._selected_core_name(),"mgba")

    def test_sega_family_reuses_bundled_genesis_plus_gx(self):
        for name in ("genesis","mastersystem","gamegear","sg1000"):
            self.assertEqual(self.panel(name)._selected_core_name(),
                             "genesis_plus_gx")
        self.assertEqual(self.panel("n64")._selected_core_name(),"parallel_n64")
        self.assertEqual(self.panel("gamecube")._selected_core_name(),"dolphin")

    def test_missing_core_reports_installation_damage_not_optional_download(self):
        panel=self.panel("snes")
        with patch("anything_plays.core_locator.find_core",return_value=None):
            panel.refresh_selected_emulator_state()
        message=panel._selected_emulator_status.set.call_args.args[0]
        self.assertIn("missing",message)
        self.assertIn("reinstall",message)
        self.assertNotIn("download",message.casefold())

    def test_installed_core_is_already_ready_to_play_offline(self):
        panel=self.panel("gba")
        with patch("anything_plays.core_locator.find_core",
                   return_value="/bundled/mgba_libretro.so"):
            panel.refresh_selected_emulator_state()
        message=panel._selected_emulator_status.set.call_args.args[0]
        self.assertIn("Ready inside Anything Plays",message)
        self.assertIn("mgba",message)

    def test_missing_gamecube_includes_required_sys_assets_in_repair(self):
        panel=self.panel("gamecube")
        with patch("anything_plays.core_locator.find_core",return_value=None):
            panel.refresh_selected_emulator_state()
        message=panel._selected_emulator_status.set.call_args.args[0]
        self.assertIn("reinstall",message)
        self.assertNotIn("optional",message.casefold())

    def test_active_verified_update_is_shown_separately(self):
        panel=self.panel("snes")
        panel._core_install_busy=True
        with patch("anything_plays.core_locator.find_core",return_value=None):
            panel.refresh_selected_emulator_state()
        self.assertIn("approved emulator update",
                      panel._selected_emulator_status.set.call_args.args[0])

if __name__=="__main__":
    unittest.main()
