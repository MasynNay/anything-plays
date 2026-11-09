"""Updater UI must not race native emulators or overwrite signed bundles."""
import unittest
from unittest.mock import Mock, patch

from anything_plays.ui_updates import UpdatesMixin


class CoreUpdateUIContracts(unittest.TestCase):
    def test_update_refuses_running_or_pending_native_session(self):
        panel = UpdatesMixin()
        panel._closing = False
        panel._updates_busy = False
        panel.root = Mock()
        panel.emu = Mock()
        panel.emu.running = True
        panel.emu.thread = None
        panel.current_rom = None
        panel.external_process = None
        self.assertFalse(panel._can_update_emulators())
        with patch("anything_plays.ui_updates.messagebox.showwarning") as warning:
            panel.install_emulator_updates()
            self.assertTrue(warning.called)
        panel.emu.running = False
        panel.emu.thread = Mock()
        panel.emu.thread.is_alive.return_value = True
        self.assertFalse(panel._can_update_emulators())
        panel.emu.thread.is_alive.return_value = False
        panel.current_rom = "/any/fake/game.gba"
        self.assertFalse(panel._can_update_emulators())
        panel.current_rom = None
        self.assertTrue(panel._can_update_emulators())

    def test_install_completion_switches_next_core_and_keeps_tk_open(self):
        from queue import Queue
        panel = UpdatesMixin()
        panel._closing = False
        panel._updates_busy = True
        panel._core_install_busy = True
        panel._available_core_packs = [
            {"name": "mgba"}, {"name": "snes9x"}
        ]
        panel.emu = Mock()
        panel.emu.find_system_core.return_value = "/updates/mgba_libretro.so"
        panel._emulator_update_status = Mock()
        panel.root = Mock()
        result = Queue()
        result.put(([("mgba", "/updates/mgba_libretro.so")],
                    [("snes9x", "unapproved asset")]))
        with patch("anything_plays.ui_updates.messagebox.showwarning") as warning:
            panel._poll_core_install(result)
        self.assertFalse(panel._core_install_busy)
        self.assertFalse(panel._updates_busy)
        self.assertEqual(
            panel.emu.core_path, "/updates/mgba_libretro.so"
        )
        self.assertEqual(panel._available_core_packs, [{"name": "snes9x"}])
        self.assertTrue(warning.called)
        panel.root.destroy.assert_not_called()

    def test_no_approved_release_does_not_download_random_core(self):
        panel = UpdatesMixin()
        panel._closing = False
        panel._updates_busy = False
        panel.root = Mock()
        panel.emu = Mock()
        panel.emu.running = False
        panel.emu.thread = None
        panel.current_rom = None
        panel.external_process = None
        panel._available_core_packs = []
        with patch("anything_plays.ui_updates.install_core_pack") as installer, \
             patch("anything_plays.ui_updates.messagebox.showinfo") as info:
            panel.install_emulator_updates()
            installer.assert_not_called()
            info.assert_called_once()


if __name__ == "__main__":
    unittest.main()
