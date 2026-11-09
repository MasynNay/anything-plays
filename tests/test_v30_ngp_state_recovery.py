"""Full-state NGP recovery must fail closed on ROM/core drift and corruption."""
import ctypes as C
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from anything_plays.libretro_state import (
    LibretroRecoveryState, MAGIC, state_file_path,
)


def native_stub(initial=b"original state from real core"):
    image = {"value": initial, "serializes": 0, "restores": 0}

    def state_size():
        return len(image["value"])

    def serialize(destination, count):
        image["serializes"] += 1
        C.memmove(destination, image["value"], count)
        return True

    def unserialize(source, count):
        image["restores"] += 1
        image["value"] = C.string_at(source, count)
        return True

    return SimpleNamespace(library=SimpleNamespace(
        retro_serialize_size=state_size,
        retro_serialize=serialize,
        retro_unserialize=unserialize,
    )), image


class NeoGeoPocketRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.rom = self.root / "roms" / "pocket.ngc"
        self.rom.parent.mkdir()
        self.rom.write_bytes(b"test ROM fixture placeholder - not released")
        self.core = self.root / "core" / "mednafen_ngp_libretro.so"
        self.core.parent.mkdir()
        self.core.write_bytes(b"test core placeholder - no real binary loaded")
        self.save_root = self.root / "user-data"
        patcher = patch("anything_plays.libretro_save._user_save_directory",
                        return_value=self.save_root)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher2 = patch("anything_plays.libretro_state._user_save_directory",
                         return_value=self.save_root)
        patcher2.start()
        self.addCleanup(patcher2.stop)

    def _checkpoint(self, native):
        return LibretroRecoveryState(self.rom, "ngpc", self.core, native)

    def test_separate_sessions_restore_exact_state_from_atomic_checkpoint(self):
        first, value = native_stub()
        checkpoint = self._checkpoint(first)
        self.assertFalse(checkpoint.restore())
        self.assertTrue(checkpoint.persist())
        self.assertTrue(checkpoint.path.is_file())
        self.assertTrue(checkpoint.path.read_bytes().startswith(MAGIC))
        self.assertFalse(checkpoint.persist())  # unchanged data is not rewritten
        initial = value["value"]

        second, restored_value = native_stub(b"?" * len(initial))
        reloaded = self._checkpoint(second)
        self.assertTrue(reloaded.restore())
        self.assertEqual(restored_value["value"], initial)
        self.assertEqual(restored_value["restores"], 1)
        self.assertFalse(reloaded.persist())

    def test_tampering_rejected_before_native_unserialize(self):
        native, _ = native_stub()
        saved = self._checkpoint(native)
        self.assertTrue(saved.persist())
        raw = saved.path.read_bytes()
        saved.path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 0x10]))
        second, state = native_stub()
        with self.assertRaisesRegex(ValueError, "checksum"):
            self._checkpoint(second).restore()
        self.assertEqual(state["restores"], 0)

    def test_changed_core_or_rom_does_not_corrupt_game_by_loading_old_state(self):
        native, _ = native_stub()
        self._checkpoint(native).persist()
        old = self.core.read_bytes()
        self.core.write_bytes(old + b"v2")
        second, data = native_stub()
        with self.assertRaisesRegex(ValueError, "different ROM/core"):
            self._checkpoint(second).restore()
        self.assertEqual(data["restores"], 0)

        self.core.write_bytes(old)
        self.rom.write_bytes(self.rom.read_bytes() + b"new-content")
        third, data2 = native_stub()
        with self.assertRaisesRegex(ValueError, "different ROM/core"):
            self._checkpoint(third).restore()
        self.assertEqual(data2["restores"], 0)

    def test_oversized_state_is_rejected_without_native_serialize(self):
        native, value = native_stub()
        native.library.retro_serialize_size = lambda: 2 ** 31
        with self.assertRaisesRegex(ValueError, "oversized"):
            self._checkpoint(native).persist()
        self.assertEqual(value["serializes"], 0)

    def test_per_rom_path_keeps_consoles_and_identical_stems_separate(self):
        first = state_file_path(self.rom, "ngpc")
        other_rom = self.root / "other" / self.rom.name
        other_rom.parent.mkdir()
        other_rom.write_bytes(b"other game")
        second = state_file_path(other_rom, "ngpc")
        third = state_file_path(self.rom, "ngp")
        self.assertNotEqual(first, second)
        self.assertNotEqual(first, third)
        self.assertEqual(first, state_file_path(self.rom, "ngpc"))
        self.assertIn("native-core", str(first))
        with self.assertRaises(ValueError):
            state_file_path(self.rom, "gamecube")

    def test_raw_flash_lab_never_uses_recovery_state(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "tools/probe_ngp_flash_persistence.py"
        ).read_text("utf-8")
        self.assertIn("session.enable_state_resume = False", source)


if __name__ == "__main__":
    unittest.main()
