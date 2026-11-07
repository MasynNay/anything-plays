"""GameCube integrated software renderer tests; no ROM or GPU required."""
import ctypes as C
import gc
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from anything_plays.gamecube_software import (
    DolphinSoftwareOptions, RetroVariable, find_dolphin_core,
    gamecube_state, packaged_dolphin_system_directory,
)
from anything_plays.gba_emulator import CoreSession, Emulator
from anything_plays.libretro_input import InputBuffer


class DolphinInPanelTests(unittest.TestCase):
    def tearDown(self):
        # If a native ctypes ABI test has corrupted a pointer, force GC
        # directly after that exact case rather than failing much later in
        # an unrelated Pillow or N64 test. Keep faulthandler enabled in CI.
        gc.collect()

    def test_core_option_explicitly_chooses_cpu_video(self):
        options = DolphinSoftwareOptions()
        variable = RetroVariable()
        variable.key = b"dolphin_renderer"
        self.assertTrue(options.environment(15, C.addressof(variable)))
        self.assertEqual(variable.value, b"Software")
        self.assertFalse(options.environment(14, None))
        self.assertTrue(options.environment(52, C.addressof(C.c_uint())))
        self.assertFalse(options.environment(15, C.addressof(
            RetroVariable(b"unrecognized", None)
        )))

    def test_bundled_core_and_sys_are_required(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "cores"
            core = root / "dolphin_libretro.so"
            sys_dir = root / "dolphin-emu" / "Sys"
            core.parent.mkdir(parents=True)
            core.write_bytes(b"synthetic, not a real native library")
            with self.assertRaisesRegex(FileNotFoundError, "system data"):
                packaged_dolphin_system_directory(core)
            sys_dir.mkdir(parents=True)
            (sys_dir / "codehandler.bin").write_bytes(b"synthetic")
            self.assertEqual(packaged_dolphin_system_directory(core), root)

    def test_gamecube_libretro_core_is_found_without_installed_dolphin_app(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            path = folder / "dolphin_libretro.so"
            path.write_bytes(b"test")
            with patch("anything_plays.gamecube_software._library_extension",
                       return_value=".so"), patch(
                "anything_plays.gamecube_software._search_directories",
                return_value=(folder,),
            ), patch("anything_plays.gba_emulator.find_dolphin_core",
                     return_value=str(path)):
                self.assertEqual(find_dolphin_core(), str(path))
                emulator = Emulator()
                emulator.system = "gamecube"
                self.assertEqual(emulator.find_system_core(), str(path))

    def test_software_video_session_uses_sys_and_separate_save_directory(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            core = home / "cores" / "dolphin_libretro.so"
            core.parent.mkdir()
            core.write_bytes(b"test")
            sysdir = core.parent / "dolphin-emu" / "Sys"
            sysdir.mkdir(parents=True)
            (sysdir / "codehandler.bin").write_bytes(b"synthetic")
            rom = home / "owned-game.rvz"
            rom.write_bytes(b"synthetic")
            emulator = Emulator()
            with patch("pathlib.Path.home", return_value=home):
                session = CoreSession(emulator, "gamecube", rom, core)
            self.assertEqual(session.pixel_format, 1)
            self.assertIsInstance(session._software_options, DolphinSoftwareOptions)
            system_path = C.c_char_p()
            save_path = C.c_char_p()
            self.assertTrue(session.environment(9, C.addressof(system_path)))
            self.assertTrue(session.environment(31, C.addressof(save_path)))
            self.assertEqual(Path(system_path.value.decode()), core.parent)
            self.assertNotEqual(system_path.value, save_path.value)
            self.assertTrue(Path(save_path.value.decode()).is_dir())

    def test_analog_sticks_and_real_gamecube_buttons_work_as_retropad(self):
        state = gamecube_state({"A", "B", "Z", "L", "R", "Left", "C Up"})
        self.assertEqual(state[(1, 0, 8)], 1)  # A
        self.assertEqual(state[(1, 0, 0)], 1)  # B
        self.assertEqual(state[(1, 0, 11)], 1)  # Z
        self.assertEqual(state[(1, 0, 12)], 1)  # L2 trigger
        self.assertEqual(state[(1, 0, 13)], 1)  # R2 trigger
        self.assertLess(state[(5, 0, 0)], 0)   # Left stick X
        self.assertLess(state[(5, 1, 1)], 0)   # C-stick Y
        self.assertEqual(gamecube_state({"Left", "Right"}).get((5, 0, 0), 0), 0)

    def test_camera_and_keyboard_input_neutralize_safely_on_stop(self):
        inputs = InputBuffer()
        inputs.system = "gamecube"
        inputs.queue_press("A", 2)
        inputs.queue_press("C Right", 2)
        inputs.set_manual("Start", True)
        inputs.before_frame(armed=True)
        self.assertEqual(inputs.state(0, 1, 0, 8), 1)
        self.assertGreater(inputs.state(0, 5, 1, 0), 0)
        self.assertEqual(inputs.state(0, 1, 0, 3), 1)
        inputs.disarm()
        inputs.release_manual()
        inputs.before_frame(armed=False)
        self.assertEqual(inputs.state(0, 1, 0, 8), 0)
        self.assertEqual(inputs.state(0, 5, 1, 0), 0)


if __name__ == "__main__":
    unittest.main()
