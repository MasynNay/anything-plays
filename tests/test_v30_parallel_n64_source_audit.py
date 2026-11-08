"""Regression contracts for authentic pinned N64 source and 11 notice files."""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import audit_v30_parallel_n64_source as core
from tools.v30_release_lock import TARGETS


def fixture():
    index = json.loads(core.INDEX.read_text("utf-8"))
    tree = {
        "sha": index["reported_source_commit"],
        "truncated": False,
        "tree": [
            {"path": ".gitmodules", "type": "blob", "mode": "100644",
             "size": 0, "sha": index["gitmodules_blob_sha1"]},
        ] + [
            {"path": row["path"], "type": "blob", "mode": "100644",
             "sha": row["git_blob_sha1"], "size": row["size_bytes"]}
            for row in index["notices"]
        ],
    }
    while len(tree["tree"]) < 1970:
        tree["tree"].append({
            "type": "tree", "mode": "040000",
            "path": f"synthetic-unused-directory-{len(tree['tree'])}",
        })
    review = {
        "status": core.SOURCE_REVIEW_STATUS,
        "approved_for_public_binary_distribution": False,
        "independent_binary_to_source_match_proven": False,
        "targets": {
            target: {"cores": {"parallel_n64": {
                "native_sha256": index["core_sha256_per_target"][target],
                "source_repository": index["source_repository"],
                "source_commit_sha": index["reported_source_commit"],
                "source_archive_sha256": index["archived_source_snapshot_sha256"],
                "source_archive_size_bytes": index["archived_source_snapshot_size_bytes"],
                "source_to_binary_verified": False,
                "redistribution_license_reviewed": False,
                "source_build_dependencies_reviewed": False,
            }}}
            for target in TARGETS
        },
    }
    return index, tree, review


