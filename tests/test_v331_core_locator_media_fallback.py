"""3.3.1: an unreadable core directory cannot block packaged emulator startup.

All candidates are tiny, non-executable local placeholder files. No native
emulator library, network drive, ROM, controller, camera or GUI is used.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.core_locator import find_core


class CoreLocatorMediaRecoveryTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.first = self.root / "unreadable-install"
        self.second = self.root / "healthy-install"
        self.first.mkdir()
        self.second.mkdir()

    def _locate(self, system="gba"):
        with patch("anything_plays.core_locator._search_directories",
                   return_value=[self.first, self.second]), patch(
                       "anything_plays.core_locator._library_extension",
                       return_value=".so"
                   ), patch(
                       "anything_plays.core_packs.managed_core_path",
                       return_value=None
                   ):
            return find_core(system)

    @staticmethod
    def _place(folder, filename):
        path = folder / filename
        path.write_bytes(b"tiny synthetic placeholder")
        return path

    def test_regular_first_packaged_core_still_wins(self):
        first = self._place(self.first, "mgba_libretro.so")
        self._place(self.second, "mgba_libretro.so")
        self.assertEqual(self._locate(), str(first))

    def test_corrupt_first_mount_probe_allows_healthy_later_directory(self):
        unhealthy = self._place(self.first, "mgba_libretro.so")
        healthy = self._place(self.second, "mgba_libretro.so")
        original = Path.is_file

        def broken_stat(path):
            if path == unhealthy:
                raise OSError("PRIVATE disconnected mount /home/person")
            return original(path)

        with patch.object(Path, "is_file", broken_stat):
            self.assertEqual(self._locate(), str(healthy))

    def test_unreadable_first_alias_allows_second_filename_same_folder(self):
        first = self._place(self.first, "mgba_libretro.so")
        alias = self._place(self.first, "libretro_mgba.so")
        original = Path.is_file

        def broken_probe(path):
            if path == first:
                raise PermissionError("PRIVATE damaged file ACL")
            return original(path)

        with patch.object(Path, "is_file", broken_probe):
            self.assertEqual(self._locate(), str(alias))

    def test_two_unreadable_names_do_not_hide_healthy_bundled_core(self):
        self._place(self.first, "mgba_libretro.so")
        self._place(self.first, "libretro_mgba.so")
        healthy = self._place(self.second, "mgba_libretro.so")
        original = Path.is_file

        def removed_media(path):
            if path.parent == self.first:
                raise OSError("PRIVATE network share offline")
            return original(path)

        with patch.object(Path, "is_file", removed_media):
            self.assertEqual(self._locate(), str(healthy))

    def test_all_missing_or_unreadable_candidates_return_none(self):
        self._place(self.first, "mgba_libretro.so")
        original = Path.is_file

        def unavailable(path):
            if path.parent == self.first:
                raise OSError("PRIVATE drive unplugged")
            return original(path)

        with patch.object(Path, "is_file", unavailable):
            self.assertIsNone(self._locate())

    def test_dolphin_incomplete_sys_skips_that_candidate(self):
        self._place(self.first, "dolphin_libretro.so")
        healthy = self._place(self.second, "dolphin_libretro.so")
        sys_file = self.second / "dolphin-emu" / "Sys" / "codehandler.bin"
        sys_file.parent.mkdir(parents=True)
        sys_file.write_bytes(b"synthetic-codehandler-not-native")
        self.assertEqual(self._locate("gamecube"), str(healthy))

    def test_dolphin_sys_stat_error_allows_later_valid_directory(self):
        self._place(self.first, "dolphin_libretro.so")
        bad_sys = self.first / "dolphin-emu" / "Sys" / "codehandler.bin"
        bad_sys.parent.mkdir(parents=True)
        bad_sys.write_bytes(b"unreadable")
        healthy = self._place(self.second, "dolphin_libretro.so")
        good_sys = self.second / "dolphin-emu" / "Sys" / "codehandler.bin"
        good_sys.parent.mkdir(parents=True)
        good_sys.write_bytes(b"valid")
        original = Path.stat

        def failed_sys_stat(path, *args, **kwargs):
            if path == bad_sys:
                raise OSError("PRIVATE USB Sys data went missing")
            return original(path, *args, **kwargs)

        with patch.object(Path, "stat", failed_sys_stat):
            self.assertEqual(self._locate("gamecube"), str(healthy))

    def test_unknown_console_still_fails_closed(self):
        with self.assertRaises(KeyError):
            self._locate("not-a-console")

    def test_managed_core_still_precedes_bundled_candidates(self):
        self._place(self.first, "mgba_libretro.so")
        with patch("anything_plays.core_locator._search_directories",
                   side_effect=AssertionError("do not scan when managed")), patch(
                       "anything_plays.core_packs.managed_core_path",
                       return_value="/approved/managed-mgba.so"
                   ):
            self.assertEqual(find_core("gba"), "/approved/managed-mgba.so")


if __name__ == "__main__":
    unittest.main()
