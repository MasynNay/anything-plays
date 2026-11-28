"""3.3.1: optional controller remapping UI cannot disable physical SDL input.

Synthetic Tk values, mapped buttons and emulator facades only; no ROMs,
USB/Bluetooth controller, system hook, window, or preferences file is used.
"""
import unittest
from unittest.mock import Mock

from anything_plays.ui_gamepad import GamepadMixin


class Value:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Disposed(Value):
    def set(self, value):
        raise RuntimeError("PRIVATE disposed widget /Users/owner/settings.json")


class Host(GamepadMixin):
    def __init__(self):
        self._closing = False
        self.root = Mock()
        self.root.focus_get.return_value = object()
        self.root.after.return_value = "next synthetic tick"
        self.gamepad_enabled = Value(True)
        self.gamepad_status = Value("Controller ready")
        self.gamepad_diagnostics_status = Value("")
        self.system_key = Value("gba")
        self._gamepad_bindings = {"gba": {}}
        self._gamepad = Mock()
        self._gamepad.api = object()
        self._gamepad.controller = object()
        self._gamepad.physical_buttons = frozenset({"A"})
        self._gamepad.poll.return_value = (
            frozenset({"A"}), "Synthetic controller connected"
        )
        self._gamepad_last_controller = self._gamepad.controller
        self._gamepad_seen_controller = True
        self._gamepad_reconnect_release_pending = False
        self._controller_capture = None
        self._controller_capture_release_pending = False
        self._gamepad_focus_release_pending = False
        self._gamepad_game_resume_release_pending = False
        self.emu = Mock()
        self.emu.running = True
        self.uses_embedded_emulator = lambda: True
        self.save_preferences = Mock(return_value=True)
        self.refresh_controller_artwork = Mock()
        self._refresh_gamepad_live_input = Mock()

    def set_buttons(self, *names):
        raw = frozenset(names)
        self._gamepad.physical_buttons = raw
        self._gamepad.poll.return_value = (raw, "Synthetic controller connected")

    def begin_capture(self, status=None, row=None):
        self._controller_capture = {
            "system": "gba", "target": "B", "baseline": frozenset(),
            "status": status or Value("waiting"),
            "rows": {"A": row or Value("A")},
        }
        self._controller_capture_release_pending = True

    def assert_pad_kept(self, testcase):
        testcase.assertTrue(self.gamepad_enabled.get())
        self._gamepad.stop.assert_not_called()
        self.emu.release_gamepad.assert_not_called()
        self.root.after.assert_called_with(65, self.gamepad_tick)


