"""Regression tests for concurrent UI Stop and 60 FPS emulator input."""
import threading
import unittest
from unittest.mock import patch

from anything_plays.libretro_input import InputBuffer, IDS


class InputSafetyTests(unittest.TestCase):
    def test_disarm_is_safe_while_worker_advances_frames(self):
        buffer = InputBuffer()
        errors = []

        def worker():
            try:
                for _ in range(1200):
                    buffer.before_frame(armed=True)
                    buffer.state(0, 1, 0, IDS["A"])
                    buffer.after_frame()
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=worker)
        thread.start()
        for _ in range(1200):
            buffer.queue_press("A", 2)
            buffer.disarm()
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive(), "Input worker stalled")
        self.assertEqual(errors, [])
        buffer.disarm()
        self.assertFalse(buffer.remaining)
        self.assertFalse(buffer.pressed)

    def test_n64_analog_mapping_is_bounded_per_frame(self):
        from anything_plays.libretro_input import desired_state
        buffer = InputBuffer()
        buffer.system = "n64"
        buffer.set_manual("Left", True)
        buffer.set_manual("C Up", True)
        with patch("anything_plays.libretro_input.desired_state",
                   wraps=desired_state) as calculate:
            buffer.before_frame(armed=False)
            self.assertEqual(calculate.call_count, 1)
            for _ in range(1000):
                self.assertLess(buffer.state(0, 5, 0, 0), 0)
                self.assertLess(buffer.state(0, 5, 1, 1), 0)
            self.assertEqual(calculate.call_count, 1)
            buffer.release_manual()
            buffer.before_frame(armed=False)
            self.assertEqual(calculate.call_count, 2)
        self.assertEqual(buffer.state(0, 5, 0, 0), 0)

    def test_manual_input_survives_camera_stop(self):
        buffer = InputBuffer()
        buffer.set_manual("A", True)
        buffer.disarm()
        buffer.before_frame(armed=False)
        self.assertEqual(buffer.state(0, 1, 0, IDS["A"]), 1)
        buffer.release_manual()
        buffer.before_frame(armed=False)
        self.assertEqual(buffer.state(0, 1, 0, IDS["A"]), 0)


if __name__ == "__main__":
    unittest.main()
