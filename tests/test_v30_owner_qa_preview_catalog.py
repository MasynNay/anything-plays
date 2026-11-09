"""Pinned four-target owner-QA fingerprints must remain unapproved and exact."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools.v30_physical_qa_matrix import CATALOG_STATUS, validate_catalog


class PinnedOwnerPreviewHashesTests(unittest.TestCase):
    def test_full_offline_current_owner_catalog_only_contains_reviewed_four_targets(self):
        path = (Path(__file__).resolve().parents[1] /
                "config/v3.0-owner-qa-preview-hashes-unapproved.json")
        catalog = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(validate_catalog(catalog), catalog)
        self.assertEqual(catalog["status"], CATALOG_STATUS)
        self.assertEqual(
            catalog["source_revision"],
            "7004115e7b9d57a3ef8f44062e134a3b55410f25",
        )
        self.assertEqual(set(catalog["targets"]), {
            "windows-x64", "linux-x64", "macos-arm64", "macos-x86_64",
        })
        self.assertIs(catalog["public_release_approved"], False)
        self.assertIs(catalog["external_license_rights_approved"], False)
        self.assertIs(catalog["binary_to_source_independently_reviewed"], False)

    def test_native_architecture_specific_actual_installer_fingerprints(self):
        p = (Path(__file__).resolve().parents[1] /
             "config/v3.0-owner-qa-preview-hashes-unapproved.json")
        j = json.loads(p.read_text(encoding="utf-8"))["targets"]
        self.assertEqual(j["windows-x64"]["installer_sha256"],
                         "407cd9ccaed7b3e1a420b46847acc04e8c6207ba819da8f9c42ef6344f55d5ee")
        self.assertEqual(j["linux-x64"]["installer_sha256"],
                         "db38caa17f0fee117b63c6d616cb876da408b7d9a1b04d1f548e906a7ff7520d")
        self.assertEqual(j["macos-arm64"]["installer_sha256"],
                         "ad079cbdb518e7f0a9e0e93c89544b17cbf0a3703878c0b365d72cea648fac25")
        self.assertEqual(j["macos-x86_64"]["installer_sha256"],
                         "f83aca8dd3965c60aeb690c2a8a8b862239131a8e3ed705fd3a5c1df10ec14f8")
        self.assertEqual(
            j["macos-arm64"]["installer_filename"],
            j["macos-x86_64"]["installer_filename"],
        )
        self.assertNotEqual(
            j["macos-arm64"]["installer_sha256"],
            j["macos-x86_64"]["installer_sha256"],
        )
        self.assertIn("~alpha1", j["linux-x64"]["installer_filename"])
        self.assertEqual({k:v["installer_size_bytes"] for k,v in j.items()}, {
            "windows-x64": 67893022,
            "linux-x64": 100714864,
            "macos-arm64": 107319945,
            "macos-x86_64": 94451784,
        })

    def test_reviewer_manifest_does_not_imply_licensing_or_real_gameplay(self):
        root = Path(__file__).resolve().parents[1]
        readme = (root/"README.md").read_text("utf-8")
        docs = (root/"docs/V3_PHYSICAL_QA_RUNBOOK.md").read_text("utf-8")
        self.assertIn("config/v3.0-owner-qa-preview-hashes-unapproved.json", docs)
        self.assertIn("42455076101", docs)
        self.assertIn("42455076101", readme)
        self.assertIn("NOT approved", docs)
        self.assertNotIn("gh release create", docs)


if __name__ == "__main__":
    unittest.main()
