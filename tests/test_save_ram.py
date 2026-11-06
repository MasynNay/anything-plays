"""Saved game RAM stays beside the ROM and writes atomically."""

import ctypes as C
from pathlib import Path
import tempfile
import unittest

from libretro_save import SaveRAM


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


if __name__ == "__main__":
    unittest.main()
