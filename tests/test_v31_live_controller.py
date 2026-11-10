"""3.1 controller diagnostics without a physical gamepad or ROM.

The setup dialog shows raw SDL inputs while emulated button mappings remain
isolated. Stale input must vanish immediately on rescan or disconnect.
"""
import unittest
from types import SimpleNamespace

from anything_plays.gamepad import (
    DEADZONE, DISABLED, GamepadReader, default_bindings, normalize_bindings,
)
from anything_plays.ui_gamepad import GamepadMixin


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakePad:
    def __init__(self):
        self.connected = True
        self.closed = False

    def attached(self):
        return self.connected and not self.closed

    def get_button(self, code):
        return code == "CONTROLLER_BUTTON_A"

    def get_axis(self, code):
        return DEADZONE if code == "CONTROLLER_AXIS_LEFTX" else 0

    def quit(self):
        self.closed = True


class LiveDiagnosticTests(unittest.TestCase):
    def reader(self):
        reader = GamepadReader(clock=lambda: 0)
        pad = FakePad()
        reader.controller = pad
        reader.name = "Test controller"
        reader.api = SimpleNamespace(get_count=lambda: 0)
        reader.pygame = SimpleNamespace(
            event=SimpleNamespace(pump=lambda: None, get=lambda: [])
        )
        reader._sdl_constant = lambda name: name
        return reader, pad

    def app(self, reader):
        app = GamepadMixin()
        app._gamepad = reader
        app.gamepad_enabled = Value(True)
        app.gamepad_live_input = Value("")
        app.gamepad_status = Value("")
        app.root = SimpleNamespace(focus_get=lambda: object())
        app.refresh_controller_artwork = lambda: None
        app.emu = SimpleNamespace(release_gamepad=lambda: None)
        return app

    def test_live_input_is_raw_while_emulator_receives_remapped_button(self):
        reader, _pad = self.reader()
        held, status = reader.poll("gba", {"A": "B", "B": DISABLED})
        self.assertEqual(held, {"B", "Right"})
        self.assertEqual(reader.physical_buttons, {"A", "LEFT_STICK_RIGHT"})
        self.assertIn("connected", status)
        app = self.app(reader)
        self.assertEqual(
            app._gamepad_live_message(), "Detected: Left Stick Right, A"
        )
        app._refresh_gamepad_live_input()
        self.assertEqual(app.gamepad_live_input.get(),
                         "Detected: Left Stick Right, A")

    def test_no_rom_or_focus_required_to_read_but_focus_guards_display(self):
        reader, _pad = self.reader()
        reader.poll("gba")
        app = self.app(reader)
        # No emulator instance or game-running flag is used by diagnostics.
        self.assertIn("Detected:", app._gamepad_live_message())
        app.root = SimpleNamespace(focus_get=lambda: None)
        self.assertIn("Focus Anything Plays", app._gamepad_live_message())
        app.gamepad_enabled.set(False)
        self.assertIn("Enable gamepad", app._gamepad_live_message())

    def test_rescan_immediately_releases_held_buttons_and_raw_snapshot(self):
        reader, pad = self.reader()
        reader.poll("gba")
        releases = []
        app = self.app(reader)
        app.emu.release_gamepad = lambda: releases.append("released")
        app.refresh_gamepad()
        self.assertEqual(releases, ["released"])
        self.assertTrue(pad.closed)
        self.assertIsNone(reader.controller)
        self.assertEqual(reader.physical_buttons, frozenset())
        self.assertIn("Connect a compatible controller",
                      app.gamepad_live_input.get())

    def test_disconnected_pad_cannot_keep_raw_buttons(self):
        reader, pad = self.reader()
        reader.poll("gba")
        pad.connected = False
        held, status = reader.poll("gba")
        self.assertEqual(held, frozenset())
        self.assertIn("No compatible", status)
        self.assertEqual(reader.physical_buttons, frozenset())

    def test_corrupt_saved_bindings_are_ignored_without_disabling_gamepad(self):
        for bad in ([], {}, 3, None, False):
            with self.subTest(bad=bad):
                result = normalize_bindings("gba", {"A": bad})
                self.assertEqual(result["A"], default_bindings("gba")["A"])
        self.assertEqual(
            normalize_bindings("gba", {"A": ["B"], "B": {"target": "A"}}),
            default_bindings("gba"),
        )
        self.assertEqual(normalize_bindings("gba", {"A": "B"})["A"], "B")

    def test_excessive_simultaneous_inputs_are_truncated_for_readability(self):
        reader, _pad = self.reader()
        reader.physical_buttons = frozenset(
            ("DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT", "A", "B")
        )
        app = self.app(reader)
        message = app._gamepad_live_message()
        self.assertTrue(message.startswith("Detected: "))
        self.assertIn("(+2 more)", message)


if __name__ == "__main__":
    unittest.main()
