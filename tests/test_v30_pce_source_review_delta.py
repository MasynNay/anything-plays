"""Test old nightly source remains unknown while 11-source new PCE trial is recorded."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools.create_v30_pce_source_review_delta import (
    TARGET_FROM_REVIEW, RESULT, reconcile,
)
from tools.v30_pce_candidate import load_index
from tools.v30_release_lock import CORE_NAMES, TARGETS


def fixture():
    pinned = load_index()
    base = {
        "schema_version": 1,
        "status": "UNAPPROVED-SOURCE-REVIEW-CANDIDATE",
        "approved_for_public_binary_distribution": False,
        "corresponding_source_inventory_verified": False,
        "independent_binary_to_source_match_proven": False,
        "native_core_count": 11, "system_profile_count": 18,
        "source_snapshots_captured": 10,
        "source_snapshots_missing": ["mednafen_pce_fast"],
        "unresolved_tasks": [
            "Determine matching Beetle PCE Fast source revision from build provenance",
            "Archive and review exact Dolphin Gitlink submodule sources and dependencies",
            "Review all native core transitive libraries",
        ],
        "targets": {},
    }
    trial = {}
    for target in TARGETS:
        cores = {
            name: {
                "native_sha256": "a" * 64,
                "original_native_archive_sha256": "b" * 64,
                "source_commit_sha": None if name == "mednafen_pce_fast" else "f"*40,
                "source_archive_sha256": None if name == "mednafen_pce_fast" else "c"*64,
                "source_to_binary_verified": False,
                "redistribution_license_reviewed": False,
                "source_build_dependencies_reviewed": False,
            }
            for name in CORE_NAMES
        }
        base["targets"][target] = {
            "cores": cores,
            "dolphin_sys": {"source_and_license_reviewed": False},
        }
    for target, record in pinned["targets"].items():
        trial[target] = {
            "status": "SOURCE-BUILT-PCE-INTEGRATION-PREVIEW-ONLY-UNAPPROVED",
            "target": target,
            "cores": 11,
            "profiles": 18,
            "original_other_cores_and_dolphin_archive_count": 11,
            "gamecube_and_all_other_original_core_archives_unchanged": True,
            "public_release_approved": False,
            "mixed_license_review_complete": False,
            "native_sha256": record["native_sha256"],
            "pce_git_commit": pinned["pinned_source_commit"],
            "pce_source_archive_sha256": record["source_archive_sha256"],
            "substituted_core": record["core_filename"],
            "substituted_archive": record["core_filename"] + ".zip",
            "staged_archive_sha256": "c" * 64,
        }
    return base, pinned, trial


class PCEEleventhSourceReviewTests(unittest.TestCase):
    def test_overlay_changes_only_pce_core_and_preserves_old_unknown_nightly(self):
        base, pinned, trial = fixture()
        result = reconcile(base, pinned, trial)
        self.assertEqual(result["status"], RESULT)
        self.assertEqual(result["source_snapshots_captured"], 11)
        self.assertEqual(result["source_snapshots_missing"], [])
        self.assertFalse(result["approved_for_public_binary_distribution"])
        self.assertFalse(result["corresponding_source_inventory_verified"])
        self.assertFalse(result["independent_binary_to_source_match_proven"])
        for target, targetname in TARGET_FROM_REVIEW.items():
            with self.subTest(target=target):
                new = result["targets"][target]
                old = base["targets"][target]
                self.assertEqual(new["dolphin_sys"], old["dolphin_sys"])
                for name in CORE_NAMES - {"mednafen_pce_fast"}:
                    self.assertEqual(new["cores"][name], old["cores"][name])
                row = new["cores"]["mednafen_pce_fast"]
                self.assertEqual(row["native_sha256"], pinned["targets"][targetname]["native_sha256"])
                self.assertEqual(row["source_commit_sha"], pinned["pinned_source_commit"])
                self.assertEqual(row["original_native_archive_sha256"], trial[targetname]["staged_archive_sha256"])
                self.assertTrue(row["source_built_in_isolated_original_hucard_ci"])
                self.assertFalse(row["source_to_binary_verified"])
                self.assertFalse(row["source_build_dependencies_reviewed"])
                self.assertFalse(row["redistribution_license_reviewed"])
                archived = result["unresolved_old_pce_buildbot_source_by_target"][targetname]
                self.assertIsNone(archived["source_commit_sha"])
                self.assertFalse(archived["source_to_binary_correspondence_resolved"])
        self.assertIsNone(base["targets"]["linux-x86_64"]["cores"]["mednafen_pce_fast"]["source_commit_sha"])

    def test_missing_successful_trial_and_forged_approval_are_rejected(self):
        base, pinned, trial = fixture()
        trial.pop("linux-x64")
        with self.assertRaisesRegex(ValueError, "four successfully integrated"):
            reconcile(base, pinned, trial)
        base, pinned, trial = fixture()
        trial["macos-arm64"]["public_release_approved"] = True
        with self.assertRaisesRegex(ValueError, "successful unapproved"):
            reconcile(base, pinned, trial)
        base, pinned, trial = fixture()
        pinned["approved_for_public_binary_distribution"] = True
        with self.assertRaisesRegex(ValueError, "unapproved source-built"):
            reconcile(base, pinned, trial)
        base, pinned, trial = fixture()
        base["approved_for_public_binary_distribution"] = True
        with self.assertRaisesRegex(ValueError, "cannot claim release approval"):
            reconcile(base, pinned, trial)
        base, pinned, trial = fixture()
        trial["windows-x64"]["pce_git_commit"] = "f"*40
        with self.assertRaisesRegex(ValueError, "native/ZIP/source identity changed"):
            reconcile(base, pinned, trial)

    def test_actual_cli_help_and_source_matrix_requires_exact_schema(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-m", "tools.create_v30_pce_source_review_delta", "--help"],
            cwd=root, text=True, capture_output=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--original-source-review", result.stdout)
        self.assertIn("--trial-evidence-directory", result.stdout)
        base, pinned, trial = fixture()
        base["targets"]["macos-x86_64"]["cores"].pop("mgba")
        with self.assertRaisesRegex(ValueError, "Missing complete original core"):
            reconcile(base, pinned, trial)


if __name__ == "__main__":
    unittest.main()
