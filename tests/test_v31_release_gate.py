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
        # Two source-pinned full-installer gates passed real four-platform
        # installed QA. Keep the unresolved hardware, source, rights and
        # publication gates blocking rather than assuming all six are open.
        verified = {
            "full_eighteen_console_installer",
            "four_platform_full_installer_verification",
        }
        still_open = set(REQUIRED_GATES) - verified
        self.assertEqual(
            set(blockers(report)),
            still_open | {"owner has not approved this exact release"},
        )
        for name in verified:
            self.assertIs(report["release_gates"][name]["verified"], True)
            self.assertTrue(report["release_gates"][name]["evidence"].startswith(
                "https://github.com/MasynNay/anything-plays/actions/runs/"
            ))
            self.assertNotIn(name, blockers(report))
        for name in still_open:
            self.assertIs(report["release_gates"][name]["verified"], False)
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
