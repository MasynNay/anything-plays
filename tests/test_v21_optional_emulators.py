"""Regression contracts for small starter app + in-app optional emulators."""
import unittest
from queue import Queue
from unittest.mock import Mock, patch
from anything_plays.ui_updates import UpdatesMixin


class OptionalEmulatorDownloads(unittest.TestCase):
    def panel(self, system="snes"):
        instance = UpdatesMixin()
        instance._closing = False
        instance._updates_busy = False
        instance._core_install_busy = False
        instance.system_key = Mock()
        instance.system_key.get.return_value = system
        instance.root = Mock()
        instance.download_emulator_button = Mock()
        instance._selected_emulator_status = Mock()
        instance._emulator_update_status = Mock()
        instance.emu = Mock()
        instance.emu.running = False
        instance.emu.thread = None
        instance.emu.find_system_core.return_value = "/installed/snes9x_libretro.so"
        instance.current_rom = None
        instance.external_process = None
        return instance

    def test_gameboy_family_reuses_default_mgba(self):
        for system in ("gb", "gbc", "gba"):
            panel = self.panel(system)
            self.assertEqual(panel._selected_core_name(), "mgba")

    def test_sega_families_share_one_download(self):
        for system in ("genesis", "mastersystem", "gamegear", "sg1000"):
            self.assertEqual(self.panel(system)._selected_core_name(),
                             "genesis_plus_gx")
        self.assertEqual(self.panel("n64")._selected_core_name(),
                         "parallel_n64")

    def test_missing_core_enables_manual_download_button(self):
        panel = self.panel("snes")
        with patch("anything_plays.core_locator.find_core", return_value=None):
            panel.refresh_selected_emulator_state()
        panel.download_emulator_button.configure.assert_called_with(
            text="Download emulator", state="normal"
        )

    def test_installed_core_does_not_offer_another_download(self):
        panel = self.panel("gba")
        with patch("anything_plays.core_locator.find_core",
                   return_value="/built-in/mgba_libretro.so"):
            panel.refresh_selected_emulator_state()
        panel.download_emulator_button.configure.assert_called_with(
            text="Emulator installed", state="disabled"
        )

    def test_gamecube_only_offers_verified_full_sys_pack_if_published(self):
        panel = self.panel("gamecube")
        panel._available_core_packs = []
        with patch("anything_plays.core_locator.find_core", return_value=None):
            panel.refresh_selected_emulator_state()
        panel.download_emulator_button.configure.assert_called_with(
            text="Download emulator", state="normal"
        )
        # A user may request GameCube but the official catalog currently
        # publishes no approved paired Dolphin + Sys ZIP. It must explain
        # the unavailability instead of downloading a bare DLL/nightly.
        def immediate_thread(*, target, **kwargs):
            return Mock(start=target)
        with patch("anything_plays.core_locator.find_core", return_value=None), \
             patch("anything_plays.ui_updates.messagebox.askyesno",
                   return_value=True), \
             patch("anything_plays.ui_updates.discover_core_packs",
                   return_value=[]), \
             patch("anything_plays.ui_updates.install_core_pack") as installer, \
             patch("anything_plays.ui_updates.Thread",
                   side_effect=immediate_thread), \
             patch("anything_plays.ui_updates.messagebox.showwarning") as warning:
            panel.download_selected_emulator()
            callback = panel.root.after.call_args.args[1]
            callback()
            installer.assert_not_called()
            warning.assert_called_once()
            self.assertIn("No approved", warning.call_args.args[1])

    def test_successful_download_reuses_app_window_and_core_locator(self):
        panel = self.panel("snes")
        panel._updates_busy = True
        panel._core_install_busy = True
        panel._available_core_packs = [{"name": "snes9x"}]
        q = Queue()
        q.put(("/installed/snes9x_libretro.so", None))
        with patch("anything_plays.core_locator.find_core",
                   return_value="/installed/snes9x_libretro.so"), patch(
            "anything_plays.ui_updates.messagebox.showinfo"
        ) as info:
            panel._poll_selected_emulator_install(q, "snes9x")
        self.assertFalse(panel._updates_busy)
        self.assertFalse(panel._core_install_busy)
        self.assertEqual(panel.emu.core_path,
                         "/installed/snes9x_libretro.so")
        self.assertEqual(panel._available_core_packs, [])
        self.assertTrue(info.called)
        panel.root.destroy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
