"""End-to-end virtual aquarium and SDL gamepad coexistence regression.

No physical cameras, gamepads, ROMs or native cores are used. Unlike pure
InputBuffer tests, real OpenCV color contours pass through CameraMixin's
actual draw_camera controller routing, GamepadReader's SDL API polling,
GamepadMixin's focus/disconnect policy, and native Libretro input callbacks.
"""
from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

import cv2
import numpy as np

from anything_plays.gamepad import GamepadReader
from anything_plays.libretro_input import InputBuffer, TWO_PLAYER_SYSTEMS
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM
from anything_plays.ui_camera import CameraMixin
from anything_plays.ui_gamepad import GamepadMixin
from anything_plays.ui_gameplay import GameplayMixin


RGB_PRIMARY = (40, 230, 85)
RGB_SECONDARY = (235, 50, 190)
BGR_PRIMARY = RGB_PRIMARY[::-1]
BGR_SECONDARY = RGB_SECONDARY[::-1]


class Variable:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class VirtualEvents:
    def __init__(self):
        self.pumps = 0
        self.drains = 0

    def pump(self):
        self.pumps += 1

    def get(self):
        self.drains += 1
        return []


class VirtualSubsystem:
    def init(self):
        pass

    def quit(self):
        pass


class VirtualPygame:
    def __init__(self):
        self.display = VirtualSubsystem()
        self.joystick = VirtualSubsystem()
        self.event = VirtualEvents()


class VirtualPhysicalPad:
    def __init__(self):
        self.buttons = set()
        self.axes = {}
        self.connected = True
        self.closed = False

    def attached(self):
        return self.connected and not self.closed

    def get_button(self, code):
        if not self.connected:
            raise OSError("Virtual gamepad unplugged")
        return code in self.buttons

    def get_axis(self, code):
        if not self.connected:
            raise OSError("Virtual gamepad unplugged")
        return self.axes.get(code, 0)

    def quit(self):
        self.closed = True


class VirtualSDL:
    def __init__(self, devices):
        self.devices = devices
        names = ("DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT",
                 "A", "B", "X", "Y", "BACK", "START",
                 "LEFTSHOULDER", "RIGHTSHOULDER")
        for name in names:
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
        return "Virtual SDL controller"


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
    def __init__(self, system="snes"):
        self.inputs = InputBuffer()
        self.inputs.system = system
        self.running = True
        self.armed = True

    def set_camera_buttons(self, p1=(), p2=()):
        if self.running and self.armed:
            self.inputs.set_camera_buttons(p1, p2)

    def set_gamepad_buttons(self, buttons):
        self.inputs.set_gamepad_buttons(buttons)

    def release_gamepad(self):
        self.inputs.release_gamepad()

    def set_manual(self, button, held):
        self.inputs.set_manual(button, held)

    def release_manual(self):
        self.inputs.release_manual()

    def press(self, button, frames=8, port=0):
        if self.armed and self.running:
            self.inputs.queue_press(button, frames, port=port)

    def disarm(self):
        self.armed = False
        self.inputs.disarm()

    def frame(self):
        self.inputs.before_frame(self.armed)

    def held(self, button, port=0):
        identity = self.inputs.id_for(button)
        if identity is None:
            raise AssertionError("Unknown console button: " + str(button))
        return bool(self.inputs.state(port, 1, 0, identity))


class VirtualAquarium(CameraMixin, GamepadMixin, GameplayMixin):
    """Minimal Tk-like context, invoking the real camera and gamepad methods."""

    def __init__(self, reader, system="snes"):
        self._closing = False
        self.root = VirtualRoot()
        self.emu = VirtualEmulator(system)
        self.system_key = Variable(system)
        self._gamepad = reader
        self._gamepad_bindings = {}
        self.gamepad_enabled = Variable(True)
        self.gamepad_status = Variable("Controller enabled")
        self.gamepad_live_input = Variable("")
        self.action = Variable("")
        self.status = Variable("")
        self.armed = True
        self.external_input = None
        self.tolerance = Variable(18)
        self.min_area = Variable(55)
        self.multi_fish_enabled = Variable(False)
        self.color2_enabled = Variable(True)
        self.color2_player = Variable("Player 2")
        self.camera_input_mode = Variable("Held while visible")
        self.hold_frames = Variable(4)
        self.cooldown = Variable(100)
        self.shuffle_enabled = Variable(False)
        self._shuffle_latched = False
        self._last_camera_pulses = {}
        self.cfg = {
            "rgb": list(RGB_PRIMARY),
            "rgb2": list(RGB_SECONDARY),
            "zones": {
                "PrimaryZone": [0, 0, 0.5, 1.0],
                "SecondaryZone": [0.5, 0, 1.0, 1.0],
            },
        }
        self.mapping_vars = {
            "PrimaryZone": Variable("A"),
            "SecondaryZone": Variable("B"),
        }
        self.frame = None
        self.cap = None
        self.reference_image = False
        self.camera_photo = None
        self.refresh_controller_artwork = lambda: None
        self.save_preferences = lambda: None
        self.uses_embedded_emulator = lambda: True
        self.render_zones = lambda frame, active: frame
        self.geometry = lambda: None

    def set_pixels(self, *, primary=(), secondary=()):
        picture = np.zeros((128, 192, 3), dtype=np.uint8)
        for point in primary:
            cv2.circle(picture, point, 13, BGR_PRIMARY, -1)
        for point in secondary:
            cv2.circle(picture, point, 13, BGR_SECONDARY, -1)
        self.frame = picture

    def one_frame(self):
        self.draw_camera()
        self.gamepad_tick()
        self.emu.frame()


