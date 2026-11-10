"""Pinned exact three nested Dolphin Gitlink source/review contracts."""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest

from tools.capture_v30_dolphin_nested_sources import (
    NESTED, PINNED, STATUS, capture_nested_sources, validate_nested_map,
    verify_upstream, _normal_repo,
)


def original():
    index = json.loads(NESTED.read_text("utf-8"))
    direct = json.loads(PINNED.read_text("utf-8"))
    rows = {}
    for entry in direct["submodules"]:
        rows[entry["path"]] = {
            "source_repository": entry["source_repository"],
            "pinned_gitlink_commit": entry["gitlink_commit"],
            "archive_sha256": "f"*64,
            "archive_size_bytes": 10,
            "nested_gitmodules_reported": [],
        }
    for parent in index["parents"]:
        row = rows[parent["parent_path"]]
        row["archive_sha256"] = parent["parent_source_archive_sha256"]
        row["archive_size_bytes"] = parent["parent_source_archive_size_bytes"]
        row["nested_gitmodules_reported"] = ["actual pinned upstream .gitmodules"]
    review = {
        "status": "UNAPPROVED-DOLPHIN-34-SOURCE-ARCHIVE-REVIEW",
        "pinned_dolphin_parent_commit": direct["parent_commit"],
        "captured_source_archive_count": 34,
        "submodules": rows,
    }
    return index, direct, review


def fake_tree(index, *, additional_nested=False):
    def tree(repo, sha):
        for parent in index["parents"]:
            if sha == parent["parent_gitlink_commit"]:
                return {
                    "sha": sha, "truncated": False,
                    "tree": [{"type": "commit", "mode": "160000",
                              "path": child["path"], "sha": child["gitlink_commit"]}
                             for child in parent["nested"]],
                }
        rows = []
        if additional_nested:
            rows = [{"type": "commit", "mode": "160000", "path": "bad-extra",
                     "sha": "a"*40}]
        return {"sha": sha, "truncated": False, "tree": rows}
    return tree


def fake_modules(index):
    def modules(repo, sha):
        parent = next(p for p in index["parents"]
                      if p["parent_gitlink_commit"] == sha)
        return "\n".join(
            f'[submodule "{c["path"]}"]\n'
            f'path = {c["path"]}\n'
            f'url = {c["declared_source_url"]}'
            for c in parent["nested"]
        )
    return modules


