"""Regression tests for concurrent UI Stop and 60 FPS emulator input."""
import threading
import unittest

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
