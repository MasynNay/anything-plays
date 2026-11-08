"""Source capture pins reported Git commits without claiming binary equivalence."""
from __future__ import annotations

from io import BytesIO
import hashlib
import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.capture_v30_source_snapshots import (
    _copy_url_to_archive, source_plan,
)
from fetch_mgba_core import SOURCE_REPOSITORIES


class V30SourceArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.manifest = json.loads(
            (root / "config/v3.0-preview-candidate-integrity.json").read_text("utf-8")
        )

    def test_reported_full_commits_are_exactly_ten_and_rights_unapproved(self):
        plan = source_plan(self.manifest["linux_native_cores"])
        self.assertEqual(len(plan), 11)
        self.assertEqual(sum(x["reported_commit"] is not None for x in plan.values()), 10)
        self.assertIsNone(plan["mednafen_pce_fast"]["reported_commit"])
        for name, record in plan.items():
            with self.subTest(name=name):
                self.assertEqual(record["repository"], SOURCE_REPOSITORIES[name])
                self.assertFalse(record["redistribution_reviewed"])
                self.assertFalse(record["source_to_binary_independently_verified"])

    def test_modified_or_forged_revisions_cannot_enter_source_plan(self):
        original = self.manifest["linux_native_cores"]
        for changed_field, value, error in (
            ("reported_source_commit", "latest", "incomplete upstream"),
            ("source_repository", "https://example.invalid/pretend", "upstream source"),
        ):
            records = [dict(x) for x in original]
            records[0][changed_field] = value
            with self.assertRaisesRegex(ValueError, error):
                source_plan(records)
        duplicate = [dict(x) for x in original]
        duplicate[1]["name"] = duplicate[0]["name"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            source_plan(duplicate)

    def test_downloading_source_only_checks_archive_bytes_not_distribution(self):
        memory = BytesIO()
        with tarfile.open(fileobj=memory, mode="w:gz") as tar:
            raw = b"pinned public upstream source"
            info = tarfile.TarInfo("project-sha/README.md")
            info.size = len(raw)
            tar.addfile(info, BytesIO(raw))
        expected = memory.getvalue()
        with TemporaryDirectory() as root:
            out = Path(root) / "source.tar.gz"
            with patch("tools.capture_v30_source_snapshots.urlopen",
                       return_value=BytesIO(expected)):
                evidence = _copy_url_to_archive("https://codeload.github.com/example", out)
            self.assertEqual(out.read_bytes(), expected)
            self.assertEqual(evidence["sha256"], hashlib.sha256(expected).hexdigest())
            self.assertFalse(
                evidence["submodules_and_build_dependencies_independently_archived"]
            )

    def test_rejects_oversized_and_unsafe_tarball(self):
        with TemporaryDirectory() as root:
            out = Path(root) / "source.tar.gz"
            with patch("tools.capture_v30_source_snapshots.urlopen",
                       return_value=BytesIO(b"too big")):
                with self.assertRaisesRegex(ValueError, "download limit"):
                    _copy_url_to_archive("https://codeload.github.com/example", out,
                                         limit=2)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
