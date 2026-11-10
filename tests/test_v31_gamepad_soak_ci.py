"""Static contracts for long-running 3.1 SDL gamepad and camera QA."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class V31SdlSoakTests(unittest.TestCase):
    def test_real_gamepad_timer_is_exercised_while_actual_tk_renders(self):
        workflow = (ROOT / ".github/workflows/v31-gamepad-endurance.yml").read_text("utf-8")
        source = (ROOT / "tests/soak_gui.py").read_text("utf-8")
        self.assertIn("tests/soak_gui.py --seconds 180 --enable-gamepad", workflow)
        self.assertIn("SDL_VIDEODRIVER: dummy", workflow)
        self.assertIn("sdl_initialized_samples", workflow)
        self.assertIn("real_controller_hardware_tested", workflow)
        self.assertIn("physical_camera_tested", workflow)
        self.assertIn("enable_gamepad=False", source)
        self.assertIn("app.gamepad_enabled.set(True)", source)
        self.assertIn("SDL controller polling stopped unexpectedly", source)
        self.assertIn('report["sdl_initialized_samples"]', source)

    def test_no_unsafe_approval_or_retail_game_hardware_claim(self):
        workflow = (ROOT / ".github/workflows/v31-gamepad-endurance.yml").read_text("utf-8")
        self.assertIn("if: always()", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("retention-days: 14", workflow)
        for forbidden in ("contents: write", "gh release create",
                          "continue-on-error: true", "softprops/action-gh-release"):
            self.assertNotIn(forbidden, workflow)


if __name__ == "__main__":
    unittest.main()
