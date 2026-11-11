"""3.1 gamepad input contracts: mapping, hotplug and keyboard isolation.

Synthetic gamepad events and actual SDL initialization are tested in CI on
Linux, Windows and both Mac architectures. Physical HID/USB/Bluetooth testing
remains a separate release gate.
"""
import ast
import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

from anything_plays.gamepad import (
    AXES, BUTTON_CONST, DEADZONE, DISABLED, SOURCES,
    STICK_RELEASE_DEADZONE, TRIGGER_THRESHOLD, TRIGGER_RELEASE_THRESHOLD,
    GamepadReader, default_bindings, mapped_buttons, normalize_bindings,
)
from anything_plays.libretro_input import IDS, InputBuffer


class MappingTests(unittest.TestCase):
    def test_supported_consoles_have_only_valid_button_targets(self):
        from anything_plays.system_profiles import BUTTONS_BY_SYSTEM
        for system, buttons in BUTTONS_BY_SYSTEM.items():
            with self.subTest(system=system):
                self.assertTrue(set(default_bindings(system).values()) <= set(buttons))

    def test_dpad_and_left_stick_press_the_same_direction(self):
        self.assertEqual(mapped_buttons("gba", {"DPAD_UP", "LEFT_STICK_UP"}), {"Up"})
        self.assertEqual(mapped_buttons("snes", {"A", "B", "X", "Y"}),
                         {"A", "B", "X", "Y"})

    def test_3d_camera_stick_and_trigger_defaults(self):
        self.assertEqual(
            mapped_buttons("n64", {"RIGHT_STICK_UP", "LEFT_TRIGGER"}),
            {"C Up", "Z"},
        )
        self.assertEqual(
            mapped_buttons("gamecube", {"RIGHT_STICK_RIGHT", "RIGHT_TRIGGER"}),
            {"C Right", "R"},
        )

    def test_genesis_buttons_use_native_console_names(self):
        self.assertEqual(mapped_buttons("genesis", {"X", "RIGHT_SHOULDER", "BACK"}),
                         {"C", "Z", "Mode"})

    def test_per_console_mappings_and_untrusted_saved_data(self):
        custom = {"A": "B", "B": DISABLED, "WRONG": "Z", "X": 999}
        normalized = normalize_bindings("gba", custom)
        self.assertEqual(normalized["A"], "B")
        self.assertEqual(normalized["B"], DISABLED)
        self.assertNotIn("WRONG", normalized)
        self.assertEqual(mapped_buttons("gba", {"A", "B"}, custom), {"B"})
        self.assertEqual(mapped_buttons("snes", {"B"}, custom), set())
        self.assertEqual(normalize_bindings("gba", []), default_bindings("gba"))


