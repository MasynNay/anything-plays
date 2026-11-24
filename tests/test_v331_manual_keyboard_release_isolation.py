"""3.3.1: broken native/IPC keyboard hooks never skip independent releases.

Only fake Tk events, emulators, manual-input latches, and remote bridges.
No ROM files, real key hooks, window, controller, or external processes.
"""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from anything_plays.ui_gameplay import GameplayMixin


class Label:
    def __init__(self, message=""):
        self.value = message

    def set(self, message):
        self.value = message

    def get(self):
        return self.value


class Host(GameplayMixin):
    def __init__(self, *, external=False):
        self.manual_active = True
        self.emu = Mock()
        self.external_input = Mock() if external else None
        self.manual_label = Label("MANUAL PLAY ACTIVE")
        self.system_key = Label("gba")
        self._shortcut_bindings = {}
        self.uses_embedded_emulator = Mock(return_value=not external)
        self.stop_external_emulator = Mock(side_effect=self._stop_external)

    def _stop_external(self):
        bridge = self.external_input
        if bridge is not None:
            bridge.close()
            self.external_input = None


def event(keysym="z"):
    return SimpleNamespace(keysym=keysym)


class ManualReleaseTests(unittest.TestCase):
    def test_normal_deactivate_releases_native_and_external(self):
        app = Host(external=True)
        bridge = app.external_input
        app.deactivate_manual()
        app.emu.release_manual.assert_called_once()
        bridge.release_manual.assert_called_once()
        self.assertFalse(app.manual_active)
        self.assertIn("Click game screen", app.manual_label.get())
        app.stop_external_emulator.assert_not_called()

    def test_native_facade_failure_falls_back_and_still_releases_external(self):
        app = Host(external=True)
        app.emu.release_manual.side_effect = OSError(
            "PRIVATE /Users/person/native device"
        )
        bridge = app.external_input
        app.deactivate_manual()
        app.emu.inputs.release_manual.assert_called_once()
        bridge.release_manual.assert_called_once()
        self.assertFalse(app.manual_active)
        self.assertNotIn("PRIVATE", app.manual_label.get())

    def test_native_fallback_failure_does_not_block_external_release(self):
        app = Host(external=True)
        app.emu.release_manual.side_effect = RuntimeError("facade")
        app.emu.inputs.release_manual.side_effect = RuntimeError("buffer")
        bridge = app.external_input
        app.deactivate_manual()
        bridge.release_manual.assert_called_once()
        app.stop_external_emulator.assert_not_called()
        self.assertFalse(app.manual_active)

    def test_external_release_failure_retires_external_process(self):
        app = Host(external=True)
        bridge = app.external_input
        bridge.release_manual.side_effect = OSError(
            "PRIVATE pipe /Users/person/IPC"
        )
        app.deactivate_manual()
        app.emu.release_manual.assert_called_once()
        app.stop_external_emulator.assert_called_once()
        bridge.close.assert_called_once()
        self.assertIsNone(app.external_input)
        self.assertFalse(app.manual_active)

    def test_failing_external_close_does_not_escape_native_release(self):
        app = Host(external=True)
        bridge = app.external_input
        bridge.release_manual.side_effect = OSError("dead pipe")
        bridge.close.side_effect = RuntimeError("broken close")
        app.deactivate_manual()
        app.emu.release_manual.assert_called_once()
        self.assertIsNone(app.external_input)
        self.assertFalse(app.manual_active)

    def test_missing_external_shutdown_hook_closes_bridge(self):
        app = Host(external=True)
        bridge = app.external_input
        bridge.release_manual.side_effect = OSError("pipe detached")
        app.stop_external_emulator = None
        app.deactivate_manual()
        bridge.close.assert_called_once()
        self.assertIsNone(app.external_input)

    def test_destroyed_manual_label_cannot_skip_release(self):
        app = Host(external=True)
        bridge = app.external_input
        app.manual_label = Mock()
        app.manual_label.set.side_effect = RuntimeError("destroyed Tk widget")
        app.deactivate_manual()
        app.emu.release_manual.assert_called_once()
        bridge.release_manual.assert_called_once()
        self.assertFalse(app.manual_active)

    def test_embedded_key_press_and_release_still_work(self):
        app = Host()
        self.assertEqual(app.manual_key_down(event("z")), "break")
        self.assertEqual(app.manual_key_up(event("z")), "break")
        app.emu.set_manual.assert_any_call("A", True)
        app.emu.set_manual.assert_any_call("A", False)
        self.assertTrue(app.manual_active)

    def test_external_key_press_and_release_still_work(self):
        app = Host(external=True)
        bridge = app.external_input
        app.manual_key_down(event("z"))
        app.manual_key_up(event("z"))
        bridge.set_manual.assert_any_call("A", True)
        bridge.set_manual.assert_any_call("A", False)
        app.emu.set_manual.assert_called_once_with("A", False)
        self.assertTrue(app.manual_active)

    def test_native_press_failure_disarms_manual_without_leaking_error(self):
        app = Host()
        app.emu.set_manual.side_effect = OSError(
            "PRIVATE /home/person/keyboard"
        )
        self.assertEqual(app.manual_key_down(event("z")), "break")
        app.emu.release_manual.assert_called_once()
        self.assertFalse(app.manual_active)
        self.assertIn("Manual input paused", app.manual_label.get())
        self.assertNotIn("PRIVATE", app.manual_label.get())

    def test_external_press_failure_retires_broken_bridge(self):
        app = Host(external=True)
        bridge = app.external_input
        bridge.set_manual.side_effect = OSError("PRIVATE external IPC")
        self.assertEqual(app.manual_key_down(event("z")), "break")
        bridge.release_manual.assert_called_once()
        # Release itself succeeds, so the process need not be killed.
        app.stop_external_emulator.assert_not_called()
        app.emu.release_manual.assert_called_once()
        self.assertFalse(app.manual_active)

    def test_external_release_failure_does_not_skip_native_release(self):
        app = Host(external=True)
        bridge = app.external_input
        bridge.set_manual.side_effect = RuntimeError("PRIVATE OS pipe")
        self.assertEqual(app.manual_key_up(event("z")), "break")
        app.emu.set_manual.assert_called_once_with("A", False)
        app.emu.release_manual.assert_called_once()
        bridge.release_manual.assert_called_once()
        self.assertFalse(app.manual_active)

    def test_native_release_failure_does_not_skip_external_key_release(self):
        app = Host(external=True)
        bridge = app.external_input
        app.emu.set_manual.side_effect = OSError("PRIVATE native input")
        self.assertEqual(app.manual_key_up(event("z")), "break")
        bridge.set_manual.assert_called_once_with("A", False)
        bridge.release_manual.assert_called_once()
        app.emu.release_manual.assert_called_once()
        self.assertFalse(app.manual_active)

    def test_unknown_key_does_not_modify_native_or_external_input(self):
        app = Host(external=True)
        self.assertIsNone(app.manual_key_down(event("F12")))
        self.assertIsNone(app.manual_key_up(event("F12")))
        app.emu.set_manual.assert_not_called()
        app.external_input.set_manual.assert_not_called()

    def test_release_after_focus_loss_does_not_rearm_input(self):
        app = Host()
        app.deactivate_manual()
        self.assertFalse(app.manual_active)
        self.assertIsNone(app.manual_key_down(event("z")))
        self.assertEqual(app.manual_key_up(event("z")), "break")
        app.emu.set_manual.assert_called_once_with("A", False)


if __name__ == "__main__":
    unittest.main()
