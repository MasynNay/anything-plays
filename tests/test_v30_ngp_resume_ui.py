"""A real restored Pocket session must be visible in the game UI.

Exercise the actual GameplayMixin.tick without constructing a Tk window,
webcam, or emulation core. Native verification happens independently in CI.
"""
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from anything_plays.ui_gameplay import GameplayMixin


class PocketResumeStatusTests(unittest.TestCase):
    def test_recovery_confirmation_survives_refresh_and_then_returns_to_playing(self):
        status = {"message": ""}

        def set_status(value):
            status["message"] = value

        game = SimpleNamespace(
            _closing=False,
            cap=None,
            frame=None,
            reference_image=None,
            current_rom="/roms/StarGunner.ngc",
            emu=SimpleNamespace(
                error=None, save_warning=None, audio_warning=None,
                resume_info="Restored the last verified Neo Geo Pocket session.",
                running=True,
            ),
            game_status=SimpleNamespace(
                set=set_status, get=lambda: status["message"],
            ),
            root=SimpleNamespace(after=Mock(return_value=42)),
        )
        GameplayMixin.tick(game)
        self.assertIn("Restored the last verified", status["message"])
        self.assertIsNone(game.emu.resume_info)
        self.assertGreater(game._save_warning_until, time.monotonic())

        GameplayMixin.tick(game)
        self.assertIn("Restored the last verified", status["message"])
        game._save_warning_until = 0
        GameplayMixin.tick(game)
        self.assertEqual(status["message"], "Playing StarGunner")
        self.assertEqual(game.root.after.call_count, 3)

    def test_real_save_errors_take_priority_over_resume_notification(self):
        status = {"message": ""}
        game = SimpleNamespace(
            _closing=False, cap=None, frame=None,
            reference_image=None, current_rom="/roms/StarGunner.ngc",
            emu=SimpleNamespace(
                error=None, save_warning="Native save failed",
                audio_warning=None, resume_info="Recovered game",
                running=True,
            ),
            game_status=SimpleNamespace(
                set=lambda value: status.update(message=value),
                get=lambda: status["message"],
            ),
            root=SimpleNamespace(after=Mock()),
        )
        GameplayMixin.tick(game)
        self.assertEqual(status["message"], "Native save failed")
        self.assertEqual(game.emu.resume_info, "Recovered game")


if __name__ == "__main__":
    unittest.main()
