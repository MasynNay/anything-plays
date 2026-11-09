"""The 3.0 endurance workflow must fail closed on real long-run regressions.

These are Linux headless tests of synthetic webcam/GUI render callbacks
and original GameCube PowerPC homebrew, NOT observed consumer gameplay.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EnduranceCiContracts(unittest.TestCase):
    def test_15_minute_real_tk_loop_is_bounded_and_uploads_evidence(self):
        workflow = (ROOT/".github/workflows/v30-endurance.yml").read_text("utf-8")
        self.assertIn("pull_request:", workflow)
        self.assertIn("branches: [feature/v3.0-unified-test]", workflow)
        self.assertIn("gui-15-minute-soak:", workflow)
        self.assertIn("tests/soak_gui.py --seconds 900 --max-growth-mb 96", workflow)
        self.assertIn("ui-15minute-rss.json", workflow)
        self.assertIn("AnythingPlays-3.0-UI-endurance-evidence", workflow)
        self.assertIn("retention-days:", workflow)
        self.assertIn("timeout-minutes: 20", workflow)

    def test_10_minute_real_gamecube_gpu_pcm_and_controller_effect(self):
        workflow = (ROOT/".github/workflows/v30-endurance.yml").read_text("utf-8")
        self.assertIn("gamecube-10-minute-native-soak:", workflow)
        self.assertIn("devkitpro/devkitppc make", workflow)
        self.assertIn("python tools/fetch_dolphin_sys.py cores", workflow)
        self.assertIn("xvfb-run -a python tools/probe_gamecube_app.py", workflow)
        self.assertIn("--require-animated --require-audio --require-controller-effect --seconds 600", workflow)
        self.assertIn("--max-growth-mb 192", workflow)
        self.assertIn("gamecube-10minute-rss.json", workflow)
        self.assertIn("AnythingPlays-3.0-GameCube-endurance-evidence", workflow)
        code = (ROOT/"tools/probe_gamecube_app.py").read_text("utf-8")
        self.assertIn("controller_effect_required", code)
        self.assertIn("gamecube_button_a_visual_effect_verified", code)
        self.assertIn("native_pcm_nonzero_values", code)
        self.assertIn("native_rss_growth_mb", code)

    def test_strict_failures_no_fake_public_rights_or_retail_gameplay(self):
        workflow = (ROOT/".github/workflows/v30-endurance.yml").read_text("utf-8")
        self.assertIn("No commercial ROM", (ROOT/"tools/probe_gamecube_app.py").read_text("utf-8"))
        self.assertIn("synthetic camera", (ROOT/"tests/soak_gui.py").read_text("utf-8"))
        self.assertNotIn("continue-on-error: true", workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("APPROVED-3.0-DISTRIBUTION", workflow)
        self.assertIn("if: always()", workflow)
        self.assertIn("contents: read", workflow)
        self.assertNotIn("actions/download-artifact", workflow)


if __name__ == "__main__":
    unittest.main()
