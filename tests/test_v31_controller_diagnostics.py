"""3.1 controller report stays local, redacts identifiers and works offline."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from anything_plays.controller_diagnostics import make_controller_report
from anything_plays.ui_gamepad import GamepadMixin


class Variable:
    def __init__(self, value):
        self.value=value

    def get(self):
        return self.value

    def set(self, value):
        self.value=value


class Clipboard:
    def __init__(self, fail=False):
        self.content=""
        self.fail=fail
        self.events=[]

    def focus_get(self):
        return object()

    def clipboard_clear(self):
        self.events.append("clear")
        if self.fail:
            raise RuntimeError("Clipboard intentionally unavailable")
        self.content=""

    def clipboard_append(self, data):
        self.events.append("append")
        self.content+=data

    def update_idletasks(self):
        self.events.append("idle")


class Reader:
    def __init__(self, with_device=True):
        self.name="Developer's private Bluetooth pad /home/user/ROMs/Game.iso"
        self.physical_buttons=frozenset({
            "A", "START", "DPAD_UP", "/home/user/ROMs/Secret.iso",
            "DEVICE_PASSWORD=private",
        })
        self.controller=object() if with_device else None
        self.pygame=SimpleNamespace(
            version=SimpleNamespace(ver="2.5.8"),
            get_sdl_version=lambda: (2, 32, 10),
        )


class ControllerPrivacyContracts(unittest.TestCase):
    def test_report_shows_useful_buttons_and_remapping_without_private_strings(self):
        result=make_controller_report(
            Reader(),
            system="gba", mappings={"A":"B"},
            enabled=True, focused=True, emulator_running=True,
            camera_armed=True,
        )
        self.assertEqual(result["selected_console"], "gba")
        self.assertEqual(result["pygame_ce_version"], "2.5.8")
        self.assertEqual(result["sdl_version"], "2.32.10")
        self.assertIn("A", result["physical_inputs_detected"])
        self.assertIn("START", result["physical_inputs_detected"])
        self.assertIn("B", result["mapped_emulator_buttons"])
        self.assertTrue(result["camera_tracking_armed"])
        self.assertTrue(result["controller_enabled"])
        self.assertFalse(result["physical_device_acceptance_verified"])
        self.assertFalse(result["redistribution_approved"])
        serialized=json.dumps(result)
        for secret in ("Developer", "/home/user", "Secret.iso",
                       "DEVICE_PASSWORD", "Game.iso"):
            self.assertNotIn(secret, serialized)

    def test_disconnected_controller_or_uninitialized_pygame_still_reports(self):
        reader=Reader(False)
        reader.pygame=None
        reader.physical_buttons="DO_NOT_LOOP_OVER_STRING"
        result=make_controller_report(reader, system="snes", enabled=False)
        self.assertFalse(result["controller_handle_present"])
        self.assertFalse(result["controller_enabled"])
        self.assertEqual(result["physical_inputs_detected"], [])
        self.assertIsNone(result["sdl_version"])
        self.assertIsNone(result["pygame_ce_version"])

    def test_unknown_console_is_rejected_not_serialized(self):
        with self.assertRaises(ValueError):
            make_controller_report(Reader(), system="/home/private/ROM")

    def test_clipboard_button_copies_json_without_file_or_network(self):
        app=GamepadMixin()
        root=Clipboard()
        app.root=root
        app._gamepad=Reader()
        app.system_key=Variable("gba")
        app._gamepad_bindings={"gba":{"A":"B"}}
        app.gamepad_enabled=Variable(True)
        app.gamepad_status=Variable("")
        app.emu=SimpleNamespace(running=True)
        app.armed=True
        self.assertTrue(app.copy_gamepad_diagnostics())
        report=json.loads(root.content)
        self.assertEqual(report["selected_console"],"gba")
        self.assertEqual(report["mapped_emulator_buttons"],["B","Start","Up"])
        self.assertIn("Controller diagnostics copied",app.gamepad_status.get())
        self.assertEqual(root.events,["clear","append","idle"])
        self.assertNotIn("/home/user",root.content)
        self.assertNotIn("Developer",root.content)

    def test_clipboard_failure_is_visible_and_does_not_claim_success(self):
        app=GamepadMixin()
        app.root=Clipboard(fail=True)
        app._gamepad=Reader(False)
        app.system_key=Variable("gba")
        app._gamepad_bindings={}
        app.gamepad_enabled=Variable(False)
        app.gamepad_status=Variable("")
        app.emu=SimpleNamespace(running=False)
        app.armed=False
        self.assertFalse(app.copy_gamepad_diagnostics())
        self.assertIn("Could not copy",app.gamepad_status.get())

    def test_right_hand_controller_settings_have_real_copy_control(self):
        source=(Path(__file__).resolve().parents[1] /
                "anything_plays/ui_gamepad.py").read_text("utf-8")
        self.assertIn('text="Copy diagnostics"',source)
        self.assertIn("command=self.copy_gamepad_diagnostics",source)
        self.assertIn("self.root.clipboard_append",source)
        self.assertNotIn("requests.post",source)


if __name__ == "__main__":
    unittest.main()
