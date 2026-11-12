"""Release gate rejects unsupported distribution; untested hardware must be disclosed."""
import json
from pathlib import Path
import unittest
from tools.check_v31_release import blockers, FILE, REQUIRED_GATES, PUBLICATION_GATES, ADVISORY_GATE


class V31ReleaseGateTests(unittest.TestCase):
    def test_scoped_public_3_1_release_decision_is_evidence_backed(self):
        report = json.loads(FILE.read_text("utf-8"))
        self.assertEqual(report["status"], "APPROVED_PENDING_PUBLICATION")
        self.assertIs(report["public_release_approved"], True)
        self.assertEqual(set(report["release_gates"]), set(REQUIRED_GATES))
        self.assertEqual(blockers(report), ())
        for name in PUBLICATION_GATES:
            with self.subTest(gate=name):
                self.assertIs(report["release_gates"][name]["verified"], True)
                self.assertTrue(report["release_gates"][name]["evidence"].startswith(
                    "https://github.com/MasynNay/anything-plays/"
                ))
        self.assertIs(report["release_gates"][ADVISORY_GATE]["verified"], False)
        self.assertIs(report["hardware_acceptance_disclosure"]["physical_controller_tested"], False)
        decision=report["release_decision"]
        self.assertEqual(decision["scope"], "FREE_NONCOMMERCIAL_NONPROMOTIONAL_NO_DONATIONS_NO_ADS")
        self.assertEqual(decision["asset_count"], 8)
        self.assertEqual(decision["exact_approved_source_revision"],
                         "104b96621ec4cb8dc39fde8c3fe96fc854c406ed")
        self.assertIs(decision["legal_compliance_guaranteed"], False)
        self.assertIs(decision["owner_requested_publication"], True)

    def test_missing_licensing_remains_blocking_even_when_hardware_disclosed(self):
        report = json.loads(FILE.read_text("utf-8"))
        report["public_release_approved"] = True
        for entry in report["release_gates"].values():
            entry["verified"] = True
            entry["evidence"] = "https://github.com/MasynNay/anything-plays/actions/runs/example"
        report["release_gates"]["pygame_sdl_redistribution_review"]["verified"] = False
        report["release_gates"]["corresponding_source_material"]["verified"] = False
        report["release_gates"]["real_controller_hardware_acceptance"] = {
            "verified": False, "evidence": None
        }
        self.assertIn("pygame_sdl_redistribution_review", blockers(report))
        self.assertIn("corresponding_source_material", blockers(report))
        self.assertNotIn("real_controller_hardware_acceptance", blockers(report))

    def test_missing_disclosure_cannot_silently_override_untested_hardware(self):
        report = json.loads(FILE.read_text("utf-8"))
        report["public_release_approved"] = True
        for name in PUBLICATION_GATES:
            report["release_gates"][name] = {
                "verified": True,
                "evidence": "https://github.com/MasynNay/anything-plays/actions/runs/example",
            }
        self.assertEqual(blockers(report), ())
        for bad in (
            None,
            {},
            {"owner_accepts_uncertified_hardware": False,
             "physical_controller_tested": False,
             "evidence": "https://github.com/MasynNay/anything-plays/foo"},
            {"owner_accepts_uncertified_hardware": True,
             "physical_controller_tested": True,
             "evidence": "https://github.com/MasynNay/anything-plays/foo"},
        ):
            test = {**report, "hardware_acceptance_disclosure": bad}
            self.assertIn("missing explicit untested-hardware disclosure", blockers(test))

    def test_3_0_source_access_and_current_preview_are_preserved(self):
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text("utf-8")
        self.assertIn("Download Anything Plays 3.0", readme)
        report = json.loads(FILE.read_text("utf-8"))
        self.assertIn("mgba_core_four_platforms", "single_mgba_core_four_platforms")
        self.assertIn("42822217817", report["verified_previews"]["single_mgba_core_four_platforms"])


if __name__ == "__main__":
    unittest.main()
