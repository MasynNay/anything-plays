"""Regression: Linux GameCube must not write root-owned /opt Dolphin Sys.

The original user report is EACCES:
  /opt/anything-plays-30-preview/cores/dolphin-emu/Sys/codehandler.bin

All fixtures are synthetic; tests never require a commercial ROM, GPU or
root access. They verify real Libretro GET_SYSTEM_DIRECTORY behavior.
"""
import ctypes as C
import os
from pathlib import Path
import stat
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.gamecube_sys import writable_dolphin_system_directory
from anything_plays.gba_emulator import CoreSession


def fixture(root):
    root = Path(root)
    core = root / "opt" / "anything-plays-30-preview" / "cores"
    sysdir = core / "dolphin-emu" / "Sys"
    (sysdir / "GC").mkdir(parents=True)
    (sysdir / "GameSettings").mkdir()
    (sysdir / "codehandler.bin").write_bytes(b"immutable-gecko-codehandler")
    (sysdir / "GC" / "font_western.bin").write_bytes(b"font")
    (sysdir / "GameSettings" / "test.ini").write_bytes(b"setting")
    (core / "dolphin_libretro.so").write_bytes(b"fake-native-header")
    for item in sysdir.rglob("*"):
        if item.is_file():
            item.chmod(0o444)
    return core / "dolphin_libretro.so", sysdir


class LinuxDolphinWritableSystemTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux-only native file lock")
    def test_linux_core_receives_user_writable_sys_not_opt(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            core, source = fixture(root)
            user = root / "user" / "share" / "anything-plays" / "saves"
            with patch("anything_plays.gamecube_sys.sys.platform", "linux"), patch(
                "anything_plays.gamecube_sys._user_save_directory",
                return_value=user,
            ), patch(
                "anything_plays.gba_emulator.native_core_save_directory",
                return_value=root / "user" / "gamecube-cards",
            ):
                session = CoreSession(None, "gamecube", root / "game.iso", str(core))
                try:
                    pointer = C.c_char_p()
                    self.assertTrue(session.environment(
                        9, C.cast(C.pointer(pointer), C.c_void_p)))
                    actual = Path(os.fsdecode(pointer.value))
                    self.assertEqual(actual.parent, user.parent / "dolphin-system")
                    self.assertNotIn("/opt/", str(actual))
                    target = actual / "dolphin-emu" / "Sys" / "codehandler.bin"
                    self.assertEqual(target.read_bytes(), b"immutable-gecko-codehandler")
                    self.assertTrue(stat.S_IMODE(target.stat().st_mode) & stat.S_IWUSR)
                    # Native Dolphin needs writable codehandler.bin at boot.
                    with target.open("r+b") as f:
                        self.assertEqual(f.read(9), b"immutable")
                        f.seek(0)
                        f.write(b"runtime")
                    self.assertEqual((source / "codehandler.bin").read_bytes(),
                                     b"immutable-gecko-codehandler")
                    self.assertFalse(stat.S_IMODE(
                        (source / "codehandler.bin").stat().st_mode) & stat.S_IWUSR)
                    save = C.c_char_p()
                    self.assertTrue(session.environment(
                        31, C.cast(C.pointer(save), C.c_void_p)))
                    self.assertEqual(Path(os.fsdecode(save.value)),
                                     root / "user" / "gamecube-cards")
                finally:
                    session.audio.close()

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux-only native file lock")
    def test_cached_sys_is_reused_and_tampering_repaired(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            core, source = fixture(root)
            with patch("anything_plays.gamecube_sys.sys.platform", "linux"), patch(
                "anything_plays.gamecube_sys._user_save_directory",
                return_value=root / "user" / "saves",
            ):
                first = writable_dolphin_system_directory(core)
                second = writable_dolphin_system_directory(core)
                self.assertEqual(first, second)
                code = first / "dolphin-emu" / "Sys" / "codehandler.bin"
                code.write_bytes(b"damaged")
                third = writable_dolphin_system_directory(core)
                self.assertEqual(third, first)
                self.assertEqual(code.read_bytes(), (source / "codehandler.bin").read_bytes())
                self.assertEqual(sorted(p.name for p in first.parent.iterdir()
                                        if p.is_dir()), [first.name])

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux-only native file lock")
    def test_missing_and_symlinked_sys_fail_closed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            core, source = fixture(root)
            with patch("anything_plays.gamecube_sys.sys.platform", "linux"), patch(
                "anything_plays.gamecube_sys._user_save_directory",
                return_value=root / "user" / "saves",
            ):
                (source / "GC" / "link").symlink_to(source / "codehandler.bin")
                with self.assertRaisesRegex(ValueError, "symbolic links"):
                    writable_dolphin_system_directory(core)
                (source / "GC" / "link").unlink()
                (source / "codehandler.bin").unlink()
                with self.assertRaisesRegex(ValueError, "codehandler"):
                    writable_dolphin_system_directory(core)

    def test_other_operating_systems_keep_packaged_sys(self):
        with TemporaryDirectory() as tmp:
            core, source = fixture(tmp)
            for platform in ("darwin", "win32"):
                with self.subTest(platform=platform), patch(
                    "anything_plays.gamecube_sys.sys.platform", platform
                ):
                    self.assertEqual(
                        writable_dolphin_system_directory(core),
                        core.parent.resolve(),
                    )


if __name__ == "__main__":
    unittest.main()
