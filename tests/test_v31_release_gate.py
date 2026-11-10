"""Release gate rejects mGBA-only previews, missing hardware, and missing rights."""
import json
from pathlib import Path
import unittest
from tools.check_v31_release import blockers, FILE, REQUIRED_GATES


class V31ReleaseGateTests(unittest.TestCase):
    def test_public_3_1_is_explicitly_blocked_by_evidence_not_yet_available(self):
        report = json.loads(FILE.read_text("utf-8"))
        self.assertEqual(report["status"], "IN_DEVELOPMENT")
        self.assertIs(report["public_release_approved"], False)
        self.assertEqual(set(report["release_gates"]), set(REQUIRED_GATES))
        self.assertEqual(len(blockers(report)), 7)
        for name in REQUIRED_GATES:
            self.assertIn(name, blockers(report))

    def test_missing_licensing_and_hardware_cannot_be_waved_through(self):
        report = json.loads(FILE.read_text("utf-8"))
        report["public_release_approved"] = True
        for entry in report["release_gates"].values():
            entry["verified"] = True
            entry["evidence"] = "https://github.com/MasynNay/anything-plays/actions/runs/example"
        report["release_gates"]["pygame_sdl_redistribution_review"]["verified"] = False
        report["release_gates"]["real_controller_hardware_acceptance"]["verified"] = False
        self.assertIn("pygame_sdl_redistribution_review", blockers(report))
        self.assertIn("real_controller_hardware_acceptance", blockers(report))

    def test_3_0_source_access_and_current_preview_are_preserved(self):
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text("utf-8")
        self.assertIn("Download Anything Plays 3.0", readme)
        report = json.loads(FILE.read_text("utf-8"))
        self.assertIn("mgba_core_four_platforms", "single_mgba_core_four_platforms")
        self.assertIn("42822217817", report["verified_previews"]["single_mgba_core_four_platforms"])


if __name__ == "__main__":
    unittest.main()
