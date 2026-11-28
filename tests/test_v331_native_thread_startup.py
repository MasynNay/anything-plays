"""Native worker startup failure must leave the emulator retryable."""
import unittest
from unittest.mock import Mock, patch

from anything_plays.gba_emulator import Emulator


class NativeThreadStartupRecoveryTests(unittest.TestCase):
    def setUp(self):
        with patch("anything_plays.gba_emulator.find_core",
                   return_value="/synthetic/core.so"):
            self.emu = Emulator()
        self.emu.inputs = Mock()

    def assert_idle_failure(self):
        self.assertIsNone(self.emu.thread)
        self.assertFalse(self.emu.running)
        self.assertFalse(self.emu.launching)
        self.assertFalse(self.emu.armed)
        self.assertTrue(self.emu.stop_event.is_set())
        self.assertEqual(self.emu.rom, "/synthetic/game.gba")
        self.assertIn("Unable to start", self.emu.last_error)
        self.assertEqual(self.emu.error, self.emu.last_error)
        self.assertNotIn("PRIVATE", self.emu.error)
        self.assertIsNone(self.emu.frame)

    def test_thread_constructor_failure_rolls_back_launch(self):
        with patch("anything_plays.gba_emulator.threading.Thread",
                   side_effect=OSError("PRIVATE /home/user")):
            with self.assertRaisesRegex(RuntimeError, "Unable to start"):
                self.emu.start("/synthetic/game.gba")
        self.assert_idle_failure()

    def test_thread_start_failure_retires_dead_worker(self):
        worker = Mock()
        worker.is_alive.return_value = False
        worker.start.side_effect = RuntimeError("PRIVATE thread quota")
        with patch("anything_plays.gba_emulator.threading.Thread",
                   return_value=worker):
            with self.assertRaisesRegex(RuntimeError, "Unable to start"):
                self.emu.start("/synthetic/game.gba")
        self.assert_idle_failure()
        worker.join.assert_not_called()

    def test_retry_after_start_failure_can_launch_new_worker(self):
        failed = Mock()
        failed.is_alive.return_value = False
        failed.start.side_effect = RuntimeError("thread quota")
        good = Mock()
        with patch("anything_plays.gba_emulator.threading.Thread",
                   side_effect=[failed, good]):
            with self.assertRaises(RuntimeError):
                self.emu.start("/synthetic/game.gba")
            self.emu.start("/synthetic/game.gba")
        good.start.assert_called_once()
        self.assertIs(self.emu.thread, good)
        self.assertTrue(self.emu.launching)
        self.assertFalse(self.emu.stop_event.is_set())
        self.assertIsNone(self.emu.error)
        self.assertIsNone(self.emu.last_error)
        self.assertEqual(self.emu.session_generation, 2)

    def test_partially_started_worker_remains_tracked_until_exit(self):
        worker = Mock()
        worker.is_alive.return_value = True
        worker.start.side_effect = RuntimeError("failed after start")
        with patch("anything_plays.gba_emulator.threading.Thread",
                   return_value=worker) as make:
            with self.assertRaises(RuntimeError):
                self.emu.start("/synthetic/game.gba")
            self.assertIs(self.emu.thread, worker)
            self.assertTrue(self.emu.stop_event.is_set())
            with self.assertRaisesRegex(RuntimeError, "still shutting down"):
                self.emu.start("/synthetic/other.gba")
            make.assert_called_once()
        self.assertEqual(self.emu.rom, "/synthetic/game.gba")
        worker.is_alive.return_value = False
        self.assertTrue(self.emu.stop())
        self.assertIsNone(self.emu.thread)
        self.assertFalse(self.emu.launching)

    def test_failed_launch_retires_old_video_and_diagnostics(self):
        self.emu.frame = object()
        self.emu.frame_serial = 12
        self.emu._gamecube_last_performance = {"old": 1}
        with patch("anything_plays.gba_emulator.threading.Thread",
                   side_effect=MemoryError("PRIVATE")):
            with self.assertRaises(RuntimeError):
                self.emu.start("/synthetic/game.gba")
        self.assert_idle_failure()
        self.assertEqual(self.emu.frame_serial, 13)
        self.assertEqual(self.emu.session_generation, 1)
        self.assertIsNone(self.emu._gamecube_last_performance)

    def test_worker_launch_failure_releases_input(self):
        worker = Mock()
        worker.is_alive.return_value = False
        worker.start.side_effect = RuntimeError("start failed")
        with patch("anything_plays.gba_emulator.threading.Thread",
                   return_value=worker):
            with self.assertRaises(RuntimeError):
                self.emu.start("/synthetic/game.gba")
        self.assertGreaterEqual(self.emu.inputs.release_manual.call_count, 2)
        self.assertGreaterEqual(self.emu.inputs.release_gamepad.call_count, 2)
        self.assertGreaterEqual(self.emu.inputs.disarm.call_count, 2)

    def test_successful_start_preserves_normal_launch_state(self):
        worker = Mock()
        with patch("anything_plays.gba_emulator.threading.Thread",
                   return_value=worker) as make:
            self.emu.start("/synthetic/game.gba")
        worker.start.assert_called_once()
        self.assertEqual(make.call_args.kwargs["name"], "libretro")
        self.assertTrue(make.call_args.kwargs["daemon"])
        self.assertIs(self.emu.thread, worker)
        self.assertTrue(self.emu.launching)
        self.assertFalse(self.emu.running)
        self.assertFalse(self.emu.stop_event.is_set())


if __name__ == "__main__":
    unittest.main()
