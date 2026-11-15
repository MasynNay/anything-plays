"""3.2 game-save persistence through 30 minutes of VIRTUAL checkpoints.

No real time passes and no native emulator, camera, controller or retail ROM
is used. At a hypothetical 60 FPS this advances 108,000 virtual frames,
checkpointing every 300 frames as CoreSession.run does. Every save uses the
isolated private preview store; stable ROM-adjacent progress must remain
byte-for-byte unchanged across restarts and a simulated interrupted write.
"""

import ctypes as C
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from anything_plays.libretro_save import SaveRAM


VIRTUAL_FRAMES = 30 * 60 * 60
CHECKPOINT_FRAMES = 300


class PreviewVirtualEnduranceTests(unittest.TestCase):
    def test_virtual_half_hour_and_restarts_keep_stable_progress_untouched(self):
        with tempfile.TemporaryDirectory(prefix="ap32-virtual-endurance-") as tmp:
            home = Path(tmp)
            rom = home / "games" / "sample.gba"
            rom.parent.mkdir()
            rom.write_bytes(b"only a dummy ROM filename; no game executed")
            stable = rom.with_suffix(".sav")
            stable_canary = b"REAL_STABLE_PROGRESS"
            stable.write_bytes(stable_canary)

            env = {
                "XDG_DATA_HOME": str(home / "data"),
                "APPDATA": str(home / "roaming"),
            }
            with patch.dict(os.environ, env), patch(
                "anything_plays.libretro_save.Path.home", return_value=home,
            ), patch(
                "anything_plays.libretro_save.is_v32_preview",
                return_value=True,
            ):
                memory = C.create_string_buffer(8)

                def save_session():
                    return SaveRAM(
                        rom, lambda _kind: C.addressof(memory),
                        lambda _kind: 8,
                    )

                sav = save_session()
                count_written = 0
                count_skipped = 0
                count_restarts = 0
                expected = None
                for virtual_frame in range(
                    0, VIRTUAL_FRAMES + 1, CHECKPOINT_FRAMES,
                ):
                    if virtual_frame % 1200 == 0:
                        expected = virtual_frame.to_bytes(8, "little")
                        memory.raw = expected
                    if sav.persist():
                        count_written += 1
                    else:
                        count_skipped += 1
                    if virtual_frame and virtual_frame % 18000 == 0:
                        memory.raw = b"\0" * 8
                        sav = save_session()
                        sav.restore()
                        self.assertEqual(memory.raw, expected)
                        count_restarts += 1
                    if virtual_frame % 9000 == 0:
                        self.assertEqual(stable.read_bytes(), stable_canary)
                        self.assertEqual(sav.path.read_bytes(), expected)
                        self.assertEqual(
                            list(sav.path.parent.glob("*.tmp")), [],
                        )
                self.assertEqual(count_restarts, 6)
                self.assertGreater(count_written, 75)
                self.assertGreater(count_skipped, 250)
                self.assertEqual(stable.read_bytes(), stable_canary)
                self.assertEqual(sav.path.read_bytes(), expected)
                self.assertTrue(sav.path.is_relative_to(home))

    def test_failed_preview_checkpoint_preserves_prior_complete_sram(self):
        with tempfile.TemporaryDirectory(prefix="ap32-save-retry-") as tmp:
            home = Path(tmp)
            rom = home / "game.gbc"
            rom.write_bytes(b"dummy game")
            legacy = rom.with_suffix(".sav")
            legacy.write_bytes(b"STABLE")
            with patch.dict(os.environ, {
                "XDG_DATA_HOME": str(home / "data"),
                "APPDATA": str(home / "roaming"),
            }), patch(
                "anything_plays.libretro_save.Path.home", return_value=home,
            ), patch(
                "anything_plays.libretro_save.is_v32_preview",
                return_value=True,
            ):
                memory = C.create_string_buffer(b"FIRST!", 6)
                sav = SaveRAM(
                    rom, lambda _kind: C.addressof(memory),
                    lambda _kind: 6,
                )
                self.assertTrue(sav.persist())
                memory.raw = b"SECOND"
                with patch("anything_plays.libretro_save.os.replace",
                           side_effect=OSError("simulated write interruption")):
                    with self.assertRaisesRegex(OSError, "interruption"):
                        sav.persist()
                self.assertEqual(sav.path.read_bytes(), b"FIRST!")
                self.assertEqual(legacy.read_bytes(), b"STABLE")
                self.assertEqual(list(sav.path.parent.glob("*.tmp")), [])
                self.assertTrue(sav.persist())
                self.assertEqual(sav.path.read_bytes(), b"SECOND")
                memory.raw = b"\0" * 6
                fresh = SaveRAM(
                    rom, lambda _kind: C.addressof(memory),
                    lambda _kind: 6,
                )
                fresh.restore()
                self.assertEqual(memory.raw, b"SECOND")
                self.assertEqual(legacy.read_bytes(), b"STABLE")


if __name__ == "__main__":
    unittest.main()
