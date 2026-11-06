"""Redundant Linux system-library cleanup safety tests."""
import pathlib
from tempfile import TemporaryDirectory
import unittest

from tools.prune_linux_system_libs import prune_staged_linux_app


class PruneLinuxSystemLibrariesTests(unittest.TestCase):
    def test_removes_only_frozen_platform_libraries(self):
        with TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "AnythingPlays"
            internal = root / "_internal"
            libdir = internal / "python3.13" / "lib-dynload"
            libdir.mkdir(parents=True)
            for name in ("libportaudio.so.2", "libjack.so.0", "libdb-5.3.so",
                         "libasound.so.2", "libreadline.so.8"):
                (internal / name).write_bytes(b"test")
            (libdir / "readline.cpython-313-x86_64-linux-gnu.so").write_bytes(b"test")
            (internal / "libmgba_libretro.so").write_bytes(b"keep")
            (root / "AnythingPlays").write_bytes(b"keep")
            removed = prune_staged_linux_app(root)
            self.assertEqual(len(removed), 6)
            self.assertTrue((internal / "libmgba_libretro.so").exists())
            self.assertTrue((root / "AnythingPlays").exists())
            self.assertEqual(prune_staged_linux_app(root), [])

    def test_rejects_symlinked_candidates(self):
        with TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "AnythingPlays"
            internal = root / "_internal"
            internal.mkdir(parents=True)
            trusted = root / "unchanged"
            trusted.write_bytes(b"keep")
            (internal / "libportaudio.so.2").symlink_to(trusted)
            with self.assertRaisesRegex(ValueError, "symlinked"):
                prune_staged_linux_app(root)
            self.assertEqual(trusted.read_bytes(), b"keep")

    def test_rejects_non_app_directories(self):
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "frozen Linux"):
                prune_staged_linux_app(pathlib.Path(temp))


if __name__ == "__main__":
    unittest.main()
