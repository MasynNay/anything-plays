"""Neo Geo Pocket cartridge flash must not collide or need writable ROMs."""

import ctypes as C
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.gba_emulator import CoreSession
from anything_plays.libretro_save import native_core_save_directory


class NeoGeoPocketNativeSavePaths(unittest.TestCase):
    def test_two_same_named_roms_have_distinct_native_flash_directories(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            left = root / "cartridges" / "a" / "Same.ngc"
            right = root / "cartridges" / "b" / "Same.ngc"
            left.parent.mkdir(parents=True)
            right.parent.mkdir(parents=True)
            left.write_bytes(b"a")
            right.write_bytes(b"b")
            with patch("anything_plays.libretro_save._user_save_directory",
                       return_value=root / "user-data"):
                left_folder = native_core_save_directory(left, "ngpc")
                right_folder = native_core_save_directory(right, "ngpc")
                self.assertNotEqual(left_folder, right_folder)
                self.assertEqual(left_folder, native_core_save_directory(left, "ngpc"))
                self.assertTrue(str(left_folder).startswith(str(root / "user-data")))
                self.assertNotIn(str(left.parent), str(left_folder))
                self.assertIn("neo-geo-pocket", str(left_folder))

    def test_ngp_and_ngpc_environment_returns_writable_per_rom_save_directory(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            system_folder = root / "system"
            system_folder.mkdir()
            for system, extension in (("ngp", ".ngp"), ("ngpc", ".ngc")):
                with self.subTest(system=system):
                    rom = root / ("my-test" + extension)
                    rom.write_bytes(b"small test ROM")
                    system_buffer = C.create_string_buffer(os.fsencode(str(system_folder)))
                    with patch("anything_plays.libretro_save._user_save_directory",
                               return_value=root / "user-data"), patch.object(
                        CoreSession, "_make_system_directory", return_value=system_buffer
                    ):
                        session = CoreSession(None, system, rom, str(root / "core.so"))
                        try:
                            pointer = C.c_char_p()
                            self.assertTrue(session.environment(
                                31, C.cast(C.pointer(pointer), C.c_void_p)))
                            folder = Path(os.fsdecode(pointer.value))
                            self.assertEqual(
                                folder, native_core_save_directory(rom, system))
                            self.assertTrue(folder.is_dir())
                            self.assertEqual(folder.parent.name, "neo-geo-pocket")

                            system_pointer = C.c_char_p()
                            self.assertTrue(session.environment(
                                9, C.cast(C.pointer(system_pointer), C.c_void_p)))
                            self.assertEqual(
                                os.fsdecode(system_pointer.value), str(system_folder))
                        finally:
                            session.audio.close()

    def test_native_flash_path_is_only_for_supported_flash_cores(self):
        with self.assertRaises(ValueError):
            native_core_save_directory("/games/test.sfc", "snes")


if __name__ == "__main__":
    unittest.main()
