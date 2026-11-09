"""Synthetic, fail-closed Dolphin original source candidate bundle contracts."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest

from tools.check_v30_dolphin_submodules import PINNED
from tools.capture_v30_dolphin_nested_sources import NESTED, STATUS as NESTED_STATUS
from tools.capture_v30_dolphin_submodule_sources import capture_shard
from tools.reconcile_v30_dolphin_source_archives import reconcile
from tools.package_v30_dolphin_source_bundle import (
    PARENT_COMMIT, REPORT, collect,
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture_archive(url, filename, *, limit):
    # Synthetic source bytes. Only the genuine immutable pin is validated;
    # no legal/source/binary approval can be inferred from these fixtures.
    contents = ("TEST SOURCE " + url).encode("ascii")
    filename.write_bytes(contents)
    nested = (
        ["tracked .gitmodules"] if any(item in url for item in
        ("mozilla/cubeb/", "bylaws/libadrenotools/")) else []
    )
    return {"sha256": sha(contents), "size_bytes": len(contents),
            "gitmodules_manifest_paths": nested}


def sample_parent(path):
    root = f"dolphin-{PARENT_COMMIT}/"
    with tarfile.open(path, "w:gz") as tar:
        for suffix in ("CMakeLists.txt", ".gitmodules",
                       "Source/Core/DolphinLibretro/CMakeLists.txt"):
            content = b"TEST ONLY - no original Dolphin compiled source."
            item = tarfile.TarInfo(root + suffix)
            item.size = len(content)
            tar.addfile(item, io.BytesIO(content))
        filler = os.urandom(160_000)
        item = tarfile.TarInfo(root + "large-random-fixture.txt")
        item.size = len(filler)
        tar.addfile(item, io.BytesIO(filler))


def build(root):
    root = Path(root)
    index = json.loads(PINNED.read_text("utf-8"))
    nested_index = copy.deepcopy(json.loads(NESTED.read_text("utf-8")))
    shards = root / "shards"
    for n in range(6):
        capture_shard(index, shards / f"shard-{n}", shard_index=n,
                      shard_count=6, fetcher=fixture_archive)
    original = reconcile(index, shards, root / "fresh")
    review = root / "fresh" / "DOLPHIN_34_SOURCE_ARCHIVE_REVIEW_UNAPPROVED.json"
    nested = root / "nested"
    nested.mkdir()
    old_digest = sha(review.read_bytes())
    for parent in nested_index["parents"]:
        row = original["submodules"][parent["parent_path"]]
        parent["parent_source_archive_sha256"] = row["archive_sha256"]
        parent["parent_source_archive_size_bytes"] = row["archive_size_bytes"]
    nested_index_path = root / "nested-index.json"
    nested_index_path.write_text(json.dumps(nested_index), "utf-8")
    items = {}
    for n, parent in enumerate(nested_index["parents"]):
        for child in parent["nested"]:
            full = parent["parent_path"] + "/" + child["path"]
            items[full] = (child, parent)
    report = {
        "schema_version": 1,
        "status": NESTED_STATUS,
        "original_34_source_review_run": "42447184893",
        "original_34_source_review_manifest_sha256": old_digest,
        "dolphin_parent_commit": PARENT_COMMIT,
        "source_candidates_captured": 3,
        "pinned_nested_gitlink_tree_closure_verified": True,
        "pinned_nested_gitlink_count": 3,
        "complete_corresponding_source_verified": False,
        "source_to_dolphin_binary_verified": False,
        "transitive_build_deps_and_notices_reviewed": False,
        "independent_license_review_complete": False,
        "public_binary_distribution_approved": False,
        "archives": {},
    }
    lines = {}
    for n, (full, (child, parent)) in enumerate(sorted(items.items())):
        filename = f"dolphin-nested-{n:02d}-{child['gitlink_commit']}.tar.gz"
        contents = b"TEST NESTED SOURCE " + full.encode()
        (nested / filename).write_bytes(contents)
        report["archives"][full] = {
            "parent_gitlink_commit": parent["parent_gitlink_commit"],
            "source_repository": child["source_repository"],
            "pinned_source_commit": child["gitlink_commit"],
            "archive_filename": filename, "archive_sha256": sha(contents),
            "archive_size_bytes": len(contents),
            "root_license_notice_candidates": [],
            "compiled_into_original_dolphin_binary_verified": False,
            "source_rights_independently_reviewed": False,
        }
        lines[filename] = sha(contents)
    report_path = nested / "DOLPHIN_THREE_NESTED_SOURCE_CANDIDATES_UNAPPROVED.json"
    report_path.write_text(json.dumps(report), "utf-8")
    lines[report_path.name] = sha(report_path.read_bytes())
    (nested / "SHA256SUMS.txt").write_text(
        "".join(f"{value}  {name}\n" for name, value in sorted(lines.items())), "ascii")
    parent = root / "parent.tar.gz"
    sample_parent(parent)
    return dict(shards=shards, nested=nested, review=review, parent=parent,
                nested_index=nested_index_path, output=root / "output")


class DolphinSourceBundleContracts(unittest.TestCase):
    def test_all_38_exact_source_candidates_archived_with_no_release_approval(self):
        with TemporaryDirectory() as tmp:
            kw = build(tmp)
            record = collect(**kw)
            self.assertEqual(record["verified_direct_gitlink_count"], 34)
            self.assertEqual(record["verified_nested_gitlink_count"], 3)
            self.assertEqual(record["source_candidate_count_including_parent"], 38)
            self.assertEqual(len(record["sources"]), 38)
            for flag in ("independent_binary_to_source_match_proven",
                         "complete_corresponding_source_and_build_dependencies_verified",
                         "license_combination_approved",
                         "dolphin_sys_source_and_rights_verified",
                         "public_binary_distribution_approved"):
                self.assertIs(record[flag], False)
            out = kw["output"]
            self.assertEqual(len(list(out.iterdir())), 40)
            self.assertTrue((out / REPORT).is_file())
            for path, row in record["sources"].items():
                file = out / row["filename"]
                self.assertEqual(sha(file.read_bytes()), row["sha256"])
                self.assertEqual(file.stat().st_size, row["size_bytes"])
                self.assertFalse(row["license_review_complete"])
            checksums = (out / "SHA256SUMS.txt").read_text()
            self.assertEqual(len(checksums.splitlines()), 39)
            self.assertTrue((out / f"dolphin-parent-{PARENT_COMMIT}.tar.gz").is_file())

    def test_rejects_changed_direct_archive_and_never_outputs_binary(self):
        with TemporaryDirectory() as tmp:
            kw = build(tmp)
            files = list(kw["shards"].rglob("dolphin-submodule-*.tar.gz"))
            self.assertTrue(files)
            files[0].write_bytes(files[0].read_bytes() + b"tampered")
            with self.assertRaises(ValueError):
                collect(**kw)
            self.assertFalse(kw["output"].exists())

    def test_rejects_forged_nested_license_and_extra_sources(self):
        with TemporaryDirectory() as tmp:
            kw = build(tmp)
            manifest = kw["nested"] / "DOLPHIN_THREE_NESTED_SOURCE_CANDIDATES_UNAPPROVED.json"
            item = json.loads(manifest.read_text())
            item["public_binary_distribution_approved"] = True
            manifest.write_text(json.dumps(item))
            with self.assertRaises(ValueError):
                collect(**kw)
            self.assertFalse(kw["output"].exists())
        with TemporaryDirectory() as tmp:
            kw = build(tmp)
            (kw["nested"] / "surprise.zip").write_bytes(b"bad")
            with self.assertRaises(ValueError):
                collect(**kw)
            self.assertFalse(kw["output"].exists())

    def test_rejects_unknown_parent_source_archive(self):
        with TemporaryDirectory() as tmp:
            kw = build(tmp)
            kw["parent"].write_bytes(b"fictional source data")
            with self.assertRaises(ValueError):
                collect(**kw)
            self.assertFalse(kw["output"].exists())


if __name__ == "__main__":
    unittest.main()
