"""Synthetic, deterministic press-to-remap regression checks."""

import unittest

from anything_plays.controller_capture import newly_pressed_source
from anything_plays.ui_gamepad import GamepadMixin


class Setting:
    def __init__(self, value=None):
        self.value = value
    def set(self, value):
        self.value = value
    def get(self):
        return self.value


class Reader:
    def __init__(self):
        self.controller = object()
        self.physical_buttons = frozenset()
        self.api = object()

    def poll(self, system, settings):
        return frozenset({"A"}) if "A" in self.physical_buttons else frozenset(), "connected"


class Emu:
    def __init__(self):
        self.running = True
        self.released = 0
        self.published = []

    def release_gamepad(self):
        self.released += 1

    def set_gamepad_buttons(self, buttons):
        self.published.append(frozenset(buttons))


class Root:
    focused = True
    def focus_get(self):
        return object() if self.focused else None

    def after(self, ms, callback):
        return 123


class CaptureHost(GamepadMixin):
    def __init__(self):
        self._closing = False
        self._controller_capture_release_pending = False
        self._gamepad_last_controller = None
        self._gamepad_seen_controller = False
        self._gamepad_reconnect_release_pending = False
        self._gamepad = Reader()
        self._gamepad_bindings = {}
        self._controller_capture = None
        self.gamepad_enabled = Setting(True)
        self.system_key = Setting("gba")
        self.gamepad_status = Setting("idle")
        self.root = Root()
        self.emu = Emu()
        self.saved = 0

    def save_preferences(self):
        self.saved += 1

    def uses_embedded_emulator(self):
        return True

    def refresh_controller_artwork(self):
        return None

    def _refresh_gamepad_live_input(self):
        return None


