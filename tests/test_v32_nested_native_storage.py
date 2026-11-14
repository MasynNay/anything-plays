"""3.2 preview native cores must never follow nested save-folder redirects.

This protects the *full-library* NGP/GameCube save contracts in advance of
their native-core license review. The current installer remains mGBA-only.
All test files are synthetic, stored under a disposable temporary directory.
"""

import ctypes as C
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from anything_plays.libretro_save import (
    _user_save_directory, native_core_save_directory,
)
from anything_plays.libretro_state import (
    LibretroRecoveryState, state_file_path,
)


def fake_native():
    image = b"SAFE"

    def size():
        return len(image)

    def serialize(destination, length):
        C.memmove(destination, image, length)
        return True

    def unserialize(_source, _length):
        raise AssertionError("Untrusted recovery state reached the native core")

    return SimpleNamespace(library=SimpleNamespace(
        retro_serialize_size=size,
        retro_serialize=serialize,
        retro_unserialize=unserialize,
    ))


class PreviewNestedSaveIsolationTests(unittest.TestCase):
    def make_symlink(self, destination, link):
        try:
            link.symlink_to(destination, target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"Native symlink support unavailable: {exc}")

    def test_native_core_redirects_are_rejected_on_each_desktop_os(self):
        for platform in ("linux", "darwin", "win32"):
            with self.subTest(platform=platform):
                with tempfile.TemporaryDirectory(prefix="ap32-native-path-") as tmp:
                    home = Path(tmp)
                    rom = home / "own-game.ngc"
                    rom.write_bytes(b"synthetic ROM file")
                    stable = home / "public-save-location"
                    stable.mkdir()
                    (stable / "canary").write_bytes(b"STABLE")
                    env = {
                        "XDG_DATA_HOME": str(home / "data"),
                        "APPDATA": str(home / "roaming"),
                    }
                    with patch.dict(os.environ, env), patch(
                        "anything_plays.libretro_save.sys.platform", platform,
                    ), patch(
                        "anything_plays.libretro_save.Path.home",
                        return_value=home,
                    ), patch(
                        "anything_plays.libretro_save.is_v32_preview",
                        return_value=True,
                    ):
                        for relative, consumer in (
                            ("native-core", "ngpc"),
                            ("native-core/neo-geo-pocket", "ngpc"),
                            ("native-core", "gamecube"),
                            ("native-core/gamecube", "gamecube"),
                            ("native-core/resume", "resume"),
                        ):
                            with self.subTest(path=relative, consumer=consumer):
                                save_root = _user_save_directory()
                                link = save_root / relative
                                # Every scenario starts without a previous
                                # linked subtree, so failure cannot be
                                # attributed to a different path component.
                                if (save_root / "native-core").is_symlink():
                                    (save_root / "native-core").unlink()
                                link.parent.mkdir(parents=True, exist_ok=True)
                                self.make_symlink(stable, link)
                                with self.assertRaisesRegex(
                                    ValueError, "must not link",
                                ):
                                    if consumer == "resume":
                                        state_file_path(rom, "ngpc")
                                    else:
                                        native_core_save_directory(rom, consumer)
                                link.unlink()
                        self.assertEqual(
                            (stable / "canary").read_bytes(), b"STABLE"
                        )
                        self.assertEqual(list(stable.iterdir()),
                                         [stable / "canary"])

    def test_replacing_resume_parent_after_construction_is_detected(self):
        with tempfile.TemporaryDirectory(prefix="ap32-resume-parent-") as tmp:
            home = Path(tmp)
            rom = home / "own-game.ngc"
            core = home / "mock-core.so"
            rom.write_bytes(b"synthetic game identity")
            core.write_bytes(b"synthetic native core identity")
            old = home / "published-save-data"
            old.mkdir()
            canary = old / "old-data"
            canary.write_bytes(b"DO NOT TOUCH")
            with patch.dict(os.environ, {
                "XDG_DATA_HOME": str(home / "data"),
                "APPDATA": str(home / "roaming"),
            }), patch("anything_plays.libretro_save.Path.home",
                     return_value=home), patch(
                         "anything_plays.libretro_save.is_v32_preview",
                         return_value=True,
                     ), patch(
                         "anything_plays.libretro_state.is_v32_preview",
                         return_value=True,
                     ):
                state = LibretroRecoveryState(
                    rom, "ngpc", core, fake_native(),
                )
                state.path.parent.mkdir(parents=True)
                resume_dir = state.path.parent
                resume_dir.rmdir()
                self.make_symlink(old, resume_dir)
                with self.assertRaisesRegex(ValueError, "must not link"):
                    state.persist()
                with self.assertRaisesRegex(ValueError, "must not link"):
                    state.restore()
                self.assertEqual(canary.read_bytes(), b"DO NOT TOUCH")
                self.assertEqual(list(old.iterdir()), [canary])

    def test_hardlinked_preview_resume_is_never_read_or_replaced(self):
        with tempfile.TemporaryDirectory(prefix="ap32-state-hardlink-") as tmp:
            home = Path(tmp)
            rom = home / "own-game.ngc"
            core = home / "mock-core.so"
            rom.write_bytes(b"synthetic game identity")
            core.write_bytes(b"synthetic core identity")
            stable = home / "stable-backup.apstate"
            stable.write_bytes(b"STABLE CHECKPOINT BYTES")
            with patch.dict(os.environ, {
                "XDG_DATA_HOME": str(home / "data"),
                "APPDATA": str(home / "roaming"),
            }), patch("anything_plays.libretro_save.Path.home",
                     return_value=home), patch(
                         "anything_plays.libretro_save.is_v32_preview",
                         return_value=True,
                     ), patch(
                         "anything_plays.libretro_state.is_v32_preview",
                         return_value=True,
                     ):
                state = LibretroRecoveryState(
                    rom, "ngpc", core, fake_native(),
                )
                state.path.parent.mkdir(parents=True)
                try:
                    os.link(stable, state.path)
                except OSError as exc:
                    self.skipTest(f"Hard links unavailable: {exc}")
                with self.assertRaisesRegex(ValueError, "share a stable file"):
                    state.restore()
                with self.assertRaisesRegex(ValueError, "share a stable file"):
                    state.persist()
                self.assertEqual(stable.read_bytes(), b"STABLE CHECKPOINT BYTES")
                self.assertEqual(state.path.read_bytes(), stable.read_bytes())

    def test_stable_native_save_directory_contract_is_unchanged(self):
        with tempfile.TemporaryDirectory(prefix="ap32-stable-compat-") as tmp:
            root = Path(tmp)
            with patch(
                "anything_plays.libretro_save._user_save_directory",
                return_value=root / "stable-data",
            ), patch(
                "anything_plays.libretro_save.is_v32_preview",
                return_value=False,
            ):
                gamecube = native_core_save_directory(
                    root / "game.iso", "gamecube",
                )
                pocket = native_core_save_directory(
                    root / "own-game.ngc", "ngpc",
                )
                self.assertEqual(
                    gamecube, root / "stable-data" / "native-core" / "gamecube",
                )
                self.assertEqual(
                    pocket.parent.name, "neo-geo-pocket",
                )


if __name__ == "__main__":
    unittest.main()
