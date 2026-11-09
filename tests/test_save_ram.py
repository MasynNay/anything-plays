"""Saved game RAM stays beside the ROM and writes atomically."""

import ctypes as C
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from anything_plays.libretro_save import SaveRAM


class SaveRAMTests(unittest.TestCase):
    def test_restore_and_persist_uses_legacy_sav_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            rom = Path(tmp) / "game.gba"
            memory = C.create_string_buffer(4)
            save = SaveRAM(rom, lambda kind: C.addressof(memory), lambda kind: 4)
            save.path.write_bytes(b"ABCD")
            save.restore()
            self.assertEqual(memory.raw, b"ABCD")
            memory.raw = b"WXYZ"
            save.persist()
            self.assertEqual((Path(tmp) / "game.sav").read_bytes(), b"WXYZ")
            self.assertFalse(save.path.with_suffix(".sav.tmp").exists())


    def test_oversized_native_sram_is_rejected_without_reading_memory(self):
        from anything_plays.libretro_save import MAX_SAVE_RAM_BYTES
        with tempfile.TemporaryDirectory() as tmp:
            memory = C.create_string_buffer(4)
            save = SaveRAM(
                Path(tmp) / "game.gba",
                lambda kind: C.addressof(memory),
                lambda kind: MAX_SAVE_RAM_BYTES + 1,
            )
            with self.assertRaisesRegex(ValueError, "64 MiB limit"):
                save.persist()
            with self.assertRaisesRegex(ValueError, "64 MiB limit"):
                save.restore()
            self.assertFalse(save.path.exists())

    def test_oversized_existing_save_is_read_only_to_memory_limit(self):
        # The existing file is larger than the core SRAM. Read only the
        # expected bytes + 1 to detect the mismatch and repair on persist.
        with tempfile.TemporaryDirectory() as tmp:
            memory = C.create_string_buffer(4)
            save = SaveRAM(
                Path(tmp) / "game.gba",
                lambda kind: C.addressof(memory),
                lambda kind: 4,
            )
            save.path.write_bytes(b"ABCD" + b"extra bytes")
            save.restore()
            self.assertEqual(memory.raw, b"ABCD")
            self.assertTrue(save.persist())
            self.assertEqual(save.path.read_bytes(), b"ABCD")

    def test_read_only_rom_library_falls_back_and_preserves_legacy_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rom = root / "games" / "game.gba"
            rom.parent.mkdir()
            memory = C.create_string_buffer(b"ABCD", 4)
            with patch("anything_plays.libretro_save._user_save_directory",
                       return_value=root / "safe-saves"):
                save = SaveRAM(rom, lambda n: C.addressof(memory), lambda n: 4)
                old_tmp = save.path.with_suffix(".sav.tmp")
                actual_write = Path.write_bytes
                def block_legacy(path, data):
                    if path == old_tmp:
                        raise PermissionError("Read-only game library")
                    return actual_write(path, data)
                with patch.object(Path, "write_bytes", block_legacy):
                    self.assertTrue(save.persist())
                self.assertEqual(save.path, save.fallback_path)
                self.assertEqual(save.path.read_bytes(), b"ABCD")
                self.assertFalse(old_tmp.exists())
                save.legacy_path.write_bytes(b"OLD!")
                memory.raw = b"0000"
                fresh = SaveRAM(rom, lambda n: C.addressof(memory), lambda n: 4)
                fresh.restore()
                self.assertEqual(memory.raw, b"ABCD")
                self.assertFalse(fresh.persist())
                self.assertEqual(fresh.path, save.fallback_path)

    def test_same_named_roms_from_two_folders_have_isolated_fallbacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("anything_plays.libretro_save._user_save_directory",
                       return_value=root / "safe-saves"):
                a = SaveRAM(root / "A" / "game.sfc", lambda n: 0, lambda n: 0)
                b = SaveRAM(root / "B" / "game.sfc", lambda n: 0, lambda n: 0)
                self.assertNotEqual(a.fallback_path, b.fallback_path)

    def test_failed_fallback_save_does_not_destroy_previous_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rom = root / "games" / "game.gba"
            rom.parent.mkdir()
            memory = C.create_string_buffer(b"GOOD", 4)
            with patch("anything_plays.libretro_save._user_save_directory",
                       return_value=root / "safe-saves"):
                save = SaveRAM(rom, lambda n: C.addressof(memory), lambda n: 4)
                save.fallback_path.parent.mkdir(parents=True)
                save.fallback_path.write_bytes(b"GOOD")
                save.restore()
                memory.raw = b"NEXT"
                with patch.object(Path, "replace", side_effect=OSError("disk full")):
                    with self.assertRaisesRegex(OSError, "disk full"):
                        save.persist()
                self.assertEqual(save.fallback_path.read_bytes(), b"GOOD")
                self.assertFalse(save.fallback_path.with_suffix(".sav.tmp").exists())

    def test_unchanged_sram_does_not_rewrite_for_thousands_of_cycles(self):
        # One saved digest means that days of idle emulation do not cause
        # repeated writes of identical game progress.
        with tempfile.TemporaryDirectory() as tmp:
            memory = C.create_string_buffer(b'ABCD', 4)
            save = SaveRAM(Path(tmp) / 'game.gba',
                           lambda kind: C.addressof(memory), lambda kind: 4)
            actual_replace = Path.replace
            replacements = []

            def count_replace(source, target):
                replacements.append(target)
                return actual_replace(source, target)

            with patch.object(Path, 'replace', count_replace):
                self.assertTrue(save.persist())
                for _ in range(1000):
                    self.assertFalse(save.persist())
                self.assertEqual(len(replacements), 1)
                self.assertEqual(save.path.read_bytes(), b'ABCD')
                memory.raw = b'WXYZ'
                self.assertTrue(save.persist())
                self.assertEqual(len(replacements), 2)
                self.assertEqual(save.path.read_bytes(), b'WXYZ')

    def test_restore_does_not_rewrite_existing_save_without_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = C.create_string_buffer(4)
            save = SaveRAM(Path(tmp) / 'game.gba',
                           lambda kind: C.addressof(memory), lambda kind: 4)
            save.path.write_bytes(b'ABCD')
            save.restore()
            self.assertFalse(save.persist())
            self.assertEqual(memory.raw, b'ABCD')

    def test_incomplete_saved_ram_file_is_normalized_on_next_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = C.create_string_buffer(4)
            save = SaveRAM(Path(tmp) / 'game.gba',
                           lambda kind: C.addressof(memory), lambda kind: 4)
            save.path.write_bytes(b'AB')
            save.restore()
            self.assertEqual(memory.raw[:2], b'AB')
            self.assertTrue(save.persist())
            self.assertEqual(save.path.stat().st_size, 4)
            self.assertFalse(save.persist())

if __name__ == "__main__":
    unittest.main()
