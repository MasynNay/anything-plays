"""GameCube worker failures must not publish native driver or ROM paths."""
import unittest
from unittest.mock import Mock, patch

from anything_plays.gba_emulator import (
    Emulator, safe_gamecube_worker_error,
)


class GameCubeWorkerErrorPrivacyTests(unittest.TestCase):
    def test_error_categories_discard_native_gpu_paths_and_device_strings(self):
        faults = (
            OSError("/Users/private/ROMs/my-game.iso"),
            RuntimeError("/home/private/devices/camera serial 9982"),
            MemoryError("GPU device secret hardware address"),
            FileNotFoundError("private Dolphin core location"),
            ValueError("driver token: SECRET-123"),
        )
        for failure in faults:
            with self.subTest(error=type(failure).__name__):
                shown = safe_gamecube_worker_error(failure)
                self.assertIn("GameCube native playback failed", shown)
                self.assertIn(type(failure).__name__, shown)
                for secret in ("private", "SECRET", "/Users/", "/home/",
                               "9982", "my-game.iso"):
                    self.assertNotIn(secret, shown)
        class PrivateDriverException(Exception):
            pass
        self.assertEqual(
            safe_gamecube_worker_error(
                PrivateDriverException("device-serial SECRET-XYZ")
            ),
            "GameCube native playback failed (UnexpectedError).",
        )

    def test_safe_actionable_known_gpu_errors_never_reflect_extra_text(self):
        self.assertEqual(
            safe_gamecube_worker_error(
                RuntimeError(
                    "GameCube needs a graphics driver supporting OpenGL 3.3 "
                    "or newer. PRIVATE device serial /home/a"
                )
            ),
            "GameCube needs a GPU driver with OpenGL 3.3 or newer. "
            "Install or update the graphics driver and restart Anything Plays.",
        )
        self.assertEqual(
            safe_gamecube_worker_error(
                RuntimeError("GPU hardware context negotiation failed")
            ),
            "GameCube GPU hardware context negotiation failed.",
        )
        self.assertEqual(
            safe_gamecube_worker_error(
                RuntimeError("GPU readback failed (OSError)")
            ),
            "GameCube GPU readback failed (OSError).",
        )
        self.assertEqual(
            safe_gamecube_worker_error(
                RuntimeError("GPU readback failed (OSError) /home/a")
            ),
            "GameCube native playback failed (RuntimeError).",
        )
        self.assertEqual(
            safe_gamecube_worker_error(
                RuntimeError(
                    "Dolphin did not register a supported accelerated render context"
                )
            ),
            "GameCube could not initialize the accelerated GPU context.",
        )

    def test_actual_emulator_worker_discards_private_driver_message(self):
        emu = Emulator()
        emu.system = "gamecube"
        emu.rom = "/home/owner/private-game.iso"
        emu.core_path = "/home/owner/private-dolphin.so"
        failure = RuntimeError(
            "GPU driver serial PRIVATE-ABCD at /dev/dri/renderD128"
        )
        session = Mock()
        session.run.side_effect = failure
        session.performance_snapshot.return_value = {
            "format": "anything-plays-gamecube-performance",
            "version": 1,
        }
        with patch(
            "anything_plays.gamecube_gpu.GameCubeHardwareSession",
            return_value=session,
        ):
            emu._run()
        self.assertEqual(
            emu.last_error, "GameCube native playback failed (RuntimeError)."
        )
        self.assertEqual(emu.error, emu.last_error)
        self.assertNotIn("/dev/dri", emu.error)
        self.assertNotIn("PRIVATE", emu.error)
        self.assertFalse(emu.running)
        self.assertFalse(emu.launching)
        self.assertIsNone(emu._gamecube_session)
        self.assertIsNotNone(emu._gamecube_last_performance)

    def test_worker_constructor_failure_is_also_redacted(self):
        emu = Emulator()
        emu.system = "gamecube"
        with patch(
            "anything_plays.gamecube_gpu.GameCubeHardwareSession",
            side_effect=OSError(
                "private native library /Users/owner/ROMs/Secret.iso"
            ),
        ):
            emu._run()
        self.assertEqual(
            emu.last_error, "GameCube native playback failed (OSError)."
        )
        self.assertIsNone(emu._gamecube_session)
        self.assertFalse(emu.running)

    def test_other_console_worker_errors_are_not_changed(self):
        emu = Emulator()
        emu.system = "gba"
        with patch(
            "anything_plays.gba_emulator.CoreSession",
            side_effect=RuntimeError("legacy message"),
        ):
            emu._run()
        self.assertEqual(emu.last_error, "RuntimeError: legacy message")
        self.assertEqual(emu.error, emu.last_error)


if __name__ == "__main__":
    unittest.main()