class ParallelN64SourceAuditContracts(unittest.TestCase):
    def test_exact_original_tree_has_zero_gitlinks_11_source_notice_blobs(self):
        index, tree, review = fixture()
        items = core.verify_tree(index, tree)
        self.assertEqual(len(items), 11)
        self.assertEqual(index["gitlink_count"], 0)
        self.assertEqual(index["gitmodules_size_bytes"], 0)
        self.assertEqual(index["gitmodules_blob_sha1"],
                         hashlib.sha1(b"blob 0\0").hexdigest())
        self.assertEqual(len(tree["tree"]), 1970)
        self.assertTrue(core.verify_old_review(index, review))
        self.assertEqual(set(review["targets"]), TARGETS)
        self.assertFalse(index["public_binary_redistribution_approved"])

    def test_real_report_requires_unchanged_original_archive_and_native_sha(self):
        index, tree, review = fixture()
        review["targets"]["macos-arm64"]["cores"]["parallel_n64"][
            "native_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "original N64 candidate"):
            core.verify_old_review(index, review)
        index, tree, review = fixture()
        review["targets"]["windows-x86_64"]["cores"]["parallel_n64"][
            "source_to_binary_verified"] = True
        with self.assertRaisesRegex(ValueError, "source_to_binary_verified"):
            core.verify_old_review(index, review)

    def test_missing_or_introduced_gitlinks_are_not_silently_accepted(self):
        index, tree, review = fixture()
        tree["tree"][-1] = {"type": "commit", "mode": "160000",
                            "path": "new-undisclosed-submodule",
                            "sha": "f"*40}
        with self.assertRaisesRegex(ValueError, "Gitlinks"):
            core.verify_tree(index, tree)
        _, tree, _ = fixture()
        tree["tree"][0]["size"] = 5
        with self.assertRaisesRegex(ValueError, "empty Git blob"):
            core.verify_tree(index, tree)
        _, tree, _ = fixture()
        tree["tree"].pop()
        with self.assertRaisesRegex(ValueError, "Git tree"):
            core.verify_tree(index, tree)

    def test_all_source_license_candidates_exact_blob_and_bytes(self):
        index, tree, review = fixture()
        tree["tree"][2]["sha"] = "f"*40
        with self.assertRaisesRegex(ValueError, "pinned Git blob"):
            core.verify_tree(index, tree)
        index, tree, review = fixture()
        tree["tree"][1]["path"] = "unlisted/COPYING"
        with self.assertRaisesRegex(ValueError, "licenses/notices"):
            core.verify_tree(index, tree)
        index, tree, review = fixture()
        index["notices"][0]["notice_reviewed"] = True
        with self.assertRaisesRegex(ValueError, "already-approved"):
            core.valid_index(index)

    def test_fixture_rejects_forged_rights_and_incomplete_native_matrix(self):
        index, tree, review = fixture()
        for flag in ("source_to_native_binary_independently_verified",
                     "public_binary_redistribution_approved",
                     "in_process_mixed_license_compatibility_reviewed"):
            with self.subTest(field=flag):
                changed = copy.deepcopy(index)
                changed[flag] = True
                with self.assertRaisesRegex(ValueError, "without evidence"):
                    core.valid_index(changed)
        bad = copy.deepcopy(index)
        bad["core_sha256_per_target"].pop("linux-x86_64")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            core.valid_index(bad)

    def test_original_tar_notice_sha256_are_measured_not_assumed(self):
        index, tree, review = fixture()
        with TemporaryDirectory() as tmp:
            file = Path(tmp)/"source.tar.gz"
            # Construct an original-style, synthetic tar without any original
            # proprietary/commercial ROM or actual upstream source content.
            # The unit test patches only the OUTER archive SHA, never the
            # actual notice blob check. Live CI checks unpatched originals.
            prefix = "parallel-n64-" + index["reported_source_commit"]
            fake_notes = {}
            with tarfile.open(file, "w:gz") as tar:
                blank = tarfile.TarInfo(prefix + "/.gitmodules")
                blank.size = 0
                tar.addfile(blank, io.BytesIO(b""))
                for row in index["notices"]:
                    content = ("SYNTHETIC UNIT TEST NOTICE ONLY: " + row["path"]).encode()
                    fake_notes[row["path"]] = content
                    tarinfo = tarfile.TarInfo(prefix + "/" + row["path"])
                    tarinfo.size = len(content)
                    tar.addfile(tarinfo, io.BytesIO(content))
                    row["git_blob_sha1"] = core._git_blob(content)
                    row["size_bytes"] = len(content)
            fake_digest = index["archived_source_snapshot_sha256"]
            fake_size = index["archived_source_snapshot_size_bytes"]
            with patch.object(core, "_hash_file", return_value=(fake_digest, fake_size)):
                digest, size, notices = core.audit_original_tar(index, file)
            self.assertEqual(digest, fake_digest)
            self.assertEqual(size, fake_size)
            self.assertEqual(len(notices), 11)
            for path in fake_notes:
                self.assertEqual(notices[path]["sha256"],
                                 hashlib.sha256(fake_notes[path]).hexdigest())
                self.assertFalse(notices[path]["license_text_independently_reviewed"])
                self.assertFalse(notices[path]["compiled_into_native_binary_independently_verified"])
            # Fail if ANY actual source member content changed after its
            # pinned Git blob SHA was recorded.
            index["notices"][0]["git_blob_sha1"] = "f"*40
            with patch.object(core, "_hash_file", return_value=(fake_digest, fake_size)):
                with self.assertRaisesRegex(ValueError, "disagrees"):
                    core.audit_original_tar(index, file)

    def test_audit_contract_stays_research_only(self):
        index, tree, review = fixture()
        root = Path(__file__).resolve().parents[1]
        yml = (root/".github/workflows/v30-parallel-n64-source-audit.yml").read_text("utf-8")
        self.assertIn("audit_v30_parallel_n64_source", yml)
        self.assertIn("42441448884", yml)
        self.assertIn("42444450521", yml)
        self.assertNotIn("gh release", yml)
        self.assertNotIn("continue-on-error: true", yml)
        self.assertIn("UNAPPROVED", yml)
        self.assertEqual(index["archived_source_snapshot_size_bytes"], 6877459)


if __name__ == "__main__":
    unittest.main()
