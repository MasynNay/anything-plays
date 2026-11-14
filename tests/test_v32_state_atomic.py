"""3.2 native recovery states survive overlapping sessions and failed writes.

Synthetic Neo Geo Pocket Libretro callbacks only: no ROM, real core, camera,
gamepad, network or OS device is opened. Both sessions share the SAME target
checkpoint to exercise the unique-temporary-file boundary.
"""
import ctypes as C
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from anything_plays.libretro_state import LibretroRecoveryState, MAGIC


def fake_native(initial):
    state = {"bytes": initial, "restores": 0}

    def size():
        return len(state["bytes"])

    def serialize(destination, length):
        C.memmove(destination, state["bytes"], length)
        return True

    def restore(source, length):
        state["bytes"] = C.string_at(source, length)
        state["restores"] += 1
        return True

    return SimpleNamespace(library=SimpleNamespace(
        retro_serialize_size=size,
        retro_serialize=serialize,
        retro_unserialize=restore,
    )), state


class V32NativeRecoveryAtomicTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="ap32-recovery-race-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.rom = self.root / "game.ngc"
        self.rom.write_bytes(b"synthetic game identity")
        self.core = self.root / "synthetic-libretro.so"
        self.core.write_bytes(b"synthetic compatible native library identity")
        self.saved = self.root / "user-data"
        self.paths = [
            patch("anything_plays.libretro_save._user_save_directory",
                  return_value=self.saved),
            patch("anything_plays.libretro_state._user_save_directory",
                  return_value=self.saved),
        ]
        for item in self.paths:
            item.start()
            self.addCleanup(item.stop)

    def checkpoint(self, payload):
        native, state = fake_native(payload)
        return LibretroRecoveryState(self.rom, "ngpc", self.core, native), state

    def test_two_checkpoint_writers_never_share_the_same_temp_file(self):
        one, _ = self.checkpoint(b"AAAA")
        two, _ = self.checkpoint(b"BBBB")
        self.assertEqual(one.path, two.path)
        original_replace = os.replace
        gate = threading.Barrier(2)
        seen = []
        lock = threading.Lock()

        def concurrent_replace(source, destination):
            with lock:
                seen.append((Path(source), Path(destination)))
            gate.wait(timeout=10)
            return original_replace(source, destination)

        with patch("anything_plays.libretro_state.os.replace",
                   side_effect=concurrent_replace):
            with ThreadPoolExecutor(max_workers=2) as pool:
                a = pool.submit(one.persist)
                b = pool.submit(two.persist)
                self.assertTrue(a.result(timeout=20))
                self.assertTrue(b.result(timeout=20))

        self.assertEqual(len(seen), 2)
        self.assertEqual(len({source for source, _ in seen}), 2)
        self.assertTrue(all(target == one.path for _, target in seen))
        self.assertTrue(all(
            source.parent == one.path.parent
            and source.name.startswith(one.path.name + ".")
            and source.suffix == ".tmp"
            for source, _ in seen
        ))
        self.assertEqual(list(one.path.parent.glob("*.tmp")), [])
        self.assertTrue(one.path.read_bytes().startswith(MAGIC))
        final, state = self.checkpoint(b"0000")
        self.assertTrue(final.restore())
        self.assertEqual(state["restores"], 1)
        self.assertIn(state["bytes"], (b"AAAA", b"BBBB"))

    def test_failed_replace_does_not_damage_last_good_checkpoint(self):
        good, _ = self.checkpoint(b"GOOD")
        self.assertTrue(good.persist())
        original = good.path.read_bytes()
        next_state, _ = self.checkpoint(b"NEXT")
        with patch("anything_plays.libretro_state.os.replace",
                   side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                next_state.persist()
        self.assertEqual(good.path.read_bytes(), original)
        self.assertEqual(list(good.path.parent.glob("*.tmp")), [])
        restored, value = self.checkpoint(b"0000")
        self.assertTrue(restored.restore())
        self.assertEqual(value["bytes"], b"GOOD")

    def test_old_fixed_temp_symlink_is_not_touched(self):
        checkpoint, _ = self.checkpoint(b"SAFE")
        checkpoint.path.parent.mkdir(parents=True)
        untouched = self.root / "unrelated-private-file"
        untouched.write_bytes(b"KEEP")
        old_temp = checkpoint.path.with_suffix(".apstate.tmp")
        try:
            old_temp.symlink_to(untouched)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable on this runner")
        self.assertTrue(checkpoint.persist())
        self.assertEqual(untouched.read_bytes(), b"KEEP")
        self.assertTrue(old_temp.is_symlink())
        self.assertEqual(list(checkpoint.path.parent.glob("*.tmp")),
                         [old_temp])

    def test_unchanged_state_does_not_rewrite_thousands_of_checkpoints(self):
        item, _ = self.checkpoint(b"CONSISTENT")
        native_replace = os.replace
        published = []

        def replace(source, destination):
            published.append(Path(source))
            return native_replace(source, destination)

        with patch("anything_plays.libretro_state.os.replace",
                   side_effect=replace):
            self.assertTrue(item.persist())
            for _ in range(1500):
                self.assertFalse(item.persist())
        self.assertEqual(len(published), 1)
        self.assertEqual(list(item.path.parent.glob("*.tmp")), [])
        reloaded, value = self.checkpoint(b"0000000000")
        self.assertTrue(reloaded.restore())
        self.assertEqual(value["bytes"], b"CONSISTENT")


if __name__ == "__main__":
    unittest.main()
