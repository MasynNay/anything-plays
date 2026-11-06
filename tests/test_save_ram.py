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
