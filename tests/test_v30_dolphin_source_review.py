"""Positive/negative contracts for reconciling real six-shard source evidence."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from tools.check_v30_dolphin_submodules import PINNED
from tools.capture_v30_dolphin_submodule_sources import capture_shard
from tools.reconcile_v30_dolphin_source_archives import SOURCE_STATUS, reconcile


def fixture_fetch(url, filename, *, limit):
    content = ("TEST SOURCE BYTES " + url).encode("ascii")
    filename.write_bytes(content)
    return {"sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
            "gitmodules_manifest_paths": []}


def six_original_shards(index, parent):
    source = parent / "input"
    for shard in range(6):
        capture_shard(index, source / f"shard-{shard}",
                      shard_index=shard, shard_count=6, fetcher=fixture_fetch)
    return source


class OriginalDolphinSourceReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads(PINNED.read_text("utf-8"))

    def test_all_six_shards_and_34_sources_rehashed_with_all_rights_false(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            source = six_original_shards(self.index, root)
            result = reconcile(self.index, source, root / "review")
            self.assertEqual(result["status"], SOURCE_STATUS)
            self.assertEqual(result["captured_source_archive_count"], 34)
            self.assertEqual(result["verified_shard_count"], 6)
            self.assertEqual(len(result["submodules"]), 34)
            self.assertEqual(sum(x["source_archive_count"] for x in result["shards"]), 34)
            self.assertTrue(result["upstream_source_archive_candidates_collected"])
            for key in ("approved_for_binary_distribution",
                        "source_to_shipped_binary_correspondence_verified",
                        "complete_corresponding_source_and_build_dependencies_verified",
                        "independent_license_review_complete",
                        "dolphin_sys_source_and_rights_verified"):
                self.assertFalse(result[key])
            saved = json.loads((root / "review/DOLPHIN_34_SOURCE_ARCHIVE_REVIEW_UNAPPROVED.json").read_text())
            self.assertEqual(saved, result)
            document = root / "review/DOLPHIN_34_SOURCE_ARCHIVE_REVIEW_UNAPPROVED.json"
            recorded = (root / "review/SHA256SUMS.txt").read_text()
            self.assertEqual(recorded, f"{hashlib.sha256(document.read_bytes()).hexdigest()}  {document.name}\n")
            self.assertEqual(len(list((root / "review").iterdir())), 2)

    def test_missing_or_extra_shard_and_unknown_files_fail_closed(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            inp = six_original_shards(self.index, root)
            (inp / "shard-3" / "unexpected-file").write_bytes(b"x")
            with self.assertRaisesRegex(ValueError, "missing/extra"):
                reconcile(self.index, inp, root / "out")
            (inp / "shard-3" / "unexpected-file").unlink()
            (inp / "shard-5").rename(inp / "shard-extra")
            with self.assertRaisesRegex(ValueError, "exactly the original six"):
                reconcile(self.index, inp, root / "out")

    def test_falsified_rights_shard_completeness_and_binary_hash_fail_closed(self):
        for mutation, message in (
            (lambda d: d.update(approved_for_binary_distribution=True), "approval"),
            (lambda d: d.update(complete_shard=False), "provenance or completeness"),
            (lambda d: d.update(shard_index=9), "provenance or completeness"),
            (lambda d: next(iter(d["submodules"].values())).update(
                corresponding_shipped_binary_verified=True), "approval"),
        ):
            with TemporaryDirectory() as folder:
                root = Path(folder)
                inp = six_original_shards(self.index, root)
                path = inp / "shard-0/DOLPHIN_SUBMODULE_SOURCE_CANDIDATES_UNAPPROVED.json"
                data = json.loads(path.read_text())
                mutation(data)
                path.write_text(json.dumps(data))
                with self.subTest(message=message):
                    with self.assertRaisesRegex(ValueError, message):
                        reconcile(self.index, inp, root / "out")
        with TemporaryDirectory() as folder:
            root = Path(folder)
            inp = six_original_shards(self.index, root)
            archive = next((inp / "shard-1").glob("*.tar.gz"))
            archive.write_bytes(archive.read_bytes() + b"tampered")
            with self.assertRaisesRegex(ValueError, "archive SHA/size mismatch"):
                reconcile(self.index, inp, root / "out")

    def test_changed_gitlink_and_checksum_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            inp = six_original_shards(self.index, root)
            index = copy.deepcopy(self.index)
            index["submodules"][0]["gitlink_commit"] = "f" * 40
            with self.assertRaisesRegex(ValueError, "changed or duplicate Gitlink"):
                reconcile(index, inp, root / "out")
        with TemporaryDirectory() as folder:
            root = Path(folder)
            inp = six_original_shards(self.index, root)
            checksum = inp / "shard-2/SHA256SUMS.txt"
            checksum.write_text("0" * 64 + "  wrong.tar.gz\n")
            with self.assertRaisesRegex(ValueError, "SHA256SUMS mismatch"):
                reconcile(self.index, inp, root / "out")

    def test_cli_and_workflow_are_research_only(self):
        root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            [sys.executable, "-m", "tools.reconcile_v30_dolphin_source_archives", "--help"],
            cwd=root, text=True, capture_output=True, timeout=15,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--input", proc.stdout)
        workflow = (root / ".github/workflows/v30-dolphin-source-review.yml").read_text()
        self.assertIn("42446758270", workflow)
        self.assertIn("DOLPHIN_34_SOURCE_ARCHIVE_REVIEW_UNAPPROVED.json", workflow)
        self.assertIn("gh run download", workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("gh release upload", workflow)
        self.assertNotIn("AP_V30_APPROVED_RELEASE: '1'", workflow)


if __name__ == "__main__":
    unittest.main()
