"""3.3 camera input generation and classic pulse safety regressions.

All tests use synthetic controls; no native cores, webcam, or private paths.
"""
import threading
import unittest
from unittest.mock import patch

from anything_plays.gba_emulator import Emulator
from anything_plays.libretro_input import IDS, InputBuffer


class CameraGenerationSafetyTests(unittest.TestCase):
    @staticmethod
    def emulator():
        # Avoid any real core discovery or native ROM initialization.
        emulator = object.__new__(Emulator)
        emulator.inputs = InputBuffer()
        emulator.running = True
        emulator.armed = True
        return emulator

    def test_stop_invalidates_prior_held_buttons_and_both_pulse_ports(self):
        inputs = InputBuffer()
        original = inputs.camera_generation()
        inputs.set_camera_buttons(("A",), ("B",), generation=original)
        inputs.queue_press("X", 4, port=0, generation=original)
        inputs.queue_press("Y", 4, port=1, generation=original)
        inputs.disarm()
        # Simulate a delayed camera frame that finished tracking before Stop.
        inputs.set_camera_buttons(("A",), ("B",), generation=original)
        inputs.queue_press("X", 4, port=0, generation=original)
        inputs.queue_press("Y", 4, port=1, generation=original)
        self.assertTrue(inputs.commands.empty())
        inputs.before_frame(True)
        for port, name in ((0, "A"), (1, "B"), (0, "X"), (1, "Y")):
            self.assertEqual(inputs.state(port, 1, 0, IDS[name]), 0)
        fresh = inputs.camera_generation()
        self.assertGreater(fresh, original)
        inputs.set_camera_buttons(("A",), ("B",), generation=fresh)
        inputs.before_frame(True)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 1)

    def test_stop_during_facade_handoff_cannot_restore_old_controls(self):
        for kind in ("held", "pulse"):
            with self.subTest(kind=kind):
                emu = self.emulator()
                if kind == "held":
                    original = emu.inputs.set_camera_buttons
                    def late(*args, **kwargs):
                        emu.disarm()
                        original(*args, **kwargs)
                    with patch.object(emu.inputs, "set_camera_buttons", side_effect=late):
                        emu.set_camera_buttons(("A",), ("B",))
                else:
                    original = emu.inputs.queue_press
                    def late(*args, **kwargs):
                        emu.disarm()
                        original(*args, **kwargs)
                    with patch.object(emu.inputs, "queue_press", side_effect=late):
                        emu.press("A", frames=4, port=1)
                emu.inputs.before_frame(True)
                self.assertEqual(emu.inputs.state(0, 1, 0, IDS["A"]), 0)
                self.assertEqual(emu.inputs.state(1, 1, 0, IDS["B"]), 0)
                self.assertEqual(emu.inputs.state(1, 1, 0, IDS["A"]), 0)
                self.assertTrue(emu.inputs.commands.empty())

    def test_disarm_while_camera_builds_snapshot_drops_expired_result(self):
        inputs = InputBuffer()
        token = inputs.camera_generation()
        started = threading.Event()
        resume = threading.Event()
        original = inputs.id_for
        failures = []
        def gated(button):
            started.set()
            if not resume.wait(3):
                raise AssertionError("camera test barrier did not resume")
            return original(button)
        def produce():
            try:
                inputs.set_camera_buttons(("A",), ("B",), generation=token)
            except Exception as exc:
                failures.append(type(exc).__name__)
        with patch.object(inputs, "id_for", side_effect=gated):
            worker = threading.Thread(target=produce)
            worker.start()
            try:
                self.assertTrue(started.wait(3))
                inputs.disarm()
            finally:
                resume.set()
                worker.join(timeout=3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(inputs._camera_held, {0: set(), 1: set()})

    def test_invalid_classic_pulse_settings_do_not_break_manual_controls(self):
        inputs = InputBuffer()
        inputs.set_manual("B", True)
        for frames in (None, [], {}, object(), True, float("nan"),
                       float("inf"), float("-inf"), "bad", "1e9999"):
            with self.subTest(frames_type=type(frames).__name__):
                inputs.queue_press("A", frames)
        for port in (None, True, False, 2, -1, "1"):
            inputs.queue_press("A", 3, port=port)
        for label in (None, [], {}, "not-a-retropad-key"):
            inputs.queue_press(label, 3)
        self.assertTrue(inputs.commands.empty())
        inputs.before_frame(armed=True)
        self.assertEqual(inputs.state(0, 1, 0, IDS["B"]), 1)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 0)
        inputs.queue_press("A", "3")
        inputs.queue_press("B", 999, port=1)
        inputs.before_frame(armed=True)
        self.assertEqual(inputs.remaining[IDS["A"]], 3)
        self.assertEqual(inputs.remaining_p2[IDS["B"]], 60)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 1)
        inputs.disarm()
        inputs.before_frame(armed=False)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 0)
        self.assertEqual(inputs.state(0, 1, 0, IDS["B"]), 1)


if __name__ == "__main__":
    unittest.main()
