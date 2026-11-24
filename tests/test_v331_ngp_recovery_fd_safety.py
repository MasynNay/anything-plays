"""3.3.1 NGP resume states: real opened-file safety and damaged media repair.

All ROM/core/state bytes are synthetic fixtures on disposable local storage.
No actual emulator, USB device, camera, network or user save is accessed.
"""
import ctypes as C
import os
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from anything_plays.libretro_state import LibretroRecoveryState, _hash_file, MAGIC


def fake_native(data=b"GOOD"):
    state = {"bytes": data, "restores": 0}

    def serialize(pointer, length):
        C.memmove(pointer, state["bytes"], length)
        return True

    def restore(pointer, length):
        state["bytes"] = C.string_at(pointer, length)
        state["restores"] += 1
        return True

    lib = SimpleNamespace(
        retro_serialize_size=lambda: len(state["bytes"]),
        retro_serialize=serialize,
        retro_unserialize=restore,
    )
    return SimpleNamespace(library=lib), state


class NeoGeoPocketOpenedFileTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.rom = self.root / "fixture.ngc"
        self.core = self.root / "libretro.so"
        self.rom.write_bytes(b"synthetic ROM")
        self.core.write_bytes(b"synthetic core")
        patcher = patch(
            "anything_plays.libretro_state._user_save_directory",
            return_value=self.root / "saves",
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def checkpoint(self):
        native, state = fake_native()
        return LibretroRecoveryState(self.rom, "ngpc", self.core, native), state

    def test_normal_identity_and_resume_round_trip(self):
        item, _ = self.checkpoint()
        self.assertTrue(item.persist())
        self.assertTrue(item.path.read_bytes().startswith(MAGIC))
        self.assertFalse(item.persist())
        second, state = self.checkpoint()
        self.assertTrue(second.restore())
        self.assertEqual(state["bytes"], b"GOOD")
        self.assertEqual(state["restores"], 1)
        self.assertFalse(second.persist())

    def test_rom_and_core_identity_open_is_bounded_nonblocking_and_nofollow(self):
        original = os.open
        flags_seen = []

        def observe(path, flags, *args, **kwargs):
            flags_seen.append((Path(path), flags))
            return original(path, flags, *args, **kwargs)

        with patch("anything_plays.libretro_state.os.open", side_effect=observe):
            item, _ = self.checkpoint()
            self.assertEqual(len(item.rom_sha), 64)
        self.assertEqual([path for path, _ in flags_seen],
                         [self.rom, self.core])
        for _path, flags in flags_seen:
            for name in ("O_BINARY", "O_NOFOLLOW", "O_NONBLOCK"):
                if getattr(os, name, 0):
                    self.assertTrue(flags & getattr(os, name))

    @unittest.skipUnless(getattr(os, "O_NOFOLLOW", 0),
                         "Open-time no-follow flag is unavailable")
    def test_symlink_swapped_after_identity_path_probe_is_not_hashed(self):
        outside = self.root / "private"
        outside.write_bytes(b"outside ROM content")
        original = Path.is_file
        swapped = []

        def probe(path):
            result = original(path)
            if path == self.rom and result and not swapped:
                self.rom.unlink()
                try:
                    self.rom.symlink_to(outside)
                except (OSError, NotImplementedError):
                    self.skipTest("Symlinks unavailable on this host")
                swapped.append(True)
            return result

        with patch.object(Path, "is_file", probe):
            with self.assertRaises((ValueError, OSError)):
                _hash_file(self.rom, 100)
        self.assertEqual(swapped, [True])
        self.assertEqual(outside.read_bytes(), b"outside ROM content")

    @unittest.skipUnless(hasattr(os, "mkfifo") and getattr(os, "O_NONBLOCK", 0),
                         "Nonblocking named pipes are unavailable")
    def test_swapped_identity_fifo_is_rejected_without_blocking(self):
        self.rom.unlink()
        os.mkfifo(self.rom)
        real_is_file = Path.is_file
        with patch.object(
            Path, "is_file",
            lambda p: True if p == self.rom else real_is_file(p),
        ):
            with self.assertRaisesRegex(ValueError, "unavailable"):
                _hash_file(self.rom, 100)

    def test_identity_file_growth_after_path_probe_rejects_new_bytes(self):
        original = os.open
        changed = []

        def grow_before_open(path, flags, *args, **kwargs):
            if Path(path) == self.rom and not changed:
                self.rom.write_bytes(b"X" * 120)
                changed.append(True)
            return original(path, flags, *args, **kwargs)

        with patch("anything_plays.libretro_state.os.open",
                   side_effect=grow_before_open):
            with self.assertRaisesRegex(ValueError, "too large"):
                _hash_file(self.rom, 100)
        self.assertEqual(changed, [True])

    def test_identity_truncation_during_read_is_not_accepted(self):
        with patch("anything_plays.libretro_state.os.fstat",
                   return_value=Mock(st_mode=stat.S_IFREG, st_size=20)):
            with self.assertRaisesRegex(ValueError, "changed"):
                _hash_file(self.rom, 100)

    def test_restore_uses_opened_descriptor_for_regular_file_validation(self):
        item, state = self.checkpoint()
        self.assertTrue(item.persist())
        with patch("anything_plays.libretro_state.os.fstat",
                   return_value=Mock(st_mode=stat.S_IFIFO, st_size=0,
                                     st_nlink=1)):
            with self.assertRaisesRegex(ValueError, "regular file"):
                item.restore()
        self.assertEqual(state["restores"], 0)

    @unittest.skipUnless(hasattr(os, "mkfifo") and getattr(os, "O_NONBLOCK", 0),
                         "Nonblocking named pipes are unavailable")
    def test_resume_file_swapped_to_fifo_never_reads_bytes(self):
        item, state = self.checkpoint()
        item.persist()
        item.path.unlink()
        os.mkfifo(item.path)
        real_is_file = Path.is_file
        with patch.object(
            Path, "is_file",
            lambda p: True if p == item.path else real_is_file(p),
        ):
            with self.assertRaisesRegex(ValueError, "regular file"):
                item.restore()
        self.assertEqual(state["restores"], 0)

    @unittest.skipUnless(getattr(os, "O_NOFOLLOW", 0),
                         "Open-time no-follow flag is unavailable")
    def test_resume_file_swapped_to_symlink_is_never_restored(self):
        item, state = self.checkpoint()
        item.persist()
        outside = self.root / "private.apstate"
        outside.write_bytes(item.path.read_bytes())
        real_is_file = Path.is_file
        swapped = []

        def probe(path):
            result = real_is_file(path)
            if path == item.path and result and not swapped:
                item.path.unlink()
                try:
                    item.path.symlink_to(outside)
                except (OSError, NotImplementedError):
                    self.skipTest("Symlinks unavailable")
                swapped.append(True)
            return result

        with patch.object(Path, "is_file", probe):
            with self.assertRaises((OSError, ValueError)):
                item.restore()
        self.assertEqual(swapped, [True])
        self.assertEqual(state["restores"], 0)

    def test_private_candidate_rejects_shared_resume_fd(self):
        item, state = self.checkpoint()
        item.persist()
        extra = self.root / "other-save"
        try:
            os.link(item.path, extra)
        except (OSError, NotImplementedError):
            self.skipTest("Hardlinks unavailable")
        with (
            patch("anything_plays.libretro_state.is_v33_candidate",
                  return_value=True),
            patch("anything_plays.libretro_state._checked_native_save_path",
                  side_effect=lambda path: path),
        ):
            with self.assertRaisesRegex(ValueError, "cannot share"):
                item.restore()
        self.assertEqual(state["restores"], 0)

    def test_private_candidate_rejects_shared_checkpoint_on_unchanged_persist(self):
        item, _ = self.checkpoint()
        item.persist()
        other = self.root / "other-save"
        try:
            os.link(item.path, other)
        except (OSError, NotImplementedError):
            self.skipTest("Hardlinks unavailable")
        original = item.path.read_bytes()
        with (
            patch("anything_plays.libretro_state.is_v33_candidate",
                  return_value=True),
            patch("anything_plays.libretro_state._checked_native_save_path",
                  side_effect=lambda path: path),
        ):
            with self.assertRaisesRegex(ValueError, "cannot share"):
                item.persist()
        self.assertEqual(item.path.read_bytes(), original)
        self.assertEqual(other.read_bytes(), original)

    def test_private_candidate_rejects_symlink_on_unchanged_persist(self):
        item, _ = self.checkpoint()
        item.persist()
        outside = self.root / "other-private-save"
        outside.write_bytes(item.path.read_bytes())
        item.path.unlink()
        try:
            item.path.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        original = outside.read_bytes()
        with (
            patch("anything_plays.libretro_state.is_v33_candidate",
                  return_value=True),
            patch("anything_plays.libretro_state._checked_native_save_path",
                  side_effect=lambda path: path),
        ):
            with self.assertRaisesRegex(ValueError, "symlinked"):
                item.persist()
        self.assertEqual(outside.read_bytes(), original)

    def test_truncated_unchanged_checkpoint_is_repaired(self):
        item, _ = self.checkpoint()
        item.persist()
        expected = item.path.read_bytes()
        item.path.write_bytes(expected[:-3])
        self.assertTrue(item.persist())
        self.assertEqual(item.path.read_bytes(), expected)
        self.assertFalse(item.persist())
        second, state = self.checkpoint()
        self.assertTrue(second.restore())
        self.assertEqual(state["bytes"], b"GOOD")

    def test_deleted_unchanged_checkpoint_is_recreated(self):
        item, _ = self.checkpoint()
        item.persist()
        item.path.unlink()
        self.assertTrue(item.persist())
        self.assertFalse(item.persist())
        second, state = self.checkpoint()
        self.assertTrue(second.restore())
        self.assertEqual(state["bytes"], b"GOOD")


if __name__ == "__main__":
    unittest.main()
