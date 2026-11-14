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
