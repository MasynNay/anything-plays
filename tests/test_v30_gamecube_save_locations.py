"""GameCube native virtual memory-card location must survive updates."""
import ctypes as C
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.gba_emulator import CoreSession
from anything_plays.libretro_save import native_core_save_directory


class GameCubeNativeCardDirectoryTests(unittest.TestCase):
    def test_memory_cards_are_shared_between_games_but_not_inside_core_sys(self):
        with TemporaryDirectory() as tmp:
            data = Path(tmp) / "user-owned-data"
            with patch("anything_plays.libretro_save._user_save_directory",
                       return_value=data):
                rom_a = Path(tmp) / "roms" / "a.iso"
                rom_b = Path(tmp) / "roms" / "b.gcm"
                a = native_core_save_directory(rom_a, "gamecube")
                b = native_core_save_directory(rom_b, "gamecube")
                self.assertEqual(a, b)
                self.assertEqual(a, data / "native-core" / "gamecube")
                self.assertNotIn("dolphin-emu/Sys", str(a))
                self.assertNotIn("30-preview", str(a))

    def test_core_requests_native_gamecube_card_dir_and_read_only_sys_separately(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            sys_dir = root / "core" / "dolphin-emu"
            sys_dir.mkdir(parents=True)
            folder = C.create_string_buffer(os.fsencode(str(sys_dir)))
            with patch("anything_plays.libretro_save._user_save_directory",
                       return_value=root / "user-data"), patch.object(
                        CoreSession, "_make_system_directory", return_value=folder):
                session = CoreSession(None, "gamecube", root / "game.iso",
                                      str(root / "core" / "dolphin_libretro.so"))
                try:
                    native = C.c_char_p()
                    self.assertTrue(session.environment(
                        31, C.cast(C.pointer(native), C.c_void_p)))
                    self.assertEqual(
                        Path(os.fsdecode(native.value)),
                        root / "user-data" / "native-core" / "gamecube",
                    )
                    self.assertTrue(Path(os.fsdecode(native.value)).is_dir())
                    system = C.c_char_p()
                    self.assertTrue(session.environment(
                        9, C.cast(C.pointer(system), C.c_void_p)))
                    self.assertEqual(Path(os.fsdecode(system.value)), sys_dir)
                finally:
                    session.audio.close()


if __name__ == "__main__":
    unittest.main()
