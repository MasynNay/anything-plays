"""Libretro system-directory and native save callbacks honor preview scope.

These tests instantiate no C library, game ROM, audio device or emulator
thread. They use only the path callback of an uninitialized CoreSession.
"""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from anything_plays.gba_emulator import CoreSession


class NativeLibretroFolderTests(unittest.TestCase):
    def session(self):
        instance = CoreSession.__new__(CoreSession)
        instance.system = "gba"
        instance.core_path = None
        return instance

    def test_preview_does_not_use_stable_macos_firmware_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            stable = home / "Library" / "Application Support" / "AnythingPlays"
            stable.mkdir(parents=True)
            (stable / "stable-marker.txt").write_bytes(b"unchanged")
            preview = home / ".config" / "anything-plays-32-preview" / "libretro-system"
            with patch("anything_plays.gba_emulator.sys.platform", "darwin"):
                with patch("anything_plays.gba_emulator.is_v32_preview",
                           return_value=True):
                    with patch("anything_plays.gba_emulator.preview_system_directory",
                               return_value=preview):
                        encoded = self.session()._make_system_directory()
            self.assertEqual(os.fsdecode(encoded.value), str(preview))
            self.assertTrue(preview.is_dir())
            self.assertEqual(
                (stable / "stable-marker.txt").read_bytes(), b"unchanged"
            )
            self.assertEqual(sorted(p.name for p in stable.iterdir()),
                             ["stable-marker.txt"])

    def test_preview_uses_same_isolated_folder_on_windows_and_linux(self):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory) / "preview-libretro-system"
            for target in ("win32", "linux"):
                with self.subTest(os=target):
                    with patch("anything_plays.gba_emulator.sys.platform",
                               target):
                        with patch("anything_plays.gba_emulator.is_v32_preview",
                                   return_value=True):
                            with patch("anything_plays.gba_emulator.preview_system_directory",
                                       return_value=private):
                                encoded = self.session()._make_system_directory()
                    self.assertEqual(os.fsdecode(encoded.value), str(private))

    def test_stable_macos_path_remains_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with patch("anything_plays.gba_emulator.sys.platform", "darwin"):
                with patch("anything_plays.gba_emulator.is_v32_preview",
                           return_value=False):
                    with patch("anything_plays.gba_emulator.Path.home",
                               return_value=home):
                        encoded = self.session()._make_system_directory()
            self.assertEqual(
                os.fsdecode(encoded.value),
                str(home / "Library" / "Application Support" / "AnythingPlays"),
            )


if __name__ == "__main__":
    unittest.main()