class InputIsolationTests(unittest.TestCase):
    def test_disarmed_camera_does_not_clear_gamepad(self):
        buffer = InputBuffer()
        buffer.set_gamepad_buttons({"A"})
        buffer.before_frame(False)
        self.assertEqual(buffer.state(0, 1, 0, IDS["A"]), 1)
        buffer.release_gamepad()
        buffer.before_frame(False)
        self.assertEqual(buffer.state(0, 1, 0, IDS["A"]), 0)

    def test_releasing_one_input_does_not_release_the_other(self):
        buffer = InputBuffer()
        buffer.set_manual("A", True)
        buffer.set_gamepad_buttons({"A", "B"})
        buffer.release_gamepad()
        buffer.before_frame(False)
        self.assertEqual(buffer.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(buffer.state(0, 1, 0, IDS["B"]), 0)
        buffer.set_gamepad_buttons({"B"})
        buffer.release_manual()
        buffer.before_frame(False)
        self.assertEqual(buffer.state(0, 1, 0, IDS["A"]), 0)
        self.assertEqual(buffer.state(0, 1, 0, IDS["B"]), 1)

    def test_invalid_buttons_and_stale_snapshot_clear(self):
        buffer = InputBuffer()
        buffer.set_gamepad_buttons({"A", "not-a-button"})
        buffer.before_frame(False)
        self.assertEqual(buffer.state(0, 1, 0, IDS["A"]), 1)
        buffer.set_gamepad_buttons(set())
        buffer.before_frame(False)
        self.assertEqual(buffer.state(0, 1, 0, IDS["A"]), 0)


class FakePad:
    def __init__(self):
        self.connected = True
        self.buttons = set()
        self.axes = {}
        self.closed = False

    def attached(self):
        return self.connected

    def get_button(self, code):
        return code in self.buttons

    def get_axis(self, code):
        return self.axes.get(code, 0)

    def quit(self):
        self.closed = True


class FakeControllerModule:
    def __init__(self, pad):
        self.pad = pad
        self.count = 1
        self.stopped = False
        for code in BUTTON_CONST.values():
            setattr(self, "CONTROLLER_BUTTON_" + code, code)
        for axis, _ in AXES.values():
            setattr(self, "CONTROLLER_AXIS_" + axis, axis)
        self.CONTROLLER_AXIS_TRIGGERLEFT = "TRIGGERLEFT"
        self.CONTROLLER_AXIS_TRIGGERRIGHT = "TRIGGERRIGHT"

    def init(self):
        pass

    def quit(self):
        self.stopped = True

    def get_count(self):
        return self.count

    def is_controller(self, index):
        return index < self.count

    def Controller(self, index):
        return self.pad

    def name_forindex(self, index):
        return "Test Xbox controller"


class Subsystem:
    def init(self):
        pass

    def quit(self):
        pass


class FakeEvents:
    def __init__(self):
        self.pumps = 0
        self.drains = 0

    def pump(self):
        self.pumps += 1

    def get(self):
        self.drains += 1
        return []


class FakePygame:
    def __init__(self):
        self.display = Subsystem()
        self.joystick = Subsystem()
        self.event = FakeEvents()


class GamepadLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.pad = FakePad()
        self.api = FakeControllerModule(self.pad)
        self.pg = FakePygame()
        self.clock = 0.0
        self.reader = GamepadReader(clock=lambda: self.clock,
                                    loader=lambda: self.pg)
        self.importer = patch("anything_plays.gamepad.importlib.import_module",
                              return_value=self.api)
        self.importer.start()
        self.addCleanup(self.importer.stop)

    def tearDown(self):
        self.reader.stop()

    def test_no_sdl_initialization_until_player_enables_gamepad(self):
        self.assertIsNone(self.reader.api)
        self.assertEqual(self.reader.poll("gba")[0], frozenset())
        self.reader.start()
        self.assertIs(self.reader.api, self.api)

    def test_buttons_sticks_and_triggers_are_normalized(self):
        self.reader.start()
        self.pad.buttons = {"A", "DPAD_LEFT"}
        self.pad.axes = {"LEFTX": DEADZONE + 400,
                         "RIGHTY": DEADZONE + 400,
                         "TRIGGERLEFT": 30000}
        buttons, name = self.reader.poll("n64")
        self.assertEqual(buttons, {"A", "Left", "Right", "C Down", "Z"})
        self.assertIn("Test Xbox", name)
        self.assertEqual(self.pg.event.pumps, 1)
        self.assertEqual(self.pg.event.drains, 1)

    def test_unplug_returns_no_buttons_and_does_not_keep_last_input(self):
        self.reader.start()
        self.pad.buttons = {"A"}
        self.assertEqual(self.reader.poll("gba")[0], {"A"})
        self.pad.connected = False
        self.api.count = 0
        buttons, status = self.reader.poll("gba")
        self.assertFalse(buttons)
        self.assertIn("No compatible", status)
        self.assertTrue(self.pad.closed)
        self.clock = 3.0
        self.assertFalse(self.reader.poll("gba")[0])

    def test_stick_hysteresis_keeps_buttons_stable_near_threshold(self):
        self.reader.start()
        self.pad.axes["LEFTX"] = DEADZONE + 10
        self.assertEqual(self.reader.poll("gba")[0], {"Right"})
        # The stick has already crossed the press threshold. Mild drift
        # back toward center must not stutter through repeated releases.
        middle = (DEADZONE + STICK_RELEASE_DEADZONE) // 2
        for value in (DEADZONE - 1, middle, STICK_RELEASE_DEADZONE):
            self.pad.axes["LEFTX"] = value
            self.assertEqual(self.reader.poll("gba")[0], {"Right"})
        self.pad.axes["LEFTX"] = STICK_RELEASE_DEADZONE - 1
        self.assertEqual(self.reader.poll("gba")[0], frozenset())
        self.pad.axes["LEFTX"] = middle
        self.assertEqual(self.reader.poll("gba")[0], frozenset())
        self.pad.axes["LEFTX"] = DEADZONE
        self.assertEqual(self.reader.poll("gba")[0], {"Right"})

    def test_opposing_stick_directions_share_one_read_per_axis(self):
        self.reader.start()
        calls = []
        original = self.pad.get_axis

        def unstable_driver(code):
            calls.append(code)
            if code == "LEFTX":
                return (DEADZONE + 1 if calls.count(code) == 1
                        else -(DEADZONE + 1))
            return original(code)

        self.pad.get_axis = unstable_driver
        held, _status = self.reader.poll("gba")
        self.assertEqual(held, {"Right"})
        self.assertEqual(calls.count("LEFTX"), 1)
        self.assertEqual(calls.count("LEFTY"), 1)
        self.assertEqual(calls.count("RIGHTX"), 1)
        self.assertEqual(calls.count("RIGHTY"), 1)

    def test_trigger_hysteresis_is_independent_for_both_sides(self):
        self.reader.start()
        self.pad.axes = {
            "TRIGGERLEFT": TRIGGER_THRESHOLD + 1,
            "TRIGGERRIGHT": TRIGGER_RELEASE_THRESHOLD + 100,
        }
        self.assertEqual(self.reader.poll("gba")[0], {"L"})
        middle = (TRIGGER_THRESHOLD + TRIGGER_RELEASE_THRESHOLD) // 2
        self.pad.axes["TRIGGERLEFT"] = middle
        self.assertEqual(self.reader.poll("gba")[0], {"L"})
        self.pad.axes["TRIGGERLEFT"] = TRIGGER_RELEASE_THRESHOLD - 1
        self.assertEqual(self.reader.poll("gba")[0], frozenset())
        self.pad.axes["TRIGGERLEFT"] = middle
        self.assertEqual(self.reader.poll("gba")[0], frozenset())

    def test_reconnect_clears_stick_and_trigger_hysteresis_latches(self):
        self.reader.start()
        self.pad.axes = {
            "LEFTX": DEADZONE + 1,
            "TRIGGERLEFT": TRIGGER_THRESHOLD + 1,
        }
        self.assertEqual(self.reader.poll("gba")[0], {"Right", "L"})
        self.pad.connected = False
        self.api.count = 0
        self.assertFalse(self.reader.poll("gba")[0])
        self.assertFalse(self.reader._active_axes)
        self.assertFalse(self.reader._active_triggers)

        self.api.pad = FakePad()
        self.api.pad.axes = {
            "LEFTX": (DEADZONE + STICK_RELEASE_DEADZONE) // 2,
            "TRIGGERLEFT": (TRIGGER_THRESHOLD + TRIGGER_RELEASE_THRESHOLD) // 2,
        }
        self.api.count = 1
        self.clock = 3.0
        # The next controller must cross *press* thresholds afresh.
        self.assertEqual(self.reader.poll("gba")[0], frozenset())
        self.reader.refresh()
        self.assertFalse(self.reader._active_axes)
        self.assertFalse(self.reader._active_triggers)

    def test_quit_releases_controller_subsystems(self):
        self.reader.start()
        self.reader.poll("gba")
        self.reader.stop()
        self.assertTrue(self.pad.closed)
        self.assertTrue(self.api.stopped)
        self.assertIsNone(self.reader.api)


    def test_transient_sdl_enumeration_error_retries_without_disabling(self):
        self.reader.start()
        self.pad.buttons = {"A"}
        original_count = self.api.get_count
        attempts = []

        def flaky_count():
            attempts.append(self.clock)
            if len(attempts) == 1:
                raise OSError("controller unplugged while SDL enumerated")
            return original_count()

        self.api.get_count = flaky_count
        held, message = self.reader.poll("gba")
        self.assertEqual(held, frozenset())
        self.assertIn("Retrying", message)
        self.assertIsNotNone(self.reader.api)
        self.assertEqual(self.reader.physical_buttons, frozenset())

        self.clock = 0.5
        held, _ = self.reader.poll("gba")
        self.assertEqual(held, frozenset())
        self.assertEqual(len(attempts), 1, "Backoff prevents a 65 ms error loop")

        self.clock = 2.0
        held, message = self.reader.poll("gba")
        self.assertEqual(held, {"A"})
        self.assertIn("connected", message)
        self.assertEqual(len(attempts), 2)

    def test_sdl_event_pump_failure_clears_held_input_then_recovers(self):
        self.reader.start()
        self.pad.buttons = {"A"}
        self.assertEqual(self.reader.poll("gba")[0], {"A"})
        previous_pump = self.pg.event.pump

        def failed_pump():
            raise RuntimeError("temporary SDL event subsystem failure")

        self.pg.event.pump = failed_pump
        self.clock = 1.0
        held, message = self.reader.poll("gba")
        self.assertEqual(held, frozenset())
        self.assertEqual(self.reader.physical_buttons, frozenset())
        self.assertIn("Retrying", message)
        self.assertTrue(self.pad.closed)

        self.clock = 1.2
        self.assertEqual(self.reader.poll("gba")[0], frozenset())
        self.pg.event.pump = previous_pump
        self.api.pad = FakePad()
        self.api.pad.buttons = {"B"}
        self.clock = 3.0
        held, message = self.reader.poll("gba")
        self.assertEqual(held, {"B"})
        self.assertIn("connected", message)

    def test_lost_friendly_name_during_hotplug_does_not_drop_pad(self):
        self.reader.start()

        def lost_name(index):
            raise OSError("name vanished during hotplug")

        self.api.name_forindex = lost_name
        self.pad.buttons = {"A"}
        held, status = self.reader.poll("gba")
        self.assertEqual(held, {"A"})
        self.assertEqual(status, "Gamepad connected")

    def test_refresh_resets_scan_error_backoff_immediately(self):
        self.reader.start()
        self.api.get_count = lambda: (_ for _ in ()).throw(OSError("scan"))
        self.assertIn("Retrying", self.reader.poll("gba")[1])
        self.assertGreater(self.reader.retry_after, 0)
        self.reader.refresh()
        self.assertEqual(self.reader.retry_after, float("-inf"))
        self.api.get_count = lambda: 1
        self.assertEqual(self.reader.poll("gba")[1], "Test Xbox controller connected")


    def test_shutdown_attempts_all_sdl_subsystems_even_when_quit_fails(self):
        self.reader.start()
        self.reader.poll("gba")
        called = []

        def bad_controller_quit():
            called.append("controller")
            raise RuntimeError("USB device gone")

        def bad_joystick_quit():
            called.append("joystick")
            raise OSError("joystick already removed")

        def good_display_quit():
            called.append("display")

        self.api.quit = bad_controller_quit
        self.pg.joystick.quit = bad_joystick_quit
        self.pg.display.quit = good_display_quit
        self.reader.stop()
        self.assertEqual(called, ["controller", "joystick", "display"])
        self.assertIsNone(self.reader.api)
        self.assertIsNone(self.reader.pygame)
        self.assertIsNone(self.reader.controller)


class SDLBackendSmokeTests(unittest.TestCase):
    def test_real_sdl_controller_api_without_physical_hardware(self):
        """Exercise actual pygame-ce initialization and poll in dummy video mode."""
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy"}):
            reader = GamepadReader()
            try:
                reader.start()
                self.assertIsNotNone(reader.api)
                self.assertIsInstance(reader._sdl_constant("CONTROLLER_BUTTON_A"), int)
                self.assertIsInstance(reader._sdl_constant("CONTROLLER_AXIS_LEFTX"), int)
                held, status = reader.poll("gba")
                self.assertIsInstance(held, frozenset)
                self.assertIsInstance(status, str)
            finally:
                reader.stop()


class WiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def test_ui_and_packaging_syntax(self):
        paths = ["anything_plays/gamepad.py", "anything_plays/ui_gamepad.py",
                 "app.py", "anything_plays/gba_emulator.py",
                 "anything_plays/libretro_input.py", "anything_plays/ui_shortcuts.py"]
        for path in paths:
            with self.subTest(file=path):
                ast.parse((self.root / path).read_text("utf-8"))

    def test_all_platform_packages_include_sdl(self):
        for script in ("packaging/build_windows.bat",
                       "packaging/build_macos_dmg.sh",
                       "packaging/build_linux_deb.sh"):
            with self.subTest(script=script):
                self.assertIn("--collect-all pygame",
                              (self.root / script).read_text("utf-8"))
        self.assertIn("pygame-ce", (self.root / "requirements.txt").read_text("utf-8"))
        self.assertIn("pygame-ce==2.5.8",
                      (self.root / "requirements-build.txt").read_text("utf-8"))

    def test_callback_cleanup_and_safe_persistence(self):
        source = (self.root / "app.py").read_text("utf-8")
        self.assertIn("self._gamepad_tick_job = root.after", source)
        self.assertIn("cleanup(\"gamepad\", self.close_gamepad)", source)
        self.assertIn("self.initialize_gamepad_preferences(preferences)", source)
        ui = (self.root / "anything_plays/ui_gamepad.py").read_text("utf-8")
        self.assertIn("if self._gamepad.api is None:", ui)
        self.assertIn("self.root.focus_get() is None", ui)
        self.assertIn("self.emu.release_gamepad()", ui)
        self.assertIn("self._gamepad.stop()", ui)
        prefs = (self.root / "anything_plays/ui_profiles.py").read_text("utf-8")
        self.assertIn("prefs['gamepad_bindings']", prefs)


if __name__ == "__main__":
    unittest.main()
