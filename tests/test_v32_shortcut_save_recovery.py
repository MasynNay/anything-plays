"""Keyboard key binding changes are transactional across disk failures.

Uses an in-memory synthetic preferences host. No Tk display, game,
controller, actual filesystem settings or external programs are opened.
"""

import unittest
from unittest.mock import Mock, patch

from anything_plays.shortcuts import DEFAULT_KEYS
from anything_plays.ui_shortcuts import ShortcutsMixin
from tools.verify_v32_installed_gui import REQUIRED_TRUE


class ShortcutHost(ShortcutsMixin):
    def __init__(self):
        self._shortcut_bindings = {"gba": {"A": "v"}, "snes": {"B": "m"}}
        self._shortcut_window = object()
        self.success = True
        self.error = None
        self.saves = 0
        self.opens = 0

    def save_preferences(self):
        self.saves += 1
        if self.error:
            raise self.error
        return self.success

    def configure_shortcuts(self):
        self.opens += 1


class ShortcutPersistenceTests(unittest.TestCase):
    def test_private_installers_require_keyboard_write_recovery(self):
        self.assertIn("v32_keyboard_rejected_save_verified", REQUIRED_TRUE)

    def test_change_success_updates_only_active_console(self):
        app = ShortcutHost()
        new = app._save_shortcut_binding("gba", "A", "n")
        self.assertEqual(new["A"], "n")
        self.assertEqual(app._shortcut_bindings["gba"]["A"], "n")
        self.assertEqual(app._shortcut_bindings["snes"], {"B": "m"})
        self.assertEqual(app.saves, 1)

    def test_rejected_write_keeps_previous_keys_and_other_consoles(self):
        app = ShortcutHost()
        before = dict(app._shortcut_bindings["gba"])
        other = dict(app._shortcut_bindings["snes"])
        app.success = False
        self.assertFalse(app._save_shortcut_binding("gba", "A", "n"))
        self.assertEqual(app._shortcut_bindings["gba"], before)
        self.assertEqual(app._shortcut_bindings["snes"], other)
        app.success = True
        self.assertEqual(app._save_shortcut_binding("gba", "A", "n")["A"], "n")

    def test_missing_mapping_is_not_created_on_failed_save(self):
        app = ShortcutHost()
        app._shortcut_bindings.pop("gba")
        app.error = OSError("simulated private directory full")
        self.assertFalse(app._save_shortcut_binding("gba", "A", "n"))
        self.assertNotIn("gba", app._shortcut_bindings)

    def test_collision_is_rejected_before_any_write(self):
        app = ShortcutHost()
        with self.assertRaisesRegex(ValueError, "assigned"):
            app._save_shortcut_binding("gba", "A", DEFAULT_KEYS["B"])
        self.assertEqual(app.saves, 0)
        self.assertEqual(app._shortcut_bindings["gba"], {"A": "v"})

    def test_reset_does_not_close_dialog_after_failed_persistence(self):
        app = ShortcutHost()
        parent = Mock()
        app.success = False
        with patch(
            "anything_plays.ui_shortcuts.messagebox.showwarning",
        ) as warning:
            self.assertFalse(app._reset_shortcuts("gba", parent))
        warning.assert_called_once()
        self.assertIs(warning.call_args.kwargs["parent"], parent)
        parent.destroy.assert_not_called()
        self.assertEqual(app.opens, 0)
        self.assertEqual(app._shortcut_bindings["gba"], {"A": "v"})
        self.assertIsNotNone(app._shortcut_window)

        app.success = True
        self.assertTrue(app._reset_shortcuts("gba", parent))
        parent.destroy.assert_called_once()
        self.assertEqual(app.opens, 1)
        self.assertNotIn("gba", app._shortcut_bindings)
        self.assertIsNone(app._shortcut_window)

    def test_reset_restores_prior_state_when_saving_raises(self):
        app = ShortcutHost()
        app.error = OSError("simulated storage failure")
        with patch("anything_plays.ui_shortcuts.messagebox.showwarning"):
            self.assertFalse(app._reset_shortcuts("gba", Mock()))
        self.assertEqual(app._shortcut_bindings["gba"], {"A": "v"})


if __name__ == "__main__":
    unittest.main()
