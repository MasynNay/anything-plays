"""3.3.1: core-pack installs/rollbacks must not race a newly starting ROM.

The fake GUI never connects to GitHub, opens an emulator, downloads cores,
loads user ROMs or writes user configuration. All transactions are mocked.
"""
from unittest import TestCase
from unittest.mock import Mock, patch

from anything_plays.ui_updates import UpdatesMixin


class ImmediateThread:
    def __init__(self, target, **_kwargs):
        self.target = target

    def start(self):
        self.target()


class UpdateHost(UpdatesMixin):
    def __init__(self):
        self._closing = False
        self._updates_busy = False
        self._core_install_busy = False
        self._available_core_packs = [{"name": "mgba", "sha256": "a" * 64}]
        self.current_rom = None
        self.external_process = None
        self.root = Mock()
        self.root.after.side_effect = lambda _delay, callback: callback()
        self.emu = Mock()
        self.emu.running = False
        self.emu.launching = False
        self.emu.thread = None
        self.emu.find_system_core.return_value = "/synthetic/new-core.so"
        self._emulator_update_status = Mock()
        self.system_key = Mock()
        self.system_key.get.return_value = "gba"
        self.refresh_selected_emulator_state = Mock()


class UpdateStartupGuardTests(TestCase):
    def setUp(self):
        self.host = UpdateHost()

    def test_launching_worker_is_not_mutable_even_without_thread_or_rom(self):
        self.host.emu.launching = True
        self.assertFalse(self.host._can_update_emulators())
        with patch("anything_plays.ui_updates.messagebox.showwarning") as warning, \
             patch("anything_plays.ui_updates.messagebox.askyesno") as consent:
            self.host.install_emulator_updates()
        warning.assert_called_once()
        consent.assert_not_called()

    def test_launching_false_allows_idle_update(self):
        self.assertTrue(self.host._can_update_emulators())
        self.host.emu.launching = True
        self.assertFalse(self.host._can_update_emulators())
        self.host.emu.launching = False
        self.assertTrue(self.host._can_update_emulators())

    def test_startup_during_install_confirmation_cancels_install(self):
        def answer(*_args, **_kwargs):
            self.host.emu.launching = True
            return True

        with patch("anything_plays.ui_updates.messagebox.askyesno",
                   side_effect=answer), patch(
                       "anything_plays.ui_updates.messagebox.showwarning"
                   ) as warning, patch(
                       "anything_plays.ui_updates.Thread"
                   ) as thread, patch(
                       "anything_plays.ui_updates.install_core_pack"
                   ) as installer:
            self.host.install_emulator_updates()
        warning.assert_called_once()
        thread.assert_not_called()
        installer.assert_not_called()
        self.assertFalse(self.host._updates_busy)
        self.assertFalse(self.host._core_install_busy)
        self.host.root.after.assert_not_called()

    def test_selected_rom_during_install_confirmation_cancels(self):
        def answer(*_args, **_kwargs):
            self.host.current_rom = "/synthetic/game.gba"
            return True

        with patch("anything_plays.ui_updates.messagebox.askyesno",
                   side_effect=answer), patch(
                       "anything_plays.ui_updates.messagebox.showwarning"
                   ) as warning, patch(
                       "anything_plays.ui_updates.Thread"
                   ) as thread:
            self.host.install_emulator_updates()
        warning.assert_called_once()
        thread.assert_not_called()
        self.assertFalse(self.host._updates_busy)

    def test_closing_during_install_confirmation_cancels_without_worker(self):
        def answer(*_args, **_kwargs):
            self.host._closing = True
            return True

        with patch("anything_plays.ui_updates.messagebox.askyesno",
                   side_effect=answer), patch(
                       "anything_plays.ui_updates.Thread"
                   ) as thread:
            self.host.install_emulator_updates()
        thread.assert_not_called()
        self.assertFalse(self.host._core_install_busy)

    def test_other_update_during_confirmation_cancels_duplicate_worker(self):
        def answer(*_args, **_kwargs):
            self.host._updates_busy = True
            return True

        with patch("anything_plays.ui_updates.messagebox.askyesno",
                   side_effect=answer), patch(
                       "anything_plays.ui_updates.Thread"
                   ) as thread:
            self.host.install_emulator_updates()
        thread.assert_not_called()
        self.assertTrue(self.host._updates_busy)

    def test_normal_idle_install_still_succeeds(self):
        with patch("anything_plays.ui_updates.messagebox.askyesno",
                   return_value=True), patch(
                       "anything_plays.ui_updates.Thread", ImmediateThread
                   ), patch(
                       "anything_plays.ui_updates.install_core_pack",
                       return_value="/synthetic/updated-mgba.so"
                   ) as installer, patch(
                       "anything_plays.ui_updates.messagebox.showinfo"
                   ) as info:
            self.host.install_emulator_updates()
        installer.assert_called_once()
        info.assert_called_once()
        self.assertEqual(self.host.emu.core_path, "/synthetic/new-core.so")
        self.assertEqual(self.host._available_core_packs, [])
        self.assertFalse(self.host._updates_busy)
        self.assertFalse(self.host._core_install_busy)

    def test_launching_during_rollback_confirmation_cancels(self):
        def answer(*_args, **_kwargs):
            self.host.emu.launching = True
            return True

        with patch("anything_plays.ui_updates.managed_core_path",
                   return_value="/synthetic/managed-mgba.so"), patch(
                       "anything_plays.ui_updates.messagebox.askyesno",
                       side_effect=answer
                   ), patch(
                       "anything_plays.ui_updates.messagebox.showwarning"
                   ) as warning, patch(
                       "anything_plays.ui_updates.rollback_core"
                   ) as rollback:
            self.host.restore_bundled_emulator()
        warning.assert_called_once()
        rollback.assert_not_called()
        self.host.refresh_selected_emulator_state.assert_not_called()

    def test_closing_during_rollback_confirmation_cancels(self):
        def answer(*_args, **_kwargs):
            self.host._closing = True
            return True

        with patch("anything_plays.ui_updates.managed_core_path",
                   return_value="/synthetic/managed-mgba.so"), patch(
                       "anything_plays.ui_updates.messagebox.askyesno",
                       side_effect=answer
                   ), patch("anything_plays.ui_updates.rollback_core") as rollback:
            self.host.restore_bundled_emulator()
        rollback.assert_not_called()

    def test_running_game_during_rollback_confirmation_cancels(self):
        def answer(*_args, **_kwargs):
            self.host.emu.running = True
            return True

        with patch("anything_plays.ui_updates.managed_core_path",
                   return_value="/synthetic/managed-mgba.so"), patch(
                       "anything_plays.ui_updates.messagebox.askyesno",
                       side_effect=answer
                   ), patch(
                       "anything_plays.ui_updates.messagebox.showwarning"
                   ) as warning, patch(
                       "anything_plays.ui_updates.rollback_core"
                   ) as rollback:
            self.host.restore_bundled_emulator()
        warning.assert_called_once()
        rollback.assert_not_called()

    def test_normal_idle_rollback_still_succeeds(self):
        with patch("anything_plays.ui_updates.managed_core_path",
                   return_value="/synthetic/managed-mgba.so"), patch(
                       "anything_plays.ui_updates.messagebox.askyesno",
                       return_value=True
                   ), patch(
                       "anything_plays.ui_updates.rollback_core"
                   ) as rollback:
            self.host.restore_bundled_emulator()
        rollback.assert_called_once_with("mgba")
        self.host.refresh_selected_emulator_state.assert_called_once()
        self.assertIn(
            "restored",
            self.host._emulator_update_status.set.call_args.args[0],
        )


if __name__ == "__main__":
    from unittest import main
    main()
