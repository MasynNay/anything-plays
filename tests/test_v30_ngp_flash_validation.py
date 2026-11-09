"""Prevent malformed NeoPop cartridge saves from reaching native C code."""

import os
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from anything_plays.gba_emulator import CoreSession
from anything_plays.neopop_flash import (
    BLOCK_HEADER, FLASH_MAGIC, HEADER, InvalidNeoPopFlash,
    MAX_FLASH_BLOCKS, MAX_FLASH_FILE_BYTES, check_cartridge_flash,
    inspect_neopop_flash,
)


def valid_flash(*blocks):
    """Synthetic native NeoPop flash, never a commercial/game ROM."""
    payload = b"".join(
        BLOCK_HEADER.pack(address, len(data)) + data
        for address, data in blocks
    )
    return HEADER.pack(FLASH_MAGIC, len(blocks), HEADER.size + len(payload)) + payload


class NeoPopFlashValidationTests(unittest.TestCase):
    def setUp(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name)
        self.flash = self.root / "game.flash"

    def read(self, payload):
        self.flash.write_bytes(payload)
        return inspect_neopop_flash(self.flash)

    def test_valid_272_byte_single_block_is_inspectable(self):
        result = self.read(valid_flash((0x200040, b"A" * 256)))
        self.assertEqual(result["file_bytes"], 272)
        self.assertEqual(result["block_count"], 1)
        self.assertEqual(result["blocks"], [{"address": 0x200040, "bytes": 256}])
        self.assertEqual(len(result["sha256"]), 64)

    def test_multi_block_file_preserves_exact_lengths_and_addresses(self):
        result = self.read(valid_flash(
            (0x200000, b"hello"), (0x210000, b"world!" * 15)
        ))
        self.assertEqual(result["block_count"], 2)
        self.assertEqual([b["bytes"] for b in result["blocks"]], [5, 90])

    def test_new_game_without_flash_is_allowed(self):
        self.assertIsNone(inspect_neopop_flash(self.flash))
        self.assertIsNone(check_cartridge_flash(self.root / "game.ngc", self.root))

    def test_truncated_and_oversized_header_fail_before_native_parse(self):
        cases = [
            (b"abc", "size bounds"),
            (HEADER.pack(0x1234, 1, 8), "magic"),
            (HEADER.pack(FLASH_MAGIC, 0, 8), "block count"),
            (HEADER.pack(FLASH_MAGIC, MAX_FLASH_BLOCKS + 1, 8), "block count"),
            (HEADER.pack(FLASH_MAGIC, 1, 10), "header size"),
            (HEADER.pack(FLASH_MAGIC, 1, 8), "block header"),
            (HEADER.pack(FLASH_MAGIC, 1, 8 + BLOCK_HEADER.size)
             + BLOCK_HEADER.pack(0x200000, 80), "block data"),
            (valid_flash((0x200000, b"valid")) + b"extra", "header size"),
        ]
        for payload, message in cases:
            with self.subTest(payload=payload[:24]):
                with self.assertRaisesRegex(InvalidNeoPopFlash, message):
                    self.read(payload)

    def test_outside_24_bit_flash_address_is_rejected(self):
        with self.assertRaisesRegex(InvalidNeoPopFlash, "outside cartridge bus"):
            self.read(valid_flash((0xFFFFFE, b"012345")))

    def test_symlink_does_not_let_flash_loader_escape_save_directory(self):
        unrelated = self.root / "private"
        unrelated.write_bytes(valid_flash((0x200000, b"valid")))
        try:
            self.flash.symlink_to(unrelated)
        except (OSError, NotImplementedError):
            self.skipTest("Platform does not permit test symlinks")
        with self.assertRaisesRegex(InvalidNeoPopFlash, "symlink"):
            inspect_neopop_flash(self.flash)

    def test_oversized_file_rejected_before_read(self):
        with self.flash.open("wb") as handle:
            handle.truncate(MAX_FLASH_FILE_BYTES + 1)
        with self.assertRaisesRegex(InvalidNeoPopFlash, "safe size"):
            inspect_neopop_flash(self.flash)

    def test_invalid_flash_rejected_before_retro_load_game_without_deletion(self):
        rom = self.root / "game.ngc"
        rom.write_bytes(b"synthetic test ROM")
        save_root = self.root / "userdata"
        system = self.root / "system"
        system.mkdir()
        buf = __import__("ctypes").create_string_buffer(os.fsencode(str(system)))
        with patch("anything_plays.libretro_save._user_save_directory",
                   return_value=save_root), patch.object(
                       CoreSession, "_make_system_directory", return_value=buf
                   ):
            session = CoreSession(None, "ngpc", rom, str(self.root / "core.so"))
            try:
                stored = Path(os.fsdecode(session._save_dir_buffer.value))
                bad = stored / "game.flash"
                bad.write_bytes(b"invalid")
                loaded = Mock()
                session.native = SimpleNamespace(system_info=loaded)
                with self.assertRaisesRegex(RuntimeError, "Unsafe Neo Geo Pocket"):
                    session._load_game()
                loaded.assert_not_called()
                self.assertEqual(bad.read_bytes(), b"invalid")
            finally:
                session.audio.close()


if __name__ == "__main__":
    unittest.main()
