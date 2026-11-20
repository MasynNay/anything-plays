"""GameCube save warnings never expose local ROMs or private filesystem paths.

No native emulator, audio hardware, ROM bytes, or external device required.
"""
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from anything_plays.gba_emulator import CoreSession


PRIVATE = "/Users/private/ROMs/family-game.iso"


def fake_progress_session(system="gamecube"):
    session = CoreSession.__new__(CoreSession)
    session.system = system
    session.emulator = SimpleNamespace(save_warning=None)
    session.save_ram = None
    session.recovery_state = None
    return session


class GameCubeSaveWarningPrivacyTests(unittest.TestCase):
    def test_periodic_sram_failure_preserves_gameplay_and_redacts_path(self):
        session = fake_progress_session()
        session.save_ram = Mock()
        session.save_ram.persist.side_effect = OSError(
            "Permission denied: " + PRIVATE
        )
        self.assertFalse(session.persist_game_progress())
        session.save_ram.persist.assert_called_once()
        self.assertIn("GameCube battery save unavailable",
                      session.emulator.save_warning)
        self.assertIn("still running", session.emulator.save_warning)
        self.assertNotIn("private", session.emulator.save_warning)
        self.assertNotIn("family-game.iso", session.emulator.save_warning)

    def test_recovery_failure_cannot_hide_successful_sram_persistence(self):
        session = fake_progress_session()
        session.save_ram = Mock()
        session.save_ram.persist.return_value = True
        session.recovery_state = Mock()
        session.recovery_state.persist.side_effect = RuntimeError(
            "private recovery data /home/owner/.config/anything-plays"
        )
        self.assertTrue(session.persist_game_progress())
        session.recovery_state.persist.assert_called_once()
        self.assertIn("GameCube recovery save unavailable",
                      session.emulator.save_warning)
        self.assertNotIn("/home/", session.emulator.save_warning)

    def test_bad_native_exception_stringification_is_never_needed(self):
        class MalformedSaveError(OSError):
            def __str__(self):
                raise RuntimeError("PRIVATE path from broken driver")
        session = fake_progress_session()
        session.save_ram = Mock()
        session.save_ram.persist.side_effect = MalformedSaveError()
        self.assertFalse(session.persist_game_progress())
        self.assertIn("GameCube battery save unavailable",
                      session.emulator.save_warning)

    def test_existing_legacy_console_error_format_is_unchanged(self):
        session = fake_progress_session("gba")
        session.save_ram = Mock()
        session.save_ram.persist.side_effect = OSError("legacy disk write")
        self.assertFalse(session.persist_game_progress())
        self.assertEqual(
            session.emulator.save_warning,
            "Battery save failed; game is still running: legacy disk write",
        )
        session.recovery_state = Mock()
        session.recovery_state.persist.side_effect = OSError("legacy state")
        session.save_ram.persist.return_value = False
        session.save_ram.persist.side_effect = None
        self.assertFalse(session.persist_game_progress())
        self.assertEqual(
            session.emulator.save_warning,
            "Recovery save failed; game is still running: legacy state",
        )
        self.assertEqual(
            session._save_failure_warning("fixed", "Could not restore saved game: ",
                                          OSError("legacy restore")),
            "Could not restore saved game: legacy restore",
        )

    def test_actual_core_worker_restore_failure_does_not_display_rom_path(self):
        with TemporaryDirectory() as folder:
            core = Path(folder) / "synthetic-dolphin.so"
            core.write_bytes(b"placeholder; native library is mocked")
            emulator = SimpleNamespace(
                inputs=Mock(),
                stop_event=threading.Event(),
                audio_sink=None,
                audio_warning=None,
                save_warning=None,
                running=False,
                launching=True,
                armed=False,
            )
            emulator.stop_event.set()  # Exercise startup/restore, no run loop.
            session = CoreSession.__new__(CoreSession)
            session.system = "gamecube"
            session.core_path = str(core)
            session.emulator = emulator
            session.native = None
            session.audio = Mock(output_error=None)
            session.rom = Path(PRIVATE)
            session.save_ram = None
            session.recovery_state = None
            session.enable_state_resume = False
            session._load_game = Mock()
            session.persist_game_progress = Mock(return_value=False)
            native = Mock()
            save = Mock()
            save.restore.side_effect = PermissionError(
                "Cannot read local save: " + PRIVATE
            )
            with (
                patch("anything_plays.gba_emulator.NativeCore",
                      return_value=native),
                patch("anything_plays.gba_emulator.SaveRAM",
                      return_value=save),
            ):
                session.run()
            native.init.assert_called_once()
            native.close.assert_called_once()
            session.audio.close.assert_called_once()
            save.restore.assert_called_once()
            self.assertTrue(emulator.save_warning.startswith(
                "GameCube saved game could not be restored"
            ))
            self.assertNotIn(PRIVATE, emulator.save_warning)
            self.assertNotIn("private", emulator.save_warning)
            self.assertFalse(emulator.launching)
            self.assertIsNone(emulator.audio_sink)


if __name__ == "__main__":
    unittest.main()
