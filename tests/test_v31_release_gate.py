"""Release gate rejects unsupported distribution; untested hardware must be disclosed."""
import json
from pathlib import Path
import unittest
from tools.check_v31_release import blockers, FILE, REQUIRED_GATES, PUBLICATION_GATES, ADVISORY_GATE


class V31ReleaseGateTests(unittest.TestCase):
    def test_publication_evidence_and_hardware_disclosure_are_separate(self):
        report = json.loads(FILE.read_text("utf-8"))
        self.assertIn(report["status"], {"IN_DEVELOPMENT", "READY_TO_PUBLISH", "PUBLISHED"})
        self.assertEqual(set(report["release_gates"]), set(REQUIRED_GATES))
        self.assertIs(report["release_gates"][ADVISORY_GATE]["verified"], False)
        self.assertIs(report["hardware_acceptance_disclosure"]["physical_controller_tested"], False)
        self.assertIs(report["hardware_acceptance_disclosure"]["owner_accepts_uncertified_hardware"], True)
        for name in PUBLICATION_GATES:
            item = report["release_gates"][name]
            if item["verified"]:
                self.assertTrue(item["evidence"].startswith(
                    "https://github.com/MasynNay/anything-plays/"
                ), name)
                self.assertNotIn(name, blockers(report))
            else:
                self.assertIn(name, blockers(report))
        if report["public_release_approved"]:
            self.assertIn(report["status"], {"READY_TO_PUBLISH", "PUBLISHED"})
            self.assertTrue(all(report["release_gates"][name]["verified"]
                                for name in PUBLICATION_GATES))
            self.assertEqual(blockers(report), ())
            base = Path(__file__).resolve().parents[1]
            self.assertTrue((base/"docs/V3_1_SCOPED_DISTRIBUTION_DECISION.md").is_file())
            self.assertTrue((base/"docs/V3_1_LGPL_REBUILD_REPLACEMENT.md").is_file())
            self.assertTrue((base/"docs/V3_1_PUBLIC_RELEASE_NOTES.md").is_file())
        else:
            self.assertIn("owner has not approved this exact release", blockers(report))

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
