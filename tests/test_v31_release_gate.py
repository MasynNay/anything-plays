"""Release gate rejects unsupported distribution; untested hardware must be disclosed."""
import json
from pathlib import Path
import unittest
from tools.check_v31_release import blockers, FILE, REQUIRED_GATES, PUBLICATION_GATES, ADVISORY_GATE


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
            (still_open - {ADVISORY_GATE}) | {"owner has not approved this exact release"},
        )
        for name in verified:
            self.assertIs(report["release_gates"][name]["verified"], True)
            self.assertTrue(report["release_gates"][name]["evidence"].startswith(
                "https://github.com/MasynNay/anything-plays/actions/runs/"
            ))
            self.assertNotIn(name, blockers(report))
        for name in still_open:
            self.assertIs(report["release_gates"][name]["verified"], False)
            if name in PUBLICATION_GATES:
                self.assertIn(name, blockers(report))
            else:
                self.assertNotIn(name, blockers(report))
        self.assertIs(report["hardware_acceptance_disclosure"]["physical_controller_tested"], False)

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
