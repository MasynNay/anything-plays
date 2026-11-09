"""GameCube hardware test must prove original PowerPC game responds to A."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]


class GameCubeControllerFeedbackContracts(unittest.TestCase):
    def test_native_game_uses_actual_pad_a_to_change_gpu_clear_color(self):
        code = (ROOT / "tools/gamecube-3d-homebrew/source/main.c").read_text()
        self.assertIn("PAD_ScanPads()", code)
        self.assertIn("PAD_ButtonsHeld(0)", code)
        self.assertIn("PAD_BUTTON_A", code)
        self.assertIn("GX_SetCopyClear((held & PAD_BUTTON_A)", code)
        self.assertIn("{18, 190, 42, 255}", code)

    def test_probe_requires_actual_pixels_not_just_nonzero_poll(self):
        code = (ROOT / "tools/probe_gamecube_app.py").read_text()
        for required in (
            "native_controller_active_green_frames",
            "native_controller_idle_dark_frames",
            "gamecube_button_a_visual_effect_verified",
            "controller_effect_required",
            "--require-controller-effect",
            "and (not require_controller_effect or controller_effect_ok)",
        ):
            self.assertIn(required, code)
        workflow = (ROOT / ".github/workflows/v30-lab.yml").read_text()
        job = workflow.split("  gamecube-original-gx3d-gpu-playback:",1)[1].split(
            "  gamecube-original-gx3d-windows:",1)[0]
        self.assertIn("--require-controller-effect", job)
        self.assertIn("--require-audio", job)
        self.assertIn("--require-animated", job)


if __name__ == "__main__":
    unittest.main()
