"""Private 3.2 saves, native system data and downloaded cores never share stable paths.

No ROM or native game core is loaded. A synthetic four-byte SRAM buffer tests
the exact restore/persist boundary, including an already-existing stable save.
Stable-version paths must remain byte-for-byte compatible.
"""

import ctypes as C
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from anything_plays.build_identity import make_identity
from anything_plays.core_packs import managed_core_root
from anything_plays.libretro_save import (
    SaveRAM, _fallback_path, _user_save_directory,
    native_core_save_directory,
)
from anything_plays.preview_storage import (
    is_v32_preview, preview_system_directory,
)


def identity(channel):
    return patch(
        "anything_plays.preview_storage.current_identity",
        return_value=make_identity(channel),
    )


class PreviewStorageTests(unittest.TestCase):
    def test_identity_is_not_a_user_controlled_save_directory(self):
        with identity("v32_preview"):
            self.assertTrue(is_v32_preview())
        with identity("v311_stable_candidate"):
            self.assertFalse(is_v32_preview())

    def test_save_directories_are_separate_on_all_desktop_os(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            with patch("pathlib.Path.home", return_value=home):
                for platform_name in ("linux", "win32", "darwin"):
                    with self.subTest(platform=platform_name):
                        with patch(
                            "anything_plays.libretro_save.sys",
                            SimpleNamespace(platform=platform_name),
                        ):
                            with patch.dict(os.environ, {
                                "APPDATA": str(home / "AppData" / "Roaming"),
                                "XDG_DATA_HOME": str(home / "xdg"),
                            }):
                                with identity("v32_preview"):
                                    preview = _user_save_directory()
                                    native = native_core_save_directory(
                                        home / "sample.gba", "ngp",
                                    )
                                with identity("v311_stable_candidate"):
                                    stable = _user_save_directory()
                                self.assertNotEqual(preview, stable)
                                self.assertNotIn(
                                    str(stable) + os.sep,
                                    str(preview) + os.sep,
                                )
                                self.assertTrue(native.is_relative_to(preview))

    def test_managed_core_overlay_is_not_the_public_30_overlay(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            with patch("pathlib.Path.home", return_value=home):
                for platform_name in ("linux", "win32", "darwin"):
                    with self.subTest(platform=platform_name):
                        with patch(
                            "anything_plays.core_packs.sys",
                            SimpleNamespace(platform=platform_name),
                        ):
                            with patch.dict(os.environ, {
                                "LOCALAPPDATA": str(home / "local"),
                                "XDG_DATA_HOME": str(home / "xdg"),
                            }):
                                with identity("v32_preview"):
                                    preview = managed_core_root()
                                with identity("v311_stable_candidate"):
                                    stable = managed_core_root()
                                self.assertNotEqual(preview, stable)
                                self.assertEqual(preview.name, "cores")
                                self.assertIn("3.2-preview", preview.parts)
                                self.assertIn("3.0", stable.parts)

    def test_native_system_directory_is_not_stable_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            result = preview_system_directory(home)
            self.assertEqual(
                result, home / ".config" / "anything-plays-32-preview"
                / "libretro-system",
            )
            self.assertNotEqual(
                result, home / ".config" / "anything-plays",
            )

    def test_preview_does_not_read_or_overwrite_a_rom_adjacent_save(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            rom = home / "my-game.gba"
            rom.write_bytes(b"homebrew-test-rom-placeholder")
            legacy = rom.with_suffix(".sav")
            legacy.write_bytes(b"OLD!")
            with patch("pathlib.Path.home", return_value=home):
                with patch.dict(os.environ, {"XDG_DATA_HOME": str(home / "xdg")}):
                    with identity("v32_preview"):
                        buffer = C.create_string_buffer(b"NEW!", 4)
                        sav = SaveRAM(
                            rom, lambda _: C.addressof(buffer), lambda _: 4,
                        )
                        self.assertEqual(sav.legacy_path, legacy)
                        self.assertNotEqual(sav.path, legacy)
                        self.assertEqual(
                            sav.path,
                            _fallback_path(rom),
                        )
                        sav.restore()
                        self.assertEqual(C.string_at(buffer, 4), b"NEW!")
                        self.assertTrue(sav.persist())
                        self.assertEqual(sav.path.read_bytes(), b"NEW!")
                        self.assertEqual(legacy.read_bytes(), b"OLD!")
                        self.assertFalse(sav.persist())

    def test_stable_save_semantics_stay_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            rom = home / "my-game.gba"
            rom.touch()
            legacy = rom.with_suffix(".sav")
            legacy.write_bytes(b"OLD!")
            with patch("pathlib.Path.home", return_value=home):
                with patch.dict(os.environ, {"XDG_DATA_HOME": str(home / "xdg")}):
                    with identity("v311_stable_candidate"):
                        buffer = C.create_string_buffer(b"NEW!", 4)
                        sav = SaveRAM(
                            rom, lambda _: C.addressof(buffer), lambda _: 4,
                        )
                        self.assertEqual(sav.path, legacy)
                        sav.restore()
                        self.assertEqual(C.string_at(buffer, 4), b"OLD!")


if __name__ == "__main__":
    unittest.main()
