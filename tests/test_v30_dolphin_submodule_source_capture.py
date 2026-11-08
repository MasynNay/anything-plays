"""Ensure Dolphin sources are pinned, sharded, hash-checked and unapproved."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from tools.check_v30_dolphin_submodules import PINNED, validate_index
from tools.capture_v30_dolphin_submodule_sources import (
    STATUS, capture_shard, immutable_archive_url,
)


def mock_archive(url, destination, *, limit):
    """Write deterministic local fixture, no HTTP calls or proprietary code."""
    data = ("ORIGINAL TEST-ONLY SOURCE ARCHIVE " + url).encode("utf-8")
    destination.write_bytes(data)
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "gitmodules_manifest_paths": [],
    }


class DolphinPinnedSourceCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads(PINNED.read_text("utf-8"))

    def test_all_34_entries_covered_exactly_once_across_six_shards(self):
        expected = set(validate_index(self.index))
        seen = set()
        for shard in range(6):
            with TemporaryDirectory() as scratch:
                out = Path(scratch) / "sources"
                report = capture_shard(self.index, out, shard_index=shard,
                                       shard_count=6, fetcher=mock_archive)
                self.assertEqual(report["status"], STATUS)
                self.assertEqual(report["parent_commit"], self.index["parent_commit"])
                self.assertTrue(report["complete_shard"])
                self.assertFalse(report["approved_for_binary_distribution"])
                self.assertFalse(report["source_to_shipped_binary_correspondence_verified"])
                self.assertFalse(report["complete_corresponding_source_and_build_dependencies_verified"])
                self.assertFalse(report["independent_license_review_complete"])
                self.assertFalse(seen.intersection(report["submodules"]))
                seen.update(report["submodules"])
                checksums = (out / "SHA256SUMS.txt").read_text().splitlines()
                self.assertEqual(len(checksums), len(report["submodules"]) + 1)
                for row in report["submodules"].values():
                    contents = (out / row["archive_file"]).read_bytes()
                    self.assertEqual(hashlib.sha256(contents).hexdigest(),
                                     row["archive_sha256"])
                    self.assertFalse(row["license_reviewed"])
                    self.assertFalse(row["corresponding_shipped_binary_verified"])
                stored = json.loads((out / "DOLPHIN_SUBMODULE_SOURCE_CANDIDATES_UNAPPROVED.json").read_text())
                self.assertEqual(report, stored)
        self.assertEqual(seen, expected)

    def test_both_allowed_hosts_use_immutable_revision_not_branch(self):
        for row in self.index["submodules"]:
            url = immutable_archive_url(row["source_repository"], row["gitlink_commit"])
            self.assertIn(row["gitlink_commit"], url)
            self.assertTrue(url.startswith(("https://codeload.github.com/",
                                            "https://gitlab.com/")))
        with self.assertRaisesRegex(ValueError, "full Git SHA"):
            immutable_archive_url("https://github.com/org/repo", "main")
        with self.assertRaisesRegex(ValueError, "Unsupported Dolphin source host"):
            immutable_archive_url("https://untrusted.invalid/org/repo", "a" * 40)
        with self.assertRaisesRegex(ValueError, "Unsupported GitHub"):
            immutable_archive_url("https://github.com/org/repo/extra", "a" * 40)

    def test_forged_approval_invalid_shard_and_nonempty_output_rejected(self):
        changed = copy.deepcopy(self.index)
        changed["public_binary_redistribution_approved"] = True
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "sources"
            with self.assertRaisesRegex(ValueError, "unreviewed approvals"):
                capture_shard(changed, out, shard_index=0, shard_count=6,
                              fetcher=mock_archive)
            for shard, count in ((-1, 6), (6, 6), (0, 0), (True, 6)):
                with self.assertRaisesRegex(ValueError, "shard"):
                    capture_shard(self.index, out, shard_index=shard,
                                  shard_count=count, fetcher=mock_archive)
            out.mkdir()
            (out / "stale").write_text("do not overwrite")
            with self.assertRaisesRegex(ValueError, "empty non-symlink"):
                capture_shard(self.index, out, shard_index=0, shard_count=6,
                              fetcher=mock_archive)

    def test_corrupted_archive_digest_and_missing_file_fail_closed(self):
        def corruption(url, path, *, limit):
            info = mock_archive(url, path, limit=limit)
            info["sha256"] = "0" * 64
            return info

        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "hash/size mismatch"):
                capture_shard(self.index, Path(tmp) / "bad",
                              shard_index=0, shard_count=34, fetcher=corruption)
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "not created as a regular file"):
                capture_shard(self.index, Path(tmp) / "missing", shard_index=0,
                              shard_count=34, fetcher=lambda *a, **k: {})

    def test_cli_and_research_workflow_cannot_publish_or_modify_release_gate(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-m", "tools.capture_v30_dolphin_submodule_sources", "--help"],
            cwd=root, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--shard-count", result.stdout)
        workflow = (root / ".github/workflows/v30-dolphin-submodule-sources.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("branches: [feature/v3.0-unified-test]", workflow)
        self.assertIn("retention-days: 45", workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("gh release upload", workflow)
        self.assertNotIn("AP_V30_APPROVED_RELEASE: '1'", workflow)


if __name__ == "__main__":
    unittest.main()
