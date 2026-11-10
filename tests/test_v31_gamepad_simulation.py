"""Run synthetic SDL controller actions through the real 3.1 input pipeline.

CI runs these on Windows, Linux and both Mac architectures without controllers
or game ROMs. An actual SDL initialization test complements the fake device;
physical HID/Bluetooth compatibility still requires real hardware.
"""
import unittest
from unittest.mock import patch

from anything_plays.gamepad import DEADZONE, TRIGGER_THRESHOLD, GamepadReader
from anything_plays.libretro_input import IDS, InputBuffer
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM
from anything_plays.ui_gamepad import GamepadMixin


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Subsystem:
    def init(self):
        pass

    def quit(self):
        pass


class Queue:
    def __init__(self):
        self.pumps = 0
        self.drains = 0

    def pump(self):
        self.pumps += 1

    def get(self):
        self.drains += 1
        return []


class SyntheticPygame:
    def __init__(self):
        self.event = Queue()
        self.display = Subsystem()
        self.joystick = Subsystem()


class VirtualPad:
    def __init__(self):
        self.buttons = set()
        self.axes = {}
        self.connected = True
        self.closed = False
        self.broken = False

    def attached(self):
        return self.connected and not self.closed

    def get_button(self, code):
        if self.broken:
            raise OSError("Virtual USB controller disconnected")
        return code in self.buttons

    def get_axis(self, code):
        if self.broken:
            raise OSError("Virtual USB controller disconnected")
        return self.axes.get(code, 0)

    def quit(self):
        self.closed = True


class SyntheticSDL:
    def __init__(self, devices):
        self.devices = devices
        for name in ("DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT",
                     "A", "B", "X", "Y", "BACK", "START",
                     "LEFTSHOULDER", "RIGHTSHOULDER"):
            setattr(self, "CONTROLLER_BUTTON_" + name, name)
        for name in ("LEFTX", "LEFTY", "RIGHTX", "RIGHTY",
                     "TRIGGERLEFT", "TRIGGERRIGHT"):
            setattr(self, "CONTROLLER_AXIS_" + name, name)

    def init(self):
        pass

    def quit(self):
        pass

    def get_count(self):
        return len(self.devices)

    def is_controller(self, index):
        return 0 <= index < len(self.devices)

    def Controller(self, index):
        return self.devices[index]

    def name_forindex(self, index):
        return "Virtual controller · no hardware"


class VirtualRoot:
    def __init__(self):
        self.focus = object()
        self.jobs = []

    def focus_get(self):
        return self.focus

    def after(self, delay, callback):
        self.jobs.append((delay, callback))
        return len(self.jobs)


class VirtualEmulator:
    def __init__(self, system="gba"):
        self.inputs = InputBuffer()
        self.inputs.system = system
        self.running = True

    def set_gamepad_buttons(self, buttons):
        self.inputs.set_gamepad_buttons(buttons)

    def release_gamepad(self):
        self.inputs.release_gamepad()