class ControllerCaptureTests(unittest.TestCase):
    def test_failed_press_mapping_retries_without_claiming_assignment(self):
        app = CaptureHost()
        status, row = Setting(), Setting("A")
        app._controller_capture = {
            "system": "gba", "target": "B",
            "baseline": frozenset(), "status": status,
            "rows": {"A": row},
        }
        app.save_preferences = lambda: False
        app._gamepad.physical_buttons = frozenset({"A"})
        app._controller_capture_tick("gba")
        self.assertEqual(app._gamepad_bindings, {})
        self.assertIsNotNone(app._controller_capture)
        self.assertEqual(row.get(), "A")
        self.assertIn("could not be saved", status.get())
        self.assertNotIn("assigned to", status.get())
        app.save_preferences = lambda: True
        app._gamepad.physical_buttons = frozenset()
        app._controller_capture_tick("gba")
        app._gamepad.physical_buttons = frozenset({"A"})
        app._controller_capture_tick("gba")
        self.assertEqual(app._gamepad_bindings["gba"]["A"], "B")
        self.assertEqual(row.get(), "B")
        self.assertIsNone(app._controller_capture)

    def test_failed_manual_mapping_restores_selector_and_prior_binding(self):
        app = CaptureHost()
        app._gamepad_bindings["gba"] = {"A": "X"}
        row = Setting("B")
        app.save_preferences = lambda: False
        self.assertFalse(app._save_gamepad_binding(
            "gba", "A", "B", display_var=row,
        ))
        self.assertEqual(app._gamepad_bindings["gba"], {"A": "X"})
        self.assertEqual(row.get(), "X")

    def test_failed_reset_defaults_keeps_mapping_and_dialog_open(self):
        app = CaptureHost()
        app._gamepad_bindings["gba"] = {"A": "B"}
        app.save_preferences = lambda: False
        closed = []
        self.assertFalse(app._reset_gamepad_mappings(
            "gba", lambda: closed.append(True),
        ))
        self.assertEqual(app._gamepad_bindings["gba"], {"A": "B"})
        self.assertEqual(closed, [])

    def test_one_edge_is_selected_and_held_button_is_not_repeated(self):
        src, baseline, ambiguous = newly_pressed_source(
            frozenset(), {"A"},
        )
        self.assertEqual(src, "A")
        self.assertFalse(ambiguous)
        self.assertEqual(
            newly_pressed_source(baseline, {"A"})[0], None,
        )
        self.assertEqual(
            newly_pressed_source(baseline, set())[0], None,
        )
        self.assertEqual(
            newly_pressed_source(set(), {"A"})[0], "A",
        )

    def test_simultaneous_buttons_are_not_assigned(self):
        src, baseline, ambiguous = newly_pressed_source(
            frozenset(), {"A", "B"},
        )
        self.assertIsNone(src)
        self.assertEqual(baseline, frozenset({"A", "B"}))
        self.assertTrue(ambiguous)

    def test_unknown_controls_are_not_assignable(self):
        src, baseline, ambiguous = newly_pressed_source(
            frozenset(), {"unknown", "A"},
        )
        self.assertEqual(src, "A")
        self.assertEqual(baseline, frozenset({"A"}))
        self.assertFalse(ambiguous)

    def test_mapping_commit_and_wait_for_release_without_game_input(self):
        app = CaptureHost()
        status, mapping = Setting(), Setting()
        app._controller_capture = {
            "system": "gba", "target": "B",
            "baseline": frozenset(), "status": status,
            "rows": {"A": mapping},
        }
        app._controller_capture_release_pending = True
        app._gamepad.physical_buttons = frozenset({"A"})
        app.gamepad_tick()
        self.assertEqual(app._gamepad_bindings["gba"]["A"], "B")
        self.assertEqual(mapping.get(), "B")
        self.assertIn("assigned to B", status.get())
        self.assertIsNone(app._controller_capture)
        self.assertEqual(app.emu.published, [frozenset()])
        app.gamepad_tick()  # still pressed: no accidental emulator press
        self.assertEqual(app.emu.published[-1], frozenset())
        app._gamepad.physical_buttons = frozenset()
        app.gamepad_tick()
        self.assertFalse(app._controller_capture_release_pending)
        app._gamepad.physical_buttons = frozenset({"A"})
        app.gamepad_tick()  # normal play can resume after release
        self.assertEqual(app.emu.published[-1], frozenset({"A"}))

    def test_focus_loss_and_return_waits_for_neutral_controller(self):
        app = CaptureHost()
        app._gamepad.physical_buttons = frozenset({"A"})
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset({"A"}))
        app.root.focused = False
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset())
        self.assertTrue(app._gamepad_focus_release_pending)
        app.root.focused = True
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset())
        self.assertIn("Release controller inputs", app.gamepad_status.get())
        app._gamepad.physical_buttons = frozenset({"A", "B"})
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset())
        app._gamepad.physical_buttons = frozenset()
        app.gamepad_tick()
        self.assertFalse(app._gamepad_focus_release_pending)
        app._gamepad.physical_buttons = frozenset({"A"})
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset({"A"}))

    def test_press_started_while_unfocused_cannot_enter_on_refocus(self):
        app = CaptureHost()
        app.root.focused = False
        app.gamepad_tick()
        app._gamepad.physical_buttons = frozenset({"A"})
        app.gamepad_tick()
        app.root.focused = True
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset())
        self.assertTrue(app._gamepad_focus_release_pending)
        app._gamepad.physical_buttons = frozenset()
        app.gamepad_tick()
        app._gamepad.physical_buttons = frozenset({"A"})
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset({"A"}))

    def test_neutral_focus_return_does_not_delay_new_gameplay_press(self):
        app = CaptureHost()
        app.root.focused = False
        app.gamepad_tick()
        app.root.focused = True
        app.gamepad_tick()
        self.assertFalse(app._gamepad_focus_release_pending)
        app._gamepad.physical_buttons = frozenset({"A"})
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset({"A"}))

    def test_hot_unplug_new_pad_requires_release_before_game_input(self):
        app = CaptureHost()
        app._gamepad.physical_buttons = frozenset({"A"})
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset({"A"}))
        app._gamepad.controller = None
        app._gamepad.physical_buttons = frozenset()
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset())
        self.assertTrue(app._gamepad_reconnect_release_pending)
        app._gamepad.controller = object()
        app._gamepad.physical_buttons = frozenset({"A"})
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset())
        self.assertTrue(app._gamepad_reconnect_release_pending)
        self.assertIn("after reconnecting", app.gamepad_status.get())
        app._gamepad.physical_buttons = frozenset()
        app.gamepad_tick()
        self.assertFalse(app._gamepad_reconnect_release_pending)
        app._gamepad.physical_buttons = frozenset({"A"})
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset({"A"}))

    def test_switching_between_connected_devices_suppresses_held_buttons(self):
        app = CaptureHost()
        app.gamepad_tick()  # Existing first device, initially neutral
        app._gamepad.physical_buttons = frozenset({"A"})
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset({"A"}))
        app._gamepad.controller = object()  # different USB/Bluetooth device
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset())
        self.assertTrue(app._gamepad_reconnect_release_pending)
        app._gamepad.physical_buttons = frozenset()
        app.gamepad_tick()
        self.assertFalse(app._gamepad_reconnect_release_pending)
        app._gamepad.physical_buttons = frozenset({"A"})
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset({"A"}))

    def test_controller_swap_during_remap_cancels_without_assigning_button(self):
        app = CaptureHost()
        app.gamepad_tick()  # establish original device identity
        note = Setting()
        app._controller_capture = {
            "system": "gba", "target": "B",
            "baseline": frozenset(), "status": note, "rows": {},
        }
        app._gamepad.controller = object()
        app._gamepad.physical_buttons = frozenset({"A"})
        app.gamepad_tick()
        self.assertIsNone(app._controller_capture)
        self.assertEqual(app._gamepad_bindings, {})
        self.assertEqual(app.saved, 0)
        self.assertIn("Controller changed", note.get())
        self.assertTrue(app._controller_capture_release_pending)
        self.assertEqual(app.emu.published[-1], frozenset())
        app._gamepad.physical_buttons = frozenset()
        app.gamepad_tick()
        self.assertFalse(app._controller_capture_release_pending)
        self.assertFalse(app._gamepad_reconnect_release_pending)

    def test_initial_controller_enable_keeps_first_ordinary_press_responsive(self):
        app = CaptureHost()
        app._gamepad.physical_buttons = frozenset({"A"})
        app.gamepad_tick()
        self.assertEqual(app.emu.published[-1], frozenset({"A"}))
        self.assertFalse(app._gamepad_reconnect_release_pending)

    def test_disconnected_capture_is_canceled_without_saving(self):
        app = CaptureHost()
        status = Setting()
        app._controller_capture = {
            "system": "gba", "target": "B",
            "baseline": frozenset(), "status": status, "rows": {},
        }
        app._gamepad.controller = None
        app._controller_capture_tick("gba")
        self.assertIsNone(app._controller_capture)
        self.assertEqual(app.saved, 0)
        self.assertTrue(app._controller_capture_release_pending)
        self.assertIn("disconnected", status.get())

    def test_out_of_focus_input_cannot_assign_a_button(self):
        app = CaptureHost()
        status = Setting()
        app._controller_capture = {
            "system": "gba", "target": "B",
            "baseline": frozenset(), "status": status, "rows": {},
        }
        app.root.focused = False
        app._gamepad.physical_buttons = frozenset({"A"})
        app._controller_capture_tick("gba")
        self.assertEqual(app._gamepad_bindings, {})
        self.assertIn("Focus Anything Plays", status.get())
        app.root.focused = True
        app._controller_capture_tick("gba")
        self.assertEqual(app._gamepad_bindings, {})
        app._gamepad.physical_buttons = frozenset()
        app._controller_capture_tick("gba")
        app._gamepad.physical_buttons = frozenset({"A"})
        app._controller_capture_tick("gba")
        self.assertEqual(app._gamepad_bindings["gba"]["A"], "B")

    def test_switching_console_does_not_map_previous_device(self):
        app = CaptureHost()
        status = Setting()
        app._controller_capture = {
            "system": "gba", "target": "B",
            "baseline": frozenset(), "status": status, "rows": {},
        }
        app._gamepad.physical_buttons = frozenset({"A"})
        app._controller_capture_tick("snes")
        self.assertEqual(app._gamepad_bindings, {})
        self.assertIn("Console changed", status.get())


if __name__ == "__main__":
    unittest.main()
