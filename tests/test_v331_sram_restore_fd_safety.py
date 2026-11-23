"""3.3.1: saved game SRAM restore validates the actual opened file.

Temporary four-byte save files only; no real ROM, emulator, cameras or
controller. Test substitutions exercise OS handle safety and failure modes.
"""
import ctypes as C
from contextlib import contextmanager
import os
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from anything_plays.libretro_save import SaveRAM


class SRAMRestoreDescriptorSafetyTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.rom = self.root / "game.gba"
        self.memory = C.create_string_buffer(b"INIT", 4)

    @contextmanager
    def session(self, *, private=False):
        with (
            patch("anything_plays.libretro_save.is_v32_preview",
                  return_value=False),
            patch("anything_plays.libretro_save.is_v33_candidate",
                  return_value=private),
            patch("anything_plays.libretro_save._user_save_directory",
                  return_value=self.root / "private-saves"),
        ):
            saver = SaveRAM(
                self.rom, lambda _kind: C.addressof(self.memory),
                lambda _kind: 4,
            )
            saver.path.parent.mkdir(parents=True, exist_ok=True)
            yield saver

    def test_regular_stable_save_restores_and_preserves_no_change_checkpoint(self):
        with self.session() as save:
            save.path.write_bytes(b"GOOD")
            save.restore()
            self.assertEqual(self.memory.raw, b"GOOD")
            self.assertFalse(save.persist())
            self.assertEqual(save.path.read_bytes(), b"GOOD")

    def test_regular_private_save_restores_without_importing_stable_progress(self):
        with self.session(private=True) as save:
            save.legacy_path.write_bytes(b"STBL")
            save.path.write_bytes(b"PRIV")
            save.restore()
            self.assertEqual(self.memory.raw, b"PRIV")
            self.assertFalse(save.persist())
            self.assertEqual(save.legacy_path.read_bytes(), b"STBL")

    def test_opened_private_save_uses_nonfollow_and_nonblocking_when_supported(self):
        with self.session(private=True) as save:
            save.path.write_bytes(b"PRIV")
            real_open = os.open
            flags_seen = []

            def observed_open(path, flags, *args, **kwargs):
                if Path(path) == save.path:
                    flags_seen.append(flags)
                return real_open(path, flags, *args, **kwargs)

            with patch("anything_plays.libretro_save.os.open",
                       side_effect=observed_open):
                save.restore()
            self.assertEqual(len(flags_seen), 1)
            for optional in ("O_NOFOLLOW", "O_NONBLOCK", "O_BINARY"):
                if getattr(os, optional, 0):
                    self.assertTrue(flags_seen[0] & getattr(os, optional))
            self.assertEqual(self.memory.raw, b"PRIV")

    def test_stable_symlink_save_remains_compatible_with_existing_users(self):
        with self.session() as save:
            shared = self.root / "synced-save.sav"
            shared.write_bytes(b"SYNC")
            try:
                save.path.symlink_to(shared)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"OS does not allow test symlinks: {exc}")
            save.restore()
            self.assertEqual(self.memory.raw, b"SYNC")
            self.assertFalse(save.persist())
            self.assertEqual(shared.read_bytes(), b"SYNC")

    def test_private_symlink_before_open_is_refused(self):
        with self.session(private=True) as save:
            stable = self.root / "stable.sav"
            stable.write_bytes(b"STBL")
            try:
                save.path.symlink_to(stable)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"OS does not allow test symlinks: {exc}")
            with self.assertRaisesRegex(ValueError, "must not link"):
                save.restore()
            self.assertEqual(self.memory.raw, b"INIT")
            self.assertEqual(stable.read_bytes(), b"STBL")

    @unittest.skipUnless(getattr(os, "O_NOFOLLOW", None) is not None,
                         "The OS does not support atomic no-follow opens")
    def test_private_symlink_swapped_after_last_is_file_check_is_not_read(self):
        with self.session(private=True) as save:
            save.path.write_bytes(b"PRIV")
            stable = self.root / "stable.sav"
            stable.write_bytes(b"STBL")
            original = Path.is_file
            probes = [0]

            def swap_after_final_probe(path):
                result = original(path)
                if path == save.path and result:
                    probes[0] += 1
                    if probes[0] == 3:
                        path.unlink()
                        path.symlink_to(stable)
                return result

            try:
                with patch.object(Path, "is_file", swap_after_final_probe):
                    with self.assertRaises(OSError):
                        save.restore()
            except (NotImplementedError, PermissionError) as exc:
                self.skipTest(f"OS does not allow test symlinks: {exc}")
            self.assertEqual(probes[0], 3)
            self.assertTrue(save.path.is_symlink())
            self.assertEqual(self.memory.raw, b"INIT")
            self.assertEqual(stable.read_bytes(), b"STBL")

    def test_private_hardlink_swapped_at_open_is_refused_by_fd_link_count(self):
        with self.session(private=True) as save:
            save.path.write_bytes(b"PRIV")
            stable = self.root / "stable.sav"
            stable.write_bytes(b"STBL")
            real_open = os.open
            swapped = [False]

            def swap_during_open(path, flags, *args, **kwargs):
                if Path(path) == save.path and not swapped[0]:
                    save.path.unlink()
                    try:
                        os.link(stable, save.path)
                    except (NotImplementedError, OSError) as exc:
                        self.skipTest(f"Hardlinks unavailable: {exc}")
                    swapped[0] = True
                return real_open(path, flags, *args, **kwargs)

            with patch("anything_plays.libretro_save.os.open",
                       side_effect=swap_during_open):
                with self.assertRaisesRegex(ValueError, "must not share"):
                    save.restore()
            self.assertTrue(swapped[0])
            self.assertEqual(self.memory.raw, b"INIT")
            self.assertEqual(stable.read_bytes(), b"STBL")

    @unittest.skipUnless(hasattr(os, "mkfifo") and hasattr(os, "O_NONBLOCK"),
                         "The OS does not support nonblocking named pipes")
    def test_swapped_named_pipe_is_rejected_without_blocking_read(self):
        with self.session() as save:
            os.mkfifo(save.path)
            original = Path.is_file

            def stale_file_probe(path):
                if path == save.path:
                    return True  # Earlier regular file was replaced by FIFO.
                return original(path)

            with patch.object(Path, "is_file", stale_file_probe):
                with self.assertRaisesRegex(ValueError, "regular file"):
                    save.restore()
            self.assertEqual(self.memory.raw, b"INIT")

    def test_descriptor_swapped_for_nonregular_file_does_not_touch_game_ram(self):
        with self.session() as save:
            save.path.write_bytes(b"GOOD")
            with patch("anything_plays.libretro_save.os.fstat",
                       return_value=Mock(st_mode=stat.S_IFCHR, st_nlink=1)):
                with self.assertRaisesRegex(ValueError, "regular file"):
                    save.restore()
            self.assertEqual(self.memory.raw, b"INIT")

    def test_oversized_file_still_reads_bounded_prefix_then_repairs_checkpoint(self):
        with self.session() as save:
            save.path.write_bytes(b"GOOD" + b"extra bytes")
            save.restore()
            self.assertEqual(self.memory.raw, b"GOOD")
            self.assertTrue(save.persist())
            self.assertEqual(save.path.read_bytes(), b"GOOD")
            self.assertFalse(save.persist())


if __name__ == "__main__":
    unittest.main()