class CaptureUiFaultTests(unittest.TestCase):
    def test_dismissed_status_on_controller_swap_preserves_enabled_pad(self):
        app = Host()
        app.begin_capture(status=Disposed())
        app._gamepad.controller = object()  # same tick as USB reconnect
        app.gamepad_tick()
        self.assertIsNone(app._controller_capture)
        self.assertTrue(app._gamepad_reconnect_release_pending)
        self.assertTrue(app._controller_capture_release_pending)
        app.emu.set_gamepad_buttons.assert_called_with(frozenset())
        app.save_preferences.assert_not_called()
        app.assert_pad_kept(self)

    def test_destroyed_row_and_status_cannot_interrupt_saved_assignment(self):
        app = Host()
        app.begin_capture(status=Disposed(), row=Disposed())
        app.gamepad_tick()
        self.assertEqual(app._gamepad_bindings["gba"]["A"], "B")
        app.save_preferences.assert_called_once()
        self.assertIsNone(app._controller_capture)
        self.assertTrue(app._controller_capture_release_pending)
        app.emu.set_gamepad_buttons.assert_called_with(frozenset())
        app.assert_pad_kept(self)
        app.set_buttons()
        app.gamepad_tick()
        self.assertFalse(app._controller_capture_release_pending)
        app.set_buttons("A")
        app.gamepad_tick()
        app.emu.set_gamepad_buttons.assert_called_with(frozenset({"A"}))

    def test_failed_disk_save_and_destroyed_notice_keep_remapping_alive(self):
        app = Host()
        app.begin_capture(status=Disposed())
        app.gamepad_diagnostics_status = Disposed()
        app.save_preferences.return_value = False
        app.gamepad_tick()
        self.assertEqual(app._gamepad_bindings["gba"], {})
        self.assertIsNotNone(app._controller_capture)
        app.emu.set_gamepad_buttons.assert_called_with(frozenset())
        app.assert_pad_kept(self)
        app.set_buttons()
        app.gamepad_tick()
        app.save_preferences.return_value = True
        app.set_buttons("A")
        app.gamepad_tick()
        self.assertIsNone(app._controller_capture)
        self.assertEqual(app._gamepad_bindings["gba"]["A"], "B")
        self.assertTrue(app.gamepad_enabled.get())

    def test_ambiguous_capture_status_fault_does_not_disable_device(self):
        app = Host()
        app.begin_capture(status=Disposed())
        app.set_buttons("A", "B")
        app.gamepad_tick()
        self.assertIsNotNone(app._controller_capture)
        app.save_preferences.assert_not_called()
        app.assert_pad_kept(self)
        app.set_buttons()
        app.gamepad_tick()
        app.set_buttons("A")
        app.gamepad_tick()
        self.assertEqual(app._gamepad_bindings["gba"]["A"], "B")

    def test_focus_query_fault_safely_releases_buttons_without_unchecking(self):
        app = Host()
        app.root.focus_get.side_effect = RuntimeError(
            "PRIVATE destroyed Tk focus path"
        )
        app.gamepad_tick()
        app.emu.set_gamepad_buttons.assert_called_with(frozenset())
        self.assertTrue(app._gamepad_focus_release_pending)
        app.assert_pad_kept(self)
        app.root.focus_get.side_effect = None
        app.gamepad_tick()  # held A must not replay on focus recovery
        app.emu.set_gamepad_buttons.assert_called_with(frozenset())
        app.set_buttons()
        app.gamepad_tick()
        self.assertFalse(app._gamepad_focus_release_pending)
        app.set_buttons("A")
        app.gamepad_tick()
        app.emu.set_gamepad_buttons.assert_called_with(frozenset({"A"}))

    def test_focus_query_fault_during_capture_cannot_learn_unfocused_input(self):
        app = Host()
        app.begin_capture(status=Disposed())
        app.root.focus_get.side_effect = OSError("PRIVATE window")
        app.gamepad_tick()
        self.assertEqual(app._gamepad_bindings["gba"], {})
        self.assertIsNotNone(app._controller_capture)
        app.assert_pad_kept(self)
        app.root.focus_get.side_effect = None
        app.gamepad_tick()  # still held: baseline prevents capture
        self.assertEqual(app._gamepad_bindings["gba"], {})
        app.set_buttons()
        app.gamepad_tick()
        app.set_buttons("A")
        app.gamepad_tick()
        self.assertEqual(app._gamepad_bindings["gba"]["A"], "B")

    def test_failed_manual_mapping_rollback_ignores_destroyed_row_and_notice(self):
        app = Host()
        app.save_preferences.return_value = False
        app.gamepad_diagnostics_status = Disposed()
        app._gamepad_bindings["gba"] = {"A": "L"}
        self.assertIs(
            app._save_gamepad_binding("gba", "A", "B", display_var=Disposed()),
            False,
        )
        self.assertEqual(app._gamepad_bindings["gba"], {"A": "L"})
        self.assertTrue(app.gamepad_enabled.get())

    def test_failed_defaults_rollback_ignores_destroyed_notice(self):
        app = Host()
        app.save_preferences.return_value = False
        app.gamepad_diagnostics_status = Disposed()
        app._gamepad_bindings["gba"] = {"A": "L"}
        close = Mock()
        self.assertIs(app._reset_gamepad_mappings("gba", close), False)
        self.assertEqual(app._gamepad_bindings["gba"], {"A": "L"})
        close.assert_not_called()

    def test_cancel_capture_with_bad_status_keeps_release_latch(self):
        app = Host()
        app.begin_capture(status=Disposed())
        app._cancel_controller_capture("Controller changed")
        self.assertIsNone(app._controller_capture)
        self.assertTrue(app._controller_capture_release_pending)
        self.assertTrue(app.gamepad_enabled.get())

    def test_healthy_status_updates_and_assignment_remain_unchanged(self):
        app = Host()
        status = Value()
        row = Value("A")
        app.begin_capture(status=status, row=row)
        app.gamepad_tick()
        self.assertEqual(row.get(), "B")
        self.assertIn("assigned to B", status.get())
        self.assertEqual(app._gamepad_bindings["gba"]["A"], "B")
        self.assertTrue(app.gamepad_enabled.get())


if __name__ == "__main__":
    unittest.main()
