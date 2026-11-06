"""Dolphin pipe controller contract tests with synthetic game input."""
import os
from pathlib import Path
import stat
import sys
from tempfile import TemporaryDirectory
import unittest

from anything_plays.dolphin_pipe import (
    DolphinPipeController, dolphin_profile, gamecube_commands,
)
from anything_plays.external_emulators import command_for


@unittest.skipIf(sys.platform == "win32", "POSIX Dolphin input pipe")
class DolphinBridgeTests(unittest.TestCase):
    def test_saves_user_profile_only_in_test_directory(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            normal = root / "normal-dolphin"
            normal.mkdir()
            sentinel = normal / "GCPadNew.ini"
            sentinel.write_text("untouched")
            directory = root / "alpha-dolphin"
            fifo = dolphin_profile(directory)
            self.assertTrue(stat.S_ISFIFO(fifo.stat().st_mode))
            self.assertEqual(sentinel.read_text(), "untouched")
            pad = (directory / "Config" / "GCPadNew.ini").read_text()
            self.assertIn("Device = Pipe/0/anythingplays21", pad)
            self.assertIn("Buttons/A = `Button A`", pad)
            self.assertIn("Main Stick/Up = `Axis MAIN Y +`", pad)
            self.assertIn("SIDevice0 = 6",
                          (directory / "Config" / "Dolphin.ini").read_text())
            self.assertEqual(dolphin_profile(directory), fifo)

    def test_main_stick_and_buttons_generate_balanced_commands(self):
        initial = gamecube_commands({"A", "Left", "Up"}, set())
        self.assertIn("PRESS A", initial)
        self.assertIn("SET MAIN 0.00 1.00", initial)
        finished = gamecube_commands(set(), {"A", "Left", "Up"})
        self.assertIn("RELEASE A", finished)
        self.assertIn("SET MAIN 0.50 0.50", finished)
        c_pressed = gamecube_commands({"C Up", "C Right"}, set())
        self.assertIn("SET C 1.00 1.00", c_pressed)
        c_released = gamecube_commands(set(), {"C Up", "C Right"})
        self.assertIn("SET C 0.50 0.50", c_released)

    def test_transmit_button_pulses_through_real_fifo(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            now = [100.0]
            pad = DolphinPipeController(
                root / "dolphin", clock=lambda: now[0]
            )
            fd = os.open(pad.pipe, os.O_RDONLY | os.O_NONBLOCK)
            try:
                pad.press("A", frames=6)
                pad.flush()
                self.assertIn(b"PRESS A\n", os.read(fd, 1024))
                now[0] += 0.2
                pad.flush()
                self.assertIn(b"RELEASE A\n", os.read(fd, 1024))
            finally:
                pad.close()
                os.close(fd)

    def test_dolphin_launch_selects_test_profile_with_existing_rom(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            user = root / "gamecube-user"
            dolphin_profile(user)
            exe = root / "Dolphin"
            rom = root / "Game.rvz"
            exe.write_bytes(b"test")
            rom.write_bytes(b"test")
            args = command_for("gamecube", rom, executable=exe, dolphin_user=user)
            self.assertEqual(args[-1], "--exec=" + str(rom))
            self.assertIn("--user=" + str(user), args)


if __name__ == "__main__":
    unittest.main()