def mock_archive_fetch(url, destination, *, limit):
    import gzip
    if "github.com" not in url:
        raise AssertionError("Source URL must be GitHub codeload")
    sha = url.rsplit("/", 1)[1]
    content = b"Original test-only MIT style placeholder, NOT a real license."
    with tarfile.open(destination, "w:gz") as tar:
        lic = tarfile.TarInfo(f"source-{sha}/LICENSE")
        lic.size = len(content)
        tar.addfile(lic, io.BytesIO(content))
    payload = Path(destination).read_bytes()
    return {"sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload), "gitmodules_manifest_paths": []}


class NestedDolphinSourceContracts(unittest.TestCase):
    def test_real_frozen_nested_index_exact_three_sha_gitlinks(self):
        index, direct, review = original()
        result = validate_nested_map(index, direct, review)
        self.assertEqual(len(result), 2)
        self.assertEqual(sum(len(r) for r in result.values()), 3)
        self.assertEqual(set(result), {
            "Externals/cubeb/cubeb", "Externals/libadrenotools",
        })
        self.assertEqual(set(result["Externals/cubeb/cubeb"]),
                         {"googletest", "cmake/sanitizers-cmake"})
        self.assertEqual(set(result["Externals/libadrenotools"]),
                         {"lib/linkernsbypass"})
        self.assertFalse(index["approved_for_binary_distribution"])
        self.assertFalse(index["complete_source_to_shipped_binary_verified"])

    def test_upstream_matching_rejects_any_unobserved_gitlink(self):
        index, direct, review = original()
        rows = validate_nested_map(index, direct, review)
        checked = verify_upstream(index, rows, tree_fetcher=fake_tree(index),
                                  modules_fetcher=fake_modules(index))
        self.assertEqual(len(checked), 3)
        with self.assertRaisesRegex(ValueError, "another nested Gitlink"):
            verify_upstream(index, rows,
                            tree_fetcher=fake_tree(index, additional_nested=True),
                            modules_fetcher=fake_modules(index))

    def test_nested_index_disallows_missing_parent_forged_approval_and_sha(self):
        index, direct, review = original()
        tampered = copy.deepcopy(index)
        tampered["approved_for_binary_distribution"] = True
        with self.assertRaisesRegex(ValueError, "approvals"):
            validate_nested_map(tampered, direct, review)
        tampered = copy.deepcopy(index)
        tampered["parents"][0]["nested"][0]["gitlink_commit"] = "latest"
        with self.assertRaisesRegex(ValueError, "immutable"):
            validate_nested_map(tampered, direct, review)
        tampered = copy.deepcopy(index)
        tampered["parents"][0]["nested"][0]["path"] = "../secret"
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            validate_nested_map(tampered, direct, review)
        tampered = copy.deepcopy(index)
        tampered["parents"][0]["parent_source_archive_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "detached"):
            validate_nested_map(tampered, direct, review)
        tampered = copy.deepcopy(index)
        tampered["parents"][1]["nested"] = []
        with self.assertRaisesRegex(ValueError, "original parent|missing"):
            validate_nested_map(tampered, direct, review)

    def test_requires_original_34_artifact_review_for_two_nested_parents(self):
        index, direct, review = original()
        review["submodules"]["Externals/cubeb/cubeb"]["nested_gitmodules_reported"] = []
        with self.assertRaisesRegex(ValueError, "missing/extra nested"):
            validate_nested_map(index, direct, review)

    def test_recursively_checked_archives_never_approve_public_binary_distribution(self):
        index, direct, review = original()
        rows = validate_nested_map(index, direct, review)
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "review"
            result = capture_nested_sources(
                index, rows, out,
                fetcher=mock_archive_fetch,
                tree_fetcher=fake_tree(index),
                modules_fetcher=fake_modules(index),
                review_sha256="a"*64,
            )
            self.assertEqual(result["status"], STATUS)
            self.assertEqual(result["source_candidates_captured"], 3)
            self.assertEqual(len(result["archives"]), 3)
            self.assertTrue(result["pinned_nested_gitlink_tree_closure_verified"])
            self.assertFalse(result["complete_corresponding_source_verified"])
            self.assertFalse(result["source_to_dolphin_binary_verified"])
            self.assertFalse(result["independent_license_review_complete"])
            self.assertFalse(result["public_binary_distribution_approved"])
            self.assertEqual(len(list(out.iterdir())), 5)
            saved = (out / "SHA256SUMS.txt").read_text("ascii").splitlines()
            self.assertEqual(len(saved), 4)
            for row in result["archives"].values():
                self.assertRegex(row["archive_sha256"], "^[a-f0-9]{64}$")
                self.assertEqual(len(row["root_license_notice_candidates"]), 1)
                self.assertFalse(row["compiled_into_original_dolphin_binary_verified"])
                self.assertFalse(row["source_rights_independently_reviewed"])

    def test_workflow_is_strict_research_and_cannot_release_binaries(self):
        root = Path(__file__).resolve().parents[1]
        yaml = (root / "docs/history/workflows/v30-dolphin-nested-sources.yml").read_text("utf-8")
        self.assertIn("42447184893", yaml)
        self.assertIn("DOLPHIN_THREE_NESTED_SOURCE_CANDIDATES_UNAPPROVED.json", yaml)
        self.assertIn("capture_v30_dolphin_nested_sources", yaml)
        self.assertNotIn("gh release", yaml)
        self.assertNotIn("continue-on-error: true", yaml)
        self.assertIn("retention-days:", yaml)


if __name__ == "__main__":
    unittest.main()
