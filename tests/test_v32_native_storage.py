"""Unreleased 3.2 gameplay must never overwrite stable saves or core packs.

Synthetic RAM only; no ROM, emulator, USB device or network required.
All three desktop OS conventions keep stable version paths unchanged.
"""

import ctypes as C
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from anything_plays.core_packs import managed_core_root
from anything_plays.libretro_save import (
    SaveRAM, _user_save_directory, native_core_save_directory,
)
from anything_plays.preview_storage import preview_system_directory


class V32NativeStorageTests(unittest.TestCase):
    def test_rom_adjacent_stable_sav_survives_private_preview_play(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            game = home / "old-game.gba"
            game.write_bytes(b"dummy game -- no real ROM")
            stable = game.with_suffix(".sav")
            stable.write_bytes(b"STABLE_PROGRESS_DO_NOT_TOUCH")
            data_root = home / "data"
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(data_root)}):
                with patch("anything_plays.libretro_save.is_v32_preview",
                           return_value=True):
                    memory = (C.c_ubyte * 4)(1, 2, 3, 4)
                    sav = SaveRAM(
                        game,
                        lambda _id: C.addressof(memory),
                        lambda _id: 4,
                    )
                    self.assertEqual(sav.path, sav.fallback_path)
                    self.assertNotEqual(sav.path, stable)
                    self.assertIn("3.2-preview", str(sav.path))
                    self.assertTrue(sav.persist())
                    self.assertEqual(sav.path.read_bytes(), bytes(memory))
                    self.assertEqual(
                        stable.read_bytes(), b"STABLE_PROGRESS_DO_NOT_TOUCH",
                    )
                    # A second preview session restores ONLY its own SRAM.
                    for i in range(4):
                        memory[i] = 0
                    new_session = SaveRAM(
                        game, lambda _id: C.addressof(memory), lambda _id: 4,
                    )
                    new_session.restore()
                    self.assertEqual(list(memory), [1, 2, 3, 4])
                    self.assertEqual(
                        stable.read_bytes(), b"STABLE_PROGRESS_DO_NOT_TOUCH",
                    )

    def _make_test_symlink(self, target, link, *, directory=True):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Symlink creation unavailable on host: {exc}")

    def test_preview_save_root_rejects_redirect_to_stable_saves(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            stable = home / "data" / "anything-plays" / "saves"
            stable.mkdir(parents=True)
            preview_parent = home / "data" / "anything-plays"
            self._make_test_symlink(stable, preview_parent / "3.2-preview")
            with patch.dict(os.environ, {
                "XDG_DATA_HOME": str(home / "data"),
            }):
                with patch("anything_plays.libretro_save.is_v32_preview",
                           return_value=True):
                    with self.assertRaisesRegex(ValueError, "must not link"):
                        _user_save_directory()
            self.assertEqual(list(stable.iterdir()), [])

    def test_preview_core_overlay_rejects_redirect_to_stable(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            old = home / "data" / "anything-plays" / "3.0"
            old.mkdir(parents=True)
            self._make_test_symlink(old, old.parent / "3.2-preview")
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(home / "data")}):
                with patch("anything_plays.core_packs.is_v32_preview",
                           return_value=True):
                    with patch("anything_plays.core_packs.sys.platform",
                               "linux"):
                        with self.assertRaisesRegex(ValueError, "must not link"):
                            managed_core_root()

    def test_libretro_system_dir_rejects_redirect_to_stable(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            preview = home / ".config" / "anything-plays-32-preview"
            stable = home / ".config" / "anything-plays" / "libretro-system"
            preview.mkdir(parents=True)
            stable.mkdir(parents=True)
            self._make_test_symlink(stable, preview / "libretro-system")
            with self.assertRaisesRegex(ValueError, "must not link"):
                preview_system_directory(home)

    def test_preview_never_restores_symlinked_legacy_save_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            game = home / "game.gba"
            game.write_bytes(b"mock ROM")
            stable = game.with_suffix(".sav")
            stable.write_bytes(b"ABCD")
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(home / "data")}):
                with patch("anything_plays.libretro_save.is_v32_preview",
                           return_value=True):
                    memory = (C.c_ubyte * 4)()
                    sav = SaveRAM(
                        game, lambda _id: C.addressof(memory), lambda _id: 4,
                    )
                    sav.path.parent.mkdir(parents=True)
                    self._make_test_symlink(
                        stable, sav.path, directory=False,
                    )
                    with self.assertRaisesRegex(ValueError, "must not link"):
                        sav.restore()
                    self.assertEqual(stable.read_bytes(), b"ABCD")

    def test_stable_rom_adjacent_save_path_remains_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            game = Path(temporary) / "old-game.gba"
            with patch("anything_plays.libretro_save.is_v32_preview",
                       return_value=False):
                sav = SaveRAM(game, lambda _id: None, lambda _id: 0)
                self.assertEqual(sav.path, game.with_suffix(".sav"))
                self.assertEqual(sav.legacy_path, sav.path)

    def test_mgba_native_system_files_use_private_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = preview_system_directory(temporary)
            self.assertEqual(
                folder, Path(temporary) / ".config"
                / "anything-plays-32-preview" / "libretro-system",
            )
            self.assertFalse(folder.exists())  # pure path resolution

    def test_core_pack_store_never_reads_existing_stable_overlay(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            data = home / "data"
            with patch("anything_plays.core_packs.sys.platform", "linux"):
                with patch("anything_plays.core_packs.Path.home",
                           return_value=home):
                    with patch.dict(os.environ, {"XDG_DATA_HOME": str(data)}):
                        with patch("anything_plays.core_packs.is_v32_preview",
                                   return_value=False):
                            stable = managed_core_root()
                        with patch("anything_plays.core_packs.is_v32_preview",
                                   return_value=True):
                            preview = managed_core_root()
            self.assertEqual(
                stable, data / "anything-plays" / "3.0" / "cores",
            )
            self.assertEqual(
                preview, data / "anything-plays" / "3.2-preview" / "cores",
            )
            self.assertNotEqual(stable, preview)

    def test_preview_save_roots_are_distinct_on_every_desktop_os(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            env = {
                "XDG_DATA_HOME": str(home / "data"),
                "APPDATA": str(home / "roaming"),
            }
            for platform_name in ("linux", "darwin", "win32"):
                with self.subTest(platform=platform_name):
                    with patch("anything_plays.libretro_save.sys.platform",
                               platform_name):
                        with patch("anything_plays.libretro_save.Path.home",
                                   return_value=home):
                            with patch.dict(os.environ, env):
                                with patch(
                                    "anything_plays.libretro_save.is_v32_preview",
                                    return_value=False,
                                ):
                                    stable = _user_save_directory()
                                with patch(
                                    "anything_plays.libretro_save.is_v32_preview",
                                    return_value=True,
                                ):
                                    preview = _user_save_directory()
                                    native = native_core_save_directory(
                                        home / "game.ngp", "ngp",
                                    )
                    self.assertNotEqual(stable, preview)
                    self.assertTrue(str(native).startswith(str(preview)))
                    self.assertTrue("Preview-3.2" in str(preview)
                                    or "3.2-preview" in str(preview))


if __name__ == "__main__":
    unittest.main()
