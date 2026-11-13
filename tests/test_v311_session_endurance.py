"""3.1.1: sustained virtual-time input/save recovery and bounded resources.

This advances 1,800 seconds of *simulated* 65ms controller polls. It never
runs for 30 real minutes and is NOT a real HID, webcam, ROM, audio, core or
physical-device endurance acceptance test. Separate Tk wall-clock soak runs
for minutes in CI and saves its own evidence.
"""
from __future__ import annotations

import ctypes
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from anything_plays.gamepad import GamepadReader
from anything_plays.libretro_input import IDS, InputBuffer
from anything_plays.libretro_save import SaveRAM


STEP_SECONDS = 0.065
VIRTUAL_SECONDS = 1800
TICKS = round(VIRTUAL_SECONDS / STEP_SECONDS)
NATIVE_BUTTON_A = "CONTROLLER_BUTTON_A"


class VirtualPad:
    def __init__(self):
        self.present = True
        self.pressed = False
        self.closed = 0

    def attached(self):
        return self.present

    def get_button(self, name):
        return self.present and self.pressed and name == NATIVE_BUTTON_A

    def get_axis(self, name):
        return 0

    def quit(self):
        self.present = False
        self.closed += 1


class VirtualSDL:
    def __init__(self):
        self.pad = VirtualPad()
        self.enumerations = 0

    def get_count(self):
        self.enumerations += 1
        return 1 if self.pad is not None else 0

    def is_controller(self, index):
        return index == 0 and self.pad is not None

    def Controller(self, index):
        return self.pad

    def name_forindex(self, index):
        return "Virtual controller · not physical hardware"

    def quit(self):
        return None


class SyntheticEnduranceTests(unittest.TestCase):
    def test_1800_seconds_of_virtual_hotplug_input_and_sram_checkpoints(self):
        virtual_now = [0.0]
        api = VirtualSDL()
        reader = GamepadReader(clock=lambda: virtual_now[0])
        reader.api = api
        pumps = [0]

        def pump():
            pumps[0] += 1

        reader.pygame = SimpleNamespace(
            event=SimpleNamespace(pump=pump, get=lambda: []),
            joystick=SimpleNamespace(quit=lambda: None),
            display=SimpleNamespace(quit=lambda: None),
        )
        reader._sdl_constant = lambda name: name
        buffer = InputBuffer()
        buffer.system = "gba"
        reconnects = 0
        polls_during_disconnect = 0
        samples_written = 0

        with tempfile.TemporaryDirectory(prefix="ap-311-virtual-soak-") as temp:
            data = ctypes.create_string_buffer(b"SEED0000", 8)
            sav = SaveRAM(Path(temp) / "synthetic-game.gba",
                          lambda kind: ctypes.addressof(data),
                          lambda kind: 8)
            self.assertTrue(sav.persist())
            samples_written += 1
            last_digest = hashlib.sha256(data.raw).digest()

            # About 27,700 snapshots: virtual 30-minute continuous session.
            # No real-time delays or native camera and gameplay emulation.
            for tick in range(TICKS):
                virtual_now[0] = tick * STEP_SECONDS
                # Every ~3 minutes, unplug the pad for 20 polling frames,
                # then reattach a fresh virtual handle.
                phase = tick % 2760
                if phase == 0 and tick:
                    if api.pad is not None:
                        api.pad.present = False
                    api.pad = None
                elif phase == 20 and tick >= 2760:
                    # Reconnect only after a planned detach, not at the
                    # start of the test where the first pad is still live.
                    api.pad = VirtualPad()
                    reconnects += 1
                if api.pad is not None:
                    api.pad.pressed = tick % 7 in (0, 1, 2)

                # Keyboard source must remain independent of any controller
                # disconnect, and camera pulses never survive disarming.
                manual_held = tick % 11 < 4
                buffer.set_manual("B", manual_held)
                armed = tick % 1000 < 700
                buffer.set_camera_buttons(("Up",) if armed and tick % 17 < 5 else ())
                held, _status = reader.poll("gba")
                buffer.set_gamepad_buttons(held)
                buffer.before_frame(armed)
                self.assertEqual(buffer.state(0, 1, 0, IDS["B"]),
                                 int(manual_held))
                self.assertEqual(buffer.state(0, 1, 0, IDS["A"]),
                                 int("A" in held))
                if not armed:
                    self.assertEqual(buffer.state(0, 1, 0, IDS["Up"]), 0)
                if api.pad is None:
                    polls_during_disconnect += 1
                    self.assertEqual(held, frozenset())
                    self.assertEqual(reader.physical_buttons, frozenset())
                self.assertLessEqual(buffer.commands.qsize(), 32)
                self.assertLessEqual(len(reader.physical_buttons), 22)
                self.assertLessEqual(len(buffer.pressed), 12)
                buffer.after_frame()

                if tick % 360 == 0:
                    data.raw = f"{tick:08d}".encode("ascii")
                    self.assertTrue(sav.persist())
                    samples_written += 1
                    last_digest = hashlib.sha256(data.raw).digest()
                    self.assertFalse(sav.persist(), "Unchanged SRAM rewritten")

            self.assertGreaterEqual(reconnects, 9)
            self.assertGreater(polls_during_disconnect, 0)
            self.assertEqual(pumps[0], TICKS)
            self.assertGreater(samples_written, 70)
            self.assertLessEqual(api.enumerations, 30,
                                 "Healthy device must not rescan every frame")
            self.assertEqual(hashlib.sha256(sav.path.read_bytes()).digest(),
                             last_digest)
            self.assertEqual(list(Path(temp).glob("*.tmp")), [])
            last_pad = api.pad
            reader.stop()
            if last_pad is not None:
                self.assertEqual(last_pad.closed, 1)
            self.assertIsNone(reader.api)
            self.assertIsNone(reader.controller)
            self.assertEqual(reader.physical_buttons, frozenset())
            self.assertEqual(reader._active_axes, frozenset())
            self.assertEqual(reader._active_triggers, frozenset())
            buffer.release_manual()
            buffer.release_gamepad()
            buffer.disarm()
            buffer.before_frame(False)
            self.assertEqual(buffer.state(0, 1, 0, IDS["A"]), 0)
            self.assertEqual(buffer.state(0, 1, 0, IDS["B"]), 0)
            self.assertEqual(buffer.state(0, 1, 0, IDS["Up"]), 0)

    def test_virtual_soak_scope_is_never_physical_hardware_evidence(self):
        # A source-level guard against claims that simulated 1,800 seconds
        # equals thirty minutes of actual installed app endurance.
        self.assertGreater(TICKS, 27_000)
        self.assertLess(TICKS, 28_000)
        self.assertEqual(round(TICKS * STEP_SECONDS), VIRTUAL_SECONDS)


if __name__ == "__main__":
    unittest.main()
