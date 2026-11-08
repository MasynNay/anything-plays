"""Acceptance flags may only close for the proven four-platform offline resolver."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools.check_v30_release import ACCEPTANCE_FILE, release_blockers
from tools.v30_release_lock import LOCK_PATH, CORE_NAMES


class FrozenOfflineReleaseEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(ACCEPTANCE_FILE.read_text("utf-8"))

    def test_exact_successful_four_target_test_run_supports_only_two_offline_flags(self):
        release = self.policy["required_release_evidence"]
        proof = release["offline_runtime_evidence"]
        self.assertIs(release["no_external_emulator_setup_required"], True)
        self.assertIs(release["no_runtime_emulator_download_required"], True)
        self.assertEqual(proof["workflow"],
                         "https://github.com/MasynNay/anything-plays/actions/runs/42448004780")
        self.assertEqual(proof["verified_commit"],
                         "2b6e0c687577b8d847ed35dcb4f10b808e5b9367")
        self.assertEqual(set(proof["targets"]),
                         {"windows-x64", "linux-x64", "macos-arm64", "macos-x64"})
        self.assertEqual(proof["profiles_resolved_per_platform"], 18)
        self.assertEqual(proof["native_sha256_verified_per_platform"], 11)
        self.assertTrue(proof["strict_network_denial"])
        self.assertTrue(proof["fresh_core_pack_store"])
        self.assertFalse(proof["public_distribution_approved"])
        self.assertFalse(proof["physical_install_and_gameplay_verified"])
        self.assertFalse(proof["legal_redistribution_review_complete"])

    def test_absent_real_game_hardware_and_rights_evidence_still_blocks_stable(self):
        release = self.policy["required_release_evidence"]
        self.assertIs(release["third_party_license_audit_complete"], False)
        for target, row in self.policy["platform_validation"].items():
            with self.subTest(target=target):
                self.assertIs(row["clean_install"], False)
                self.assertIs(row["all_consoles_verified"], False)
                self.assertIs(row["long_run_verified"], False)
                self.assertTrue(row["all_consoles_bundled_offline"])
        for system, row in self.policy["systems"].items():
            with self.subTest(system=system):
                self.assertFalse(row["real_game_verified"])
                self.assertFalse(row["audio_verified"])
        blockers = release_blockers(self.policy)
        self.assertGreater(len(blockers), 30)
        self.assertTrue(any("third_party_license_audit_complete" in x for x in blockers))
        self.assertFalse(any("no_external_emulator_setup_required not verified" in x for x in blockers))
        self.assertFalse(any("no_runtime_emulator_download_required not verified" in x for x in blockers))

    def test_native_production_lock_remains_immutable_and_unapproved(self):
        lock = json.loads(LOCK_PATH.read_text("utf-8"))
        self.assertEqual(lock["native_core_count"], len(CORE_NAMES))
        self.assertEqual(len(CORE_NAMES), 11)
        self.assertFalse(lock["approved_for_binary_distribution"])
        self.assertFalse(lock["license_compatibility_reviewed"])
        self.assertFalse(lock["corresponding_source_inventory_verified"])
        self.assertEqual(lock["targets"], {})


if __name__ == "__main__":
    unittest.main()
