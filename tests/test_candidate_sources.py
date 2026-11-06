"""Offline validation of source snapshot provenance controls."""

from copy import deepcopy
import unittest

from tools.capture_candidate_sources import source_revisions, REQUIRED_TARGETS

COMMITS = {
    "mgba": "7a12d6d4b9acb14c0ae62c9166b6a2f3d08007f6",
    "snes9x": "fae2fea08f74180759ef540ee94259213f503480",
}


class SourceSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.lock = {"targets": {}}
        for target in REQUIRED_TARGETS:
            self.lock["targets"][target] = {
                name: {
                    "source_repository_url": f"https://github.com/libretro/{name}",
                    "source_commit_sha": commit,
                }
                for name, commit in COMMITS.items()
            }

    def test_locked_commits_match_for_all_four_targets(self):
        result = source_revisions(self.lock)
        self.assertEqual(set(result), {"mgba", "snes9x"})
        for name, commit in COMMITS.items():
            self.assertEqual(result[name]["source_commit_sha"], commit)

    def test_refuses_incomplete_architecture_set(self):
        self.lock["targets"].pop("macos-x86_64")
        with self.assertRaisesRegex(ValueError, "Incomplete four-target"):
            source_revisions(self.lock)

    def test_refuses_conflicting_source_revision(self):
        self.lock["targets"]["linux-x86_64"]["mgba"]["source_commit_sha"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "Architecture source revisions disagree"):
            source_revisions(self.lock)

    def test_refuses_forged_upstream_url(self):
        self.lock["targets"]["windows-x86_64"]["snes9x"]["source_repository_url"] = (
            "https://example.invalid/snes9x"
        )
        with self.assertRaisesRegex(ValueError, "Unexpected upstream"):
            source_revisions(self.lock)

    def test_refuses_short_or_invalid_revision(self):
        self.lock["targets"]["macos-arm64"]["mgba"]["source_commit_sha"] = "7a12d6d"
        with self.assertRaisesRegex(ValueError, "Missing source SHA"):
            source_revisions(self.lock)


if __name__ == "__main__":
    unittest.main()
