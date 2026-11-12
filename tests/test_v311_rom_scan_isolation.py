"""3.1.1 ROM shelf must not follow a linked file, image or selected root.

Use temporary synthetic filenames only. No game ROMs, private directories,
network storage, or real removable drives are involved.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from anything_plays.rom_library import find_cover_art, scan_rom_directory


class LinkedGameShelfTests(unittest.TestCase):
    @staticmethod
    def link(source, dest, *, directory=False):
        try:
            dest.symlink_to(source, target_is_directory=directory)
        except (NotImplementedError, OSError) as exc:
            raise unittest.SkipTest(
                f"Symlinks unavailable for this test environment: {exc}"
            )

    def test_symlinked_game_and_directory_do_not_escape_selected_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "library"
            private = root / "outside"
            library.mkdir()
            private.mkdir()
            (private / "secret.gba").write_bytes(b"not a permitted ROM")
            (library / "local.gba").write_bytes(b"safe synthetic data")
            self.link(private / "secret.gba", library / "linked.gba")
            self.link(private, library / "outside-folder", directory=True)

            found = scan_rom_directory(library, (".gba",))
            self.assertEqual([p.name for p in found], ["local.gba"])

    def test_symlinked_selected_root_is_not_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real"
            real.mkdir()
            (real / "game.gba").write_bytes(b"synthetic")
            linked = root / "alias"
            self.link(real, linked, directory=True)
            self.assertEqual(scan_rom_directory(linked, (".gba",)), [])
            self.assertEqual([p.name for p in scan_rom_directory(real, (".gba",))],
                             ["game.gba"])

    def test_cover_skips_linked_image_and_finds_local_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "library"
            private = root / "private"
            library.mkdir()
            private.mkdir()
            rom = library / "Sample.gba"
            rom.write_bytes(b"synthetic")
            outside = private / "outside.png"
            outside.write_bytes(b"private image placeholder")
            self.link(outside, library / "Sample.png")
            (library / "cover.png").write_bytes(b"safe local cover")

            self.assertEqual(find_cover_art(rom), library / "cover.png")
            (library / "cover.png").unlink()
            self.assertIsNone(find_cover_art(rom))

    def test_one_disconnected_file_does_not_hide_healthy_neighbors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "first.gba").write_bytes(b"synthetic")
            (root / "missing.gba").write_bytes(b"synthetic")
            (root / "third.gba").write_bytes(b"synthetic")
            original = Path.is_file

            def intermittent_file_status(path):
                if path.name == "missing.gba":
                    raise OSError("removable media vanished for this entry")
                return original(path)

            with patch.object(Path, "is_file", intermittent_file_status):
                found = scan_rom_directory(root, (".gba",))
            self.assertEqual([p.name for p in found],
                             ["first.gba", "third.gba"])

    def test_inaccessible_selected_root_returns_empty_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = Path.is_dir

            def disconnected_root(path):
                if path == root:
                    raise OSError("the USB volume is offline")
                return original(path)

            with patch.object(Path, "is_dir", disconnected_root):
                self.assertEqual(scan_rom_directory(root, (".gba",)), [])

    def test_normal_case_insensitive_scan_and_cover_remain_functional(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "My_Game.GBA").write_bytes(b"synthetic")
            (root / "My_Game.webp").write_bytes(b"synthetic cover")
            (root / "ignore.txt").write_bytes(b"not a ROM")
            found = scan_rom_directory(root, (".gba",))
            self.assertEqual([p.name for p in found], ["My_Game.GBA"])
            self.assertEqual(find_cover_art(found[0]), root / "My_Game.webp")


if __name__ == "__main__":
    unittest.main()
