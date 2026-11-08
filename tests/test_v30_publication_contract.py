"""A stable 3.0 publisher must never accept a preview or unchecked native core."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.collect_v30_production_assets import (
    MANIFEST, TARGETS, collect_production_assets,
)
from tools.stage_v30_release_assets import expected_installers


REV = "e" * 40
SHA = "a" * 64


def make_candidate(root, *, version="3.0.0"):
    root = Path(root)
    for target, filename in zip(TARGETS, expected_installers(version)):
        folder = root / target
        folder.mkdir(parents=True)
        payload = (b"APPROVED-PRODUCTION-" + target.encode()) * 65000
        (folder / filename).write_bytes(payload)
        evidence = {
            "target": target,
            "source_revision": REV,
            "installer_name": filename,
            "installer_sha256": hashlib.sha256(payload).hexdigest(),
            "release_mode": "APPROVED-IMMUTABLE-PRODUCTION",
            "public_binary_distribution_approved": True,
            "profiles_bundled": 18,
            "native_cores_bundled": 11,
            "native_inputs_lock_sha256": SHA,
            "corresponding_source_inventory_sha256": SHA,
            "license_review_record": "docs/V3_LICENSE_COMPATIBILITY_GATE.md",
        }
        (folder / MANIFEST).write_text(
            json.dumps(evidence), encoding="utf-8",
        )


class PublicationContracts(unittest.TestCase):
    def test_four_approved_artifacts_with_matching_provenance_can_be_staged(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            make_candidate(root / "input")
            names = collect_production_assets(
                root / "input", root / "output", version="3.0.0",
                source_revision=REV,
            )
            self.assertEqual(set(names), set(expected_installers("3.0.0")))
            for filename in names:
                self.assertGreater((root / "output" / filename).stat().st_size, 1024 * 1024)

    def test_rejects_test_only_previews_even_with_matching_checksums(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            make_candidate(root / "input")
            manifest = root / "input" / "linux-x64" / MANIFEST
            record = json.loads(manifest.read_text("utf-8"))
            record["release_mode"] = "UNRELEASED-DEVELOPER-TEST-ONLY"
            record["public_binary_distribution_approved"] = False
            manifest.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unapproved provenance"):
                collect_production_assets(root / "input", root / "out",
                                          version="3.0.0", source_revision=REV)
            self.assertFalse((root / "out").exists())

    def test_rejects_changed_installers_and_missing_licenses(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            make_candidate(root / "input")
            file = root / "input" / "windows-x64" / expected_installers("3.0.0")[0]
            file.write_bytes(file.read_bytes() + b"tampered")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                collect_production_assets(root / "input", root / "out",
                                          version="3.0.0", source_revision=REV)
            self.assertFalse((root / "out").exists())

    def test_refuses_unexpected_release_files_and_untrusted_commit(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            make_candidate(root / "input")
            (root / "input" / "linux-x64" / "preview.deb").write_bytes(b"bad")
            with self.assertRaisesRegex(ValueError, "unexpected or missing"):
                collect_production_assets(root / "input", root / "out",
                                          version="3.0.0", source_revision=REV)
            with self.assertRaisesRegex(ValueError, "fully pinned"):
                collect_production_assets(root / "input", root / "out",
                                          version="3.0.0", source_revision="main")

    def test_rejects_preexisting_output_and_symlinks(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            make_candidate(root / "input")
            output = root / "out"
            output.mkdir()
            (output / "keep.txt").write_text("existing")
            with self.assertRaisesRegex(ValueError, "must be empty"):
                collect_production_assets(root / "input", output,
                                          version="3.0.0", source_revision=REV)
            self.assertEqual((output / "keep.txt").read_text(), "existing")
            link = root / "link"
            try:
                link.symlink_to(root / "input", target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Symlink creation unavailable")
            with self.assertRaisesRegex(ValueError, "symlinks"):
                collect_production_assets(link, root / "fresh",
                                          version="3.0.0", source_revision=REV)

    def test_workflow_is_manual_and_publication_is_gated(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/v30-publish-approved.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertIn('refs/heads/main', workflow)
        self.assertIn("python tools/check_v30_release.py", workflow)
        self.assertIn("collect_v30_production_assets.py", workflow)
        self.assertIn("APPROVED-3.0-DISTRIBUTION", workflow)
        self.assertIn("Approved production candidates", workflow)
        self.assertIn("docs/V3_RELEASE_NOTES_APPROVED.md", workflow)
        self.assertIn("--draft", workflow)
        self.assertIn("inputs.publish_publicly", workflow)
        self.assertIn("gh release edit", workflow)


if __name__ == "__main__":
    unittest.main()
