"""Git-approved runtime source must not depend on a self-referential commit."""
from __future__ import annotations
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from tools.verify_v30_reviewed_runtime_code import (
    REVIEW_ONLY_FILES, verify_runtime_code_unchanged,
)


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True,
                          text=True, check=True, timeout=10).stdout.strip()


def write(root, path, data):
    p=root/path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data, "utf-8")


def commit(root, label):
    git(root, "add", ".")
    git(root, "commit", "-qm", label)
    return git(root, "rev-parse", "HEAD")


class ReviewedGitRuntimeSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "local-test@example.invalid")
        git(self.root, "config", "user.name", "Source review regression")
        write(self.root, "app.py", "print('original application')\n")
        write(self.root, "anything_plays/runner.py", "print('native frontend')\n")
        write(self.root, "packaging/build_linux_deb.sh", "# reviewed\n")
        write(self.root, "tools/check_v30_release.py", "# reviewed\n")
        self.reviewed=commit(self.root, "Frozen independently reviewed app code")

    def approvals(self):
        write(self.root, "config/v3.0-core-lock.json", '{"approved": false}\n')
        write(self.root, "config/v3.0-release-acceptance.json", '{"status":"reviewed"}\n')
        write(self.root, "config/v3.0-corresponding-source-inventory.json",
              '{"rights":"reviewed"}\n')
        write(self.root, "docs/V3_LICENSE_COMPATIBILITY_APPROVED.md", "signoff")
        write(self.root, "docs/V3_RELEASE_NOTES_APPROVED.md", "release notes")
        write(self.root, "CONTINUE_HERE.md", "journal")
        return commit(self.root, "Administrative review added after source freeze")

    def test_approved_commit_may_add_only_explicit_release_metadata(self):
        actual=self.approvals()
        self.assertNotEqual(self.reviewed, actual)
        evidence=verify_runtime_code_unchanged(self.reviewed, actual, repo=self.root)
        self.assertTrue(evidence["runtime_and_packaging_source_unchanged"])
        self.assertFalse(evidence["release_approval_automatically_granted"])
        self.assertEqual(evidence["actual_build_commit"], actual)
        self.assertEqual(evidence["reviewed_application_source_commit"], self.reviewed)
        self.assertEqual(set(evidence["metadata_only_git_differences"]), REVIEW_ONLY_FILES)
        self.assertEqual(len(REVIEW_ONLY_FILES), 6)

    def test_source_checkout_that_is_byte_identical_is_valid(self):
        evidence=verify_runtime_code_unchanged(
            self.reviewed, self.reviewed, repo=self.root)
        self.assertEqual(evidence["metadata_only_git_differences"], [])
        self.assertTrue(evidence["runtime_and_packaging_source_unchanged"])

    def test_any_updated_binary_build_input_blocks_metadata_only_release(self):
        approved = self.approvals()
        for path in ("app.py", "anything_plays/runner.py",
                     "packaging/build_linux_deb.sh", "tools/check_v30_release.py",
                     ".github/workflows/v30-production-candidates.yml",
                     "docs/NEW_UNREVIEWED.md", "requirements.txt"):
            with self.subTest(path=path):
                # Isolate EACH forbidden path against the genuine reviewed
                # approval-only baseline. Otherwise the first dirty app.py
                # would make all later subtests spuriously pass.
                git(self.root, "reset", "--hard", approved)
                git(self.root, "clean", "-fd")
                write(self.root, path, "unreviewed runtime/ci/source edit\n")
                actual=commit(self.root, "Unreviewed code changed")
                with self.assertRaisesRegex(ValueError, "Unreviewed application/build source"):
                    verify_runtime_code_unchanged(self.reviewed, actual, repo=self.root)

    def test_wrong_head_dirty_checkout_missing_or_fake_git_sha_fail_closed(self):
        actual=self.approvals()
        with self.assertRaisesRegex(ValueError, "not checkout HEAD"):
            verify_runtime_code_unchanged(actual, self.reviewed, repo=self.root)
        with self.assertRaisesRegex(ValueError, "Git verification failed"):
            verify_runtime_code_unchanged("a"*40, actual, repo=self.root)
        with self.assertRaisesRegex(ValueError, "immutable full"):
            verify_runtime_code_unchanged("latest", actual, repo=self.root)
        write(self.root, "app.py", "not committed\n")
        with self.assertRaisesRegex(ValueError, "uncommitted tracked"):
            verify_runtime_code_unchanged(self.reviewed, actual, repo=self.root)

    def test_approved_production_ci_fetches_git_history_and_checks_tree(self):
        root=Path(__file__).resolve().parents[1]
        workflow=(root/".github/workflows/v30-production-candidates.yml").read_text("utf-8")
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("tools.verify_v30_reviewed_runtime_code", workflow)
        self.assertIn('GITHUB_SHA', workflow)
        self.assertIn("reviewed-source-commit",workflow)
        emitter=(root/"tools/emit_v30_production_provenance.py").read_text("utf-8")
        self.assertIn("verify_runtime_code_unchanged", emitter)
        self.assertIn("reviewed_application_source_commit", emitter)
        self.assertIn("runtime_build_inputs_unchanged_since_approved_source", emitter)
        self.assertNotIn("git reset --hard", workflow)
        self.assertNotIn("continue-on-error: true", workflow)


if __name__=="__main__":
    unittest.main()