class VirtualControllerTests(unittest.TestCase):
    def setUp(self):
        self.time = 0.0
        self.pad = VirtualPad()
        self.devices = [self.pad]
        self.sdl = SyntheticSDL(self.devices)
        self.pg = SyntheticPygame()
        self.reader = GamepadReader(
            clock=lambda: self.time, loader=lambda: self.pg
        )
        patcher = patch(
            "anything_plays.gamepad.importlib.import_module",
            return_value=self.sdl
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.reader.start()
        self.addCleanup(self.reader.stop)

    def frame(self, system="gba", mappings=None, emulator=None):
        emu = emulator or VirtualEmulator(system)
        emu.inputs.system = system
        held, message = self.reader.poll(system, mappings)
        emu.set_gamepad_buttons(held)
        emu.inputs.before_frame(False)
        return emu, held, message

    def ui(self):
        app = GamepadMixin()
        app._closing = False
        app.root = VirtualRoot()
        app.emu = VirtualEmulator()
        app._gamepad = self.reader
        app._gamepad_bindings = {"gba": {"A": "B"}}
        app.gamepad_enabled = Value(True)
        app.gamepad_status = Value("")
        app.system_key = Value("gba")
        app.uses_embedded_emulator = lambda: True
        app.save_preferences = lambda: None
        app.refresh_controller_artwork = lambda: None
        return app

    def test_all_eighteen_consoles_reach_libretro_callback(self):
        self.pad.buttons = {"A", "START", "DPAD_UP"}
        self.assertEqual(len(BUTTONS_BY_SYSTEM), 18)
        for console in BUTTONS_BY_SYSTEM:
            with self.subTest(console=console):
                emu, held, status = self.frame(console)
                self.assertEqual(held, {"A", "Start", "Up"})
                self.assertIn("Virtual controller", status)
                if console in ("n64", "gamecube"):
                    self.assertEqual(emu.inputs.state(0, 1, 0, 8), 1)
                    self.assertEqual(emu.inputs.state(0, 1, 0, 3), 1)
                    self.assertEqual(emu.inputs.state(0, 5, 0, 1), -28000)
                else:
                    self.assertEqual(
                        emu.inputs.state(0, 1, 0, emu.inputs.id_for("A")), 1
                    )
                    self.assertEqual(
                        emu.inputs.state(0, 1, 0, emu.inputs.id_for("Up")), 1
                    )
                self.assertEqual(emu.inputs.state(1, 1, 0, IDS["A"]), 0)

    def test_stick_deadzone_and_trigger_boundary(self):
        self.pad.axes = {
            "LEFTX": DEADZONE - 1,
            "RIGHTY": -(DEADZONE - 1),
            "TRIGGERLEFT": TRIGGER_THRESHOLD - 1,
        }
        self.assertFalse(self.frame("n64")[1])
        self.pad.axes = {
            "LEFTX": DEADZONE, "RIGHTY": -DEADZONE,
            "TRIGGERLEFT": TRIGGER_THRESHOLD,
        }
        emu, held, _status = self.frame("n64")
        self.assertEqual(held, {"Right", "C Up", "Z"})
        self.assertEqual(emu.inputs.state(0, 5, 0, 0), 28000)
        self.assertEqual(emu.inputs.state(0, 5, 1, 1), -28000)

    def test_gamecube_second_stick_and_trigger(self):
        self.pad.axes = {
            "RIGHTX": DEADZONE + 7, "TRIGGERRIGHT": TRIGGER_THRESHOLD
        }
        emu, held, _status = self.frame("gamecube")
        self.assertEqual(held, {"C Right", "R"})
        self.assertEqual(emu.inputs.state(0, 5, 1, 0), 28000)
        self.assertEqual(emu.inputs.state(0, 1, 0, 13), 1)

    def test_keyboard_and_controller_can_hold_same_and_different_buttons(self):
        self.pad.buttons = {"A", "B"}
        emu = VirtualEmulator()
        emu.inputs.set_manual("A", True)
        emu, held, _ = self.frame(
            "gba", {"A": "B", "B": "(None)"}, emu
        )
        self.assertEqual(held, {"B"})
        self.assertEqual(emu.inputs.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(emu.inputs.state(0, 1, 0, IDS["B"]), 1)
        self.pad.buttons.clear()
        self.frame("gba", emulator=emu)
        self.assertEqual(emu.inputs.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(emu.inputs.state(0, 1, 0, IDS["B"]), 0)
        emu.inputs.release_manual()
        emu.inputs.before_frame(False)
        self.assertEqual(emu.inputs.state(0, 1, 0, IDS["A"]), 0)

    def test_unplug_and_reconnect_release_buttons(self):
        self.pad.buttons = {"A"}
        emu, _held, _ = self.frame()
        self.assertEqual(emu.inputs.state(0, 1, 0, IDS["A"]), 1)
        self.pad.connected = False
        self.devices.clear()
        self.frame(emulator=emu)
        self.assertEqual(emu.inputs.state(0, 1, 0, IDS["A"]), 0)
        self.assertTrue(self.pad.closed)
        new_pad = VirtualPad()
        new_pad.buttons = {"B"}
        self.devices.append(new_pad)
        self.time = 1.6
        emu, held, _ = self.frame(emulator=emu)
        self.assertEqual(held, {"B"})
        self.assertEqual(emu.inputs.state(0, 1, 0, IDS["B"]), 1)
        self.assertEqual(emu.inputs.state(0, 1, 0, IDS["A"]), 0)

    def test_failure_mid_button_read_never_leaves_stale_input(self):
        self.pad.buttons = {"A"}
        emu, _held, _ = self.frame()
        self.pad.broken = True
        emu, held, status = self.frame(emulator=emu)
        self.assertFalse(held)
        self.assertIn("disconnected", status)
        self.assertEqual(emu.inputs.state(0, 1, 0, IDS["A"]), 0)

    def test_six_hundred_frames_do_not_stick_or_accumulate_events(self):
        emu = VirtualEmulator("snes")
        for index in range(600):
            self.pad.buttons = (
                {"A"} if index % 3 == 0 else
                {"B"} if index % 3 == 1 else set()
            )
            emu, held, _ = self.frame("snes", emulator=emu)
            self.assertEqual(
                emu.inputs.state(0, 1, 0, IDS["A"]), int("A" in held)
            )
            self.assertEqual(
                emu.inputs.state(0, 1, 0, IDS["B"]), int("B" in held)
            )
        self.assertEqual(self.pg.event.pumps, 600)
        self.assertEqual(self.pg.event.drains, 600)

    def test_ui_tick_releases_controller_when_window_loses_focus(self):
        app = self.ui()
        self.pad.buttons = {"A"}
        app.gamepad_tick()
        app.emu.inputs.before_frame(False)
        self.assertEqual(app.emu.inputs.state(0, 1, 0, IDS["B"]), 1)
        app.root.focus = None
        app.gamepad_tick()
        app.emu.inputs.before_frame(False)
        self.assertEqual(app.emu.inputs.state(0, 1, 0, IDS["B"]), 0)
        app.root.focus = object()
        app.gamepad_tick()
        app.emu.inputs.before_frame(False)
        self.assertEqual(app.emu.inputs.state(0, 1, 0, IDS["B"]), 1)
        self.assertEqual([delay for delay, _cb in app.root.jobs], [65] * 3)

    def test_ui_stops_gamepad_for_no_game_or_external_emulator(self):
        app = self.ui()
        self.pad.buttons = {"A"}
        app.emu.running = False
        app.gamepad_tick()
        app.emu.inputs.before_frame(False)
        self.assertEqual(app.emu.inputs.state(0, 1, 0, IDS["B"]), 0)
        app.emu.running = True
        app.uses_embedded_emulator = lambda: False
        app.gamepad_tick()
        app.emu.inputs.before_frame(False)
        self.assertEqual(app.emu.inputs.state(0, 1, 0, IDS["B"]), 0)
        self.assertIn("Embedded emulators only", app.gamepad_status.get())

    def test_switching_consoles_uses_independent_bindings(self):
        app = self.ui()
        self.pad.buttons = {"A"}
        app.gamepad_tick()
        app.emu.inputs.before_frame(False)
        self.assertEqual(app.emu.inputs.state(0, 1, 0, IDS["B"]), 1)
        app.system_key.set("snes")
        app.emu.inputs.system = "snes"
        app.gamepad_tick()
        app.emu.inputs.before_frame(False)
        self.assertEqual(app.emu.inputs.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(app.emu.inputs.state(0, 1, 0, IDS["B"]), 0)

    def test_disabling_controller_releases_game_and_sdl_device(self):
        app = self.ui()
        self.pad.buttons = {"A"}
        app.gamepad_tick()
        app.gamepad_enabled.set(False)
        app.toggle_gamepad()
        app.emu.inputs.before_frame(False)
        self.assertEqual(app.emu.inputs.state(0, 1, 0, IDS["B"]), 0)
        self.assertIsNone(self.reader.api)
        self.assertEqual(app.gamepad_status.get(), "Controller disabled")


if __name__ == "__main__":
    unittest.main()
