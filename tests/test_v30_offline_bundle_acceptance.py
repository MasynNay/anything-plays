"""Keep package inclusion evidence distinct from gameplay and legal approval."""
import json
from pathlib import Path
import unittest

from tools.check_v30_release import release_blockers


ROOT = Path(__file__).resolve().parents[1]


class OfflineBundleEvidenceTests(unittest.TestCase):
    def test_only_offline_bundling_is_accepted(self):
        record = json.loads(
            (ROOT / "config/v3.0-release-acceptance.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(len(record["systems"]), 18)
        self.assertEqual(len(record["platform_validation"]), 4)
        for system in record["systems"].values():
            self.assertIs(system["bundled"], True)
            self.assertIn("42432952359", system["bundled_evidence"])
            self.assertIs(system["real_game_verified"], False)
            self.assertIs(system["audio_verified"], False)
        for platform in record["platform_validation"].values():
            self.assertIs(platform["all_consoles_bundled_offline"], True)
            self.assertIn("42432952359", platform["offline_bundle_evidence"])
            self.assertIs(platform["all_consoles_verified"], False)
            self.assertIs(platform["long_run_verified"], False)
        self.assertIs(
            record["required_release_evidence"]["third_party_license_audit_complete"],
            False,
        )
        blockers = release_blockers(record)
        self.assertTrue(blockers)
        self.assertTrue(any("third_party_license" in item for item in blockers))


if __name__ == "__main__":
    unittest.main()
