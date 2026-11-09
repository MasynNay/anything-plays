"""Original native + source joiner must stay research-only and fail closed."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SourceReviewWorkflowContracts(unittest.TestCase):
    def test_joins_existing_successful_runs_without_publishing(self):
        workflow = (ROOT / ".github/workflows/v30-source-review-matrix.yml").read_text("utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("\n  pull_request:", workflow)
        self.assertIn("\n  push:", workflow)
        self.assertIn("branches: [feature/v3.0-unified-test]", workflow)
        self.assertIn("inputs.native_input_run_id || '42437133733'", workflow)
        self.assertIn("inputs.source_snapshot_run_id || '42441448884'", workflow)
        for name in (
            "Anything Plays 3.0 | Complete offline installer lab",
            "Anything Plays 3.0 | Preserve reported upstream sources",
            "PRESERVED_NATIVE_INPUTS.json",
            "SOURCE_SNAPSHOTS_UNAPPROVED.json",
            "NATIVE-INPUTS-UNAPPROVED",
            "SOURCE-SNAPSHOTS-UNAPPROVED",
            "python -m tools.create_v30_candidate_lock",
            "python -m tools.create_v30_source_review_inventory",
            "AnythingPlays-3.0.0-SOURCE-REVIEW-UNAPPROVED",
            "retention-days: 90",
        ):
            self.assertIn(name, workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("gh release edit", workflow)
        self.assertIn('["approved_for_public_binary_distribution"] is False', workflow)
        self.assertIn('["source_snapshots_captured"] == 10', workflow)
        self.assertIn("sum(p.name.endswith(\".tar.gz\") for p in source_files) == 10", workflow)

    def test_generator_writes_all_source_approval_flags_false(self):
        generator = (ROOT / "tools/create_v30_source_review_inventory.py").read_text("utf-8")
        self.assertIn('"approved_for_public_binary_distribution": False', generator)
        self.assertIn('"corresponding_source_inventory_verified": False', generator)
        self.assertIn('"source_to_binary_verified": False', generator)
        self.assertIn('"source_build_dependencies_reviewed": False', generator)
        self.assertIn('"redistribution_license_reviewed": False', generator)
        self.assertIn('"source_and_license_reviewed": False', generator)
        self.assertIn('"mednafen_pce_fast"', generator)


if __name__ == "__main__":
    unittest.main()