class PixelAndControllerCoexistenceTests(TestCase):
    def setUp(self):
        self.pad = VirtualPhysicalPad()
        self.devices = [self.pad]
        self.api = VirtualSDL(self.devices)
        self.pygame = VirtualPygame()
        self.reader = GamepadReader(
            clock=lambda: 100, loader=lambda: self.pygame
        )
        self.module_patch = patch(
            "anything_plays.gamepad.importlib.import_module",
            return_value=self.api,
        )
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        self.reader.start()
        self.addCleanup(self.reader.stop)
        self.app = VirtualAquarium(self.reader)

    def test_two_real_color_contours_plus_gamepad_and_keyboard_same_frame(self):
        app = self.app
        self.pad.buttons = {"B"}
        app.emu.set_manual("Start", True)
        app.set_pixels(primary=[(45, 60)], secondary=[(145, 60)])
        app.one_frame()
        self.assertTrue(app.emu.held("A", 0), "primary camera object")
        self.assertTrue(app.emu.held("B", 0), "physical SDL controller")
        self.assertTrue(app.emu.held("Start", 0), "keyboard")
        self.assertTrue(app.emu.held("B", 1), "secondary camera object")
        self.assertFalse(app.emu.held("A", 1))
        self.assertIn("P2: B", app.action.get())

        app.set_pixels()
        app.one_frame()
        self.assertFalse(app.emu.held("A", 0))
        self.assertFalse(app.emu.held("B", 1))
        self.assertTrue(app.emu.held("B", 0))
        self.assertTrue(app.emu.held("Start", 0))

    def test_overlapping_camera_and_gamepad_hold_releases_independently(self):
        app = self.app
        self.pad.buttons = {"A"}
        app.color2_enabled.set(False)
        app.set_pixels(primary=[(44, 56)])
        app.one_frame()
        self.assertTrue(app.emu.held("A"))
        app.set_pixels()
        app.one_frame()
        self.assertTrue(app.emu.held("A"), "SDL should retain its own hold")
        app.emu.set_manual("A", True)
        self.pad.connected = False
        self.devices.clear()
        app.one_frame()
        self.assertTrue(app.emu.held("A"), "keyboard remains after unplug")
        self.assertFalse(self.reader.physical_buttons)
        app.emu.release_manual()
        app.emu.frame()
        self.assertFalse(app.emu.held("A"))

    def test_focus_loss_drops_gamepad_not_armed_camera_or_player_two(self):
        app = self.app
        self.pad.buttons = {"A"}
        app.set_pixels(primary=[(44, 56)], secondary=[(144, 60)])
        app.one_frame()
        app.root.focus = None
        app.one_frame()
        self.assertTrue(app.emu.held("A"), "camera should remain armed")
        self.assertTrue(app.emu.held("B", 1))
        self.assertFalse(app.emu.inputs.gamepad_buttons)
        app.set_pixels()
        app.one_frame()
        self.assertFalse(app.emu.held("A"))
        self.assertFalse(app.emu.held("B", 1))
        app.root.focus = object()
        app.one_frame()
        self.assertTrue(app.emu.held("A"), "SDL resumes after focus returns")

    def test_camera_stop_does_not_release_keyboard_or_controller(self):
        app = self.app
        self.pad.buttons = {"B"}
        app.emu.set_manual("Start", True)
        app.set_pixels(primary=[(44, 56)], secondary=[(144, 60)])
        app.one_frame()
        app.stop_controls()
        app.emu.frame()
        self.assertFalse(app.emu.held("A"))
        self.assertFalse(app.emu.held("B", 1))
        self.assertTrue(app.emu.held("B"))
        self.assertTrue(app.emu.held("Start"))
        self.assertFalse(app.armed)
        self.assertEqual(app.emu.inputs.commands.qsize(), 0)

    def test_rescan_drops_only_controller_while_both_camera_ports_remain(self):
        app = self.app
        self.pad.buttons = {"START"}
        app.set_pixels(primary=[(44, 56)], secondary=[(144, 60)])
        app.one_frame()
        self.assertTrue(app.emu.held("Start"))
        app.refresh_gamepad()
        app.emu.frame()
        self.assertFalse(app.emu.held("Start"))
        self.assertTrue(app.emu.held("A"))
        self.assertTrue(app.emu.held("B", 1))
        self.assertFalse(self.reader.physical_buttons)

    def test_multi_target_color_tracking_does_not_drop_controller_state(self):
        app = self.app
        app.color2_enabled.set(False)
        app.multi_fish_enabled.set(True)
        self.pad.buttons = {"START"}
        app.set_pixels(primary=[(44, 60), (145, 60)])
        app.one_frame()
        self.assertTrue(app.emu.held("A"))
        self.assertTrue(app.emu.held("B"))
        self.assertTrue(app.emu.held("Start"))
        self.assertIn("Primary objects: 2", app.action.get())

    def test_pulse_camera_queue_expires_but_controller_remains(self):
        app = self.app
        app.color2_enabled.set(False)
        app.camera_input_mode.set("Pulse (classic)")
        self.pad.buttons = {"B"}
        app.set_pixels(primary=[(44, 60)])
        app.one_frame()
        self.assertTrue(app.emu.held("A"))
        self.assertTrue(app.emu.held("B"))
        app.set_pixels()
        for _ in range(7):
            app.one_frame()
            app.emu.inputs.after_frame()
        app.emu.frame()
        self.assertFalse(app.emu.held("A"))
        self.assertTrue(app.emu.held("B"))
        self.assertEqual(app.emu.inputs.commands.qsize(), 0)

    def test_camera_and_gamepad_work_for_all_eighteen_system_profiles(self):
        app = self.app
        self.pad.buttons = {"START"}
        app.color2_enabled.set(False)
        app.set_pixels(primary=[(44, 60)])
        self.assertEqual(len(BUTTONS_BY_SYSTEM), 18)
        for system in BUTTONS_BY_SYSTEM:
            with self.subTest(system=system):
                app.system_key.set(system)
                app.emu.inputs.system = system
                app.emu.inputs.disarm()
                app.one_frame()
                self.assertTrue(app.emu.held("A"),
                                "primary color zone was not delivered")
                self.assertTrue(app.emu.held("Start"),
                                "gamepad input was not delivered")
                self.assertEqual(app.emu.inputs.commands.qsize(), 0)

    def test_thousand_camera_and_controller_frames_remain_bounded(self):
        app = self.app
        app.color2_enabled.set(False)
        app.multi_fish_enabled.set(True)
        for i in range(1000):
            self.pad.buttons = {"A"} if i % 2 else {"START"}
            app.set_pixels(primary=[(44, 60)] if i % 3 else [(145, 60)])
            app.one_frame()
            self.assertEqual(app.emu.held("A"),
                             i % 3 != 0 or i % 2 == 1)
            self.assertEqual(app.emu.held("B"), i % 3 == 0)
            self.assertEqual(app.emu.inputs.commands.qsize(), 0)
            app.emu.inputs.after_frame()
        self.assertEqual(self.pygame.event.pumps, 1000)
        self.assertEqual(self.pygame.event.drains, 1000)
        self.assertEqual(len(app.root.jobs), 1000)
        self.assertLessEqual(len(app.emu.inputs.gamepad_buttons), 1)

    def test_unsupported_second_player_rejected_without_silencing_controller(self):
        app = self.app
        self.pad.buttons = {"A"}
        app.system_key.set("gba")
        app.emu.inputs.system = "gba"
        app.set_pixels(secondary=[(145, 60)])
        app.one_frame()
        self.assertTrue(app.emu.held("A"))
        self.assertFalse(app.emu.held("B", 1))
        self.assertIn("Secondary object cannot use Player 2", app.action.get())


if __name__ == "__main__":
    import unittest
    unittest.main()
