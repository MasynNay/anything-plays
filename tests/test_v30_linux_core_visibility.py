"""Regression: unreadable root-owned Dolphin files never crash app startup.

The user encountered a second failure after the initial Linux GameCube
EACCES: on relaunch the stored GameCube profile caused find_dolphin_core
to stat codehandler.bin inside a root-only Sys directory and raise before
Tk could initialize. Verify both core lookup code paths fail closed.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.core_locator import find_core
from anything_plays.gamecube_software import find_dolphin_core


class LinuxDolphinVisibilityTests(unittest.TestCase):
    def test_unreadable_codehandler_never_prevents_gui_startup(self):
        with TemporaryDirectory() as home:
            cores = Path(home) / "cores"
            sys = cores / "dolphin-emu" / "Sys"
            sys.mkdir(parents=True)
            (cores / "dolphin_libretro.so").write_bytes(b"synthetic-test")
            target = sys / "codehandler.bin"
            target.write_bytes(b"synthetic")
            real_stat = Path.stat

            def deny_sys(self, *args, **kwargs):
                if self == target:
                    raise PermissionError(
                        "[Errno 13] Permission denied: " + str(self)
                    )
                return real_stat(self, *args, **kwargs)

            with patch("pathlib.Path.stat", new=deny_sys), patch(
                "anything_plays.core_packs.managed_core_path",
                return_value=None
            ), patch(
                "anything_plays.gamecube_software._search_directories",
                return_value=[cores]
            ), patch(
                "anything_plays.core_locator._search_directories",
                return_value=[cores]
            ):
                self.assertIsNone(find_dolphin_core())
                self.assertIsNone(find_core("gamecube"))
                # It is not correct to silently pretend the emulator works.
                # The UI remains available to show a damaged/missing-core state.

    def test_linux_full_deb_normalizes_special_sys_directory_modes(self):
        source = (Path(__file__).resolve().parents[1] /
                  "packaging" / "build_linux_deb.sh").read_text("utf-8")
        self.assertIn("find dist/AnythingPlays/cores/dolphin-emu -type d", source)
        self.assertIn("-exec chmod u=rwx,g=rx,o=rx,g-s", source)
        self.assertIn("-exec chmod u=rw,g=r,o=r", source)
        self.assertIn("Verified installed root-owned Dolphin Sys", source)


if __name__ == "__main__":
    unittest.main()
