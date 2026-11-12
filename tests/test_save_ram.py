"""Saved game RAM stays beside the ROM and writes atomically."""

import ctypes as C
from concurrent.futures import ThreadPoolExecutor
import threading
import os
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
                original_open = tempfile.NamedTemporaryFile
                def block_legacy(*args, **kwargs):
                    if Path(kwargs["dir"]) == rom.parent:
                        raise PermissionError("Read-only game library")
                    return original_open(*args, **kwargs)
                with patch("anything_plays.libretro_save.tempfile.NamedTemporaryFile",
                           side_effect=block_legacy):
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
                with patch("anything_plays.libretro_save.os.replace",
                           side_effect=OSError("disk full")):
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
            actual_replace = os.replace
            replacements = []

            def count_replace(source, target):
                replacements.append(target)
                return actual_replace(source, target)

            with patch("anything_plays.libretro_save.os.replace",
                       side_effect=count_replace):
                self.assertTrue(save.persist())
                for _ in range(1000):
                    self.assertFalse(save.persist())
                self.assertEqual(len(replacements), 1)
                self.assertEqual(save.path.read_bytes(), b'ABCD')
                memory.raw = b'WXYZ'
                self.assertTrue(save.persist())
                self.assertEqual(len(replacements), 2)
                self.assertEqual(save.path.read_bytes(), b'WXYZ')

    def test_unique_temporary_files_and_fsync_preserve_last_complete_save(self):
        # Independent instances must not share a fixed .sav.tmp pathname.
        with tempfile.TemporaryDirectory() as tmp:
            memory = C.create_string_buffer(b"ONE!", 4)
            save = SaveRAM(Path(tmp) / "game.gba",
                           lambda kind: C.addressof(memory), lambda kind: 4)
            actual_replace = os.replace
            temp_names = []

            def count_replace(source, target):
                temp_names.append(Path(source).name)
                self.assertEqual(Path(target), save.path)
                self.assertEqual(Path(source).parent, save.path.parent)
                return actual_replace(source, target)

            with (
                patch("anything_plays.libretro_save.os.replace",
                      side_effect=count_replace),
                patch("anything_plays.libretro_save.os.fsync",
                      wraps=os.fsync) as fsync,
            ):
                self.assertTrue(save.persist())
                memory.raw = b"TWO!"
                self.assertTrue(save.persist())
            self.assertEqual(save.path.read_bytes(), b"TWO!")
            self.assertEqual(len(temp_names), 2)
            self.assertNotEqual(temp_names[0], temp_names[1])
            self.assertTrue(all(name.startswith("game.sav.")
                                and name.endswith(".tmp")
                                for name in temp_names))
            self.assertEqual(fsync.call_count, 2)
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])

    def test_two_independent_writers_never_share_temporary_save_files(self):
        # Force two independent app instances to reach the atomic replace
        # at the same time. The old fixed .sav.tmp design clobbered one
        # writer's snapshot and could delete the other's in-flight data.
        with tempfile.TemporaryDirectory() as tmp:
            rom = Path(tmp) / "game.gba"
            first = C.create_string_buffer(b"AAAA", 4)
            second = C.create_string_buffer(b"BBBB", 4)
            a = SaveRAM(rom, lambda kind: C.addressof(first), lambda kind: 4)
            b = SaveRAM(rom, lambda kind: C.addressof(second), lambda kind: 4)
            barrier = threading.Barrier(2)
            seen = []
            lock = threading.Lock()
            native_replace = os.replace

            def synchronized_replace(source, target):
                with lock:
                    seen.append(Path(source))
                    initial_call = len(seen) <= 2
                if initial_call:
                    # First calls overlap; retries must not reenter this
                    # two-party barrier or deadlock after one writer wins.
                    barrier.wait(timeout=10)
                return native_replace(source, target)

            with patch("anything_plays.libretro_save.os.replace",
                       side_effect=synchronized_replace):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    fa = pool.submit(a.persist)
                    fb = pool.submit(b.persist)
                    self.assertTrue(fa.result(timeout=20))
                    self.assertTrue(fb.result(timeout=20))

            self.assertGreaterEqual(len(seen), 2)
            self.assertEqual(len(set(seen)), 2)
            self.assertNotEqual(seen[0], seen[1])
            self.assertTrue(all(p.parent == rom.parent for p in seen))
            self.assertIn(rom.with_suffix(".sav").read_bytes(),
                          (b"AAAA", b"BBBB"))
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])

    def test_windows_transient_sharing_violation_retries_without_fallback(self):
        if os.name != "nt":
            self.skipTest("Windows sharing error codes are platform-specific")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memory = C.create_string_buffer(b"SAFE", 4)
            save = SaveRAM(root / "game.gba",
                           lambda kind: C.addressof(memory), lambda kind: 4)
            native_replace = os.replace
            attempts = [0]

            def temporary_lock(source, destination):
                attempts[0] += 1
                if attempts[0] == 1:
                    denied = PermissionError(13, "temporary file sharing violation")
                    denied.winerror = 32
                    raise denied
                return native_replace(source, destination)

            with (patch("anything_plays.libretro_save.os.replace",
                        side_effect=temporary_lock),
                  patch("anything_plays.libretro_save.time.sleep") as sleeper):
                self.assertTrue(save.persist())
            self.assertEqual(attempts[0], 2)
            sleeper.assert_called_once()
            self.assertEqual(save.path, root / "game.sav")
            self.assertEqual(save.path.read_bytes(), b"SAFE")
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_existing_fixed_tmp_symlink_is_never_followed(self):
        if os.name == "nt":
            self.skipTest("Symlink creation may require Windows developer mode")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            victim = root / "other-file"
            victim.write_bytes(b"PRIVATE")
            stale = root / "game.sav.tmp"
            stale.symlink_to(victim)
            memory = C.create_string_buffer(b"GOOD", 4)
            save = SaveRAM(root / "game.gba",
                           lambda kind: C.addressof(memory), lambda kind: 4)
            self.assertTrue(save.persist())
            self.assertEqual(victim.read_bytes(), b"PRIVATE")
            self.assertTrue(stale.is_symlink())
            self.assertEqual(save.path.read_bytes(), b"GOOD")

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
