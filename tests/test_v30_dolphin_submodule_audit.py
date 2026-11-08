"""Dolphin's exact source Gitlinks are pinned, never treated as binary clearance."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools.check_v30_dolphin_submodules import (
    PINNED, PARENT_COMMIT, gitmodules, validate_index, verify_upstream,
)


class DolphinSubmoduleAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads(PINNED.read_text("utf-8"))

    def test_exact_34_upstream_gitlink_revisions_and_unapproved_rights(self):
        records = validate_index(self.index)
        self.assertEqual(len(records), 34)
        self.assertEqual(self.index["parent_commit"], PARENT_COMMIT)
        self.assertIn("Externals/FFmpeg-bin", records)
        self.assertIn("Externals/mGBA/mgba", records)
        self.assertEqual(
            records["Externals/bzip2/bzip2"]["url"],
            "https://gitlab.com/bzip2/bzip2.git",
        )
        self.assertFalse(self.index["public_binary_redistribution_approved"])
        self.assertTrue(all(
            not row["submodule_archive_captured"]
            and not row["corresponding_binary_verified"]
            and not row["license_reviewed"]
            for row in self.index["submodules"]
        ))

    def test_upstream_tree_and_gitmodules_match_frozen_map(self):
        links = validate_index(self.index)
        tree = {
            "sha": self.index["parent_git_tree_sha"],
            "truncated": False,
            "tree": [{"path": name, "type": "commit", "sha": row["sha"]}
                     for name, row in links.items()],
        }
        modules = "\n".join(
            f'[submodule "{name}"]\n\tpath = {name}\n\turl = {row["url"]}'
            for name, row in links.items()
        )
        self.assertEqual(len(gitmodules(modules)), 34)
        self.assertEqual(verify_upstream(self.index, tree, modules), 34)
        wrong_tree = copy.deepcopy(tree)
        wrong_tree["tree"][0]["sha"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "Gitlink or URL mismatch"):
            verify_upstream(self.index, wrong_tree, modules)
        wrong_tree["tree"] = tree["tree"]
        wrong_tree["truncated"] = True
        with self.assertRaisesRegex(ValueError, "Git tree identity"):
            verify_upstream(self.index, wrong_tree, modules)

    def test_never_accept_fake_gitlinks_paths_or_approval_flags(self):
        for operation, pattern in (
            (lambda d: d["submodules"][0].update(gitlink_commit="main"), "pinned gitlink"),
            (lambda d: d["submodules"][0].update(path="Externals/../escape"), "Unsafe submodule"),
            (lambda d: d["submodules"][0].update(source_repository="https://evil.invalid/a"), "pinned gitlink"),
            (lambda d: d["submodules"][0].update(license_reviewed=True), "Unverified"),
            (lambda d: d.update(public_binary_redistribution_approved=True), "unreviewed approvals"),
            (lambda d: d["submodules"].pop(), "34 pinned"),
        ):
            altered = copy.deepcopy(self.index)
            operation(altered)
            with self.subTest(pattern=pattern):
                with self.assertRaisesRegex(ValueError, pattern):
                    validate_index(altered)

    def test_cli_checks_frozen_index_without_network_or_source_download(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-m", "tools.check_v30_dolphin_submodules"],
            cwd=root, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("34 immutable Dolphin gitlink identities", result.stdout)
        self.assertIn("UNAPPROVED", result.stdout)


if __name__ == "__main__":
    unittest.main()
