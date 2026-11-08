"""4-target production artifact emitter must fail closed without source rights."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from tools.emit_v30_production_provenance import (
    NATIVE_MAP, prepare_production_artifact, validate_source_inventory,
)
from tools.stage_v30_release_assets import expected_installers
from tools.v30_release_lock import CORE_NAMES, TARGETS as NATIVE_TARGETS


def digest(data):
    return hashlib.sha256(data).hexdigest()


def synthetic_evidence():
    targets = {}
    source_targets = {}
    for target in NATIVE_TARGETS:
        ext = (".dll" if target.startswith("windows") else
               ".so" if target.startswith("linux") else ".dylib")
        cores = {}
        source_cores = {}
        for name in CORE_NAMES:
            core_sha = digest((name + target).encode("utf-8"))
            cores[name] = {
                "file": name + "_libretro" + ext,
                "native_sha256": core_sha,
                "native_size_bytes": 1000,
                "original_archive_sha256": digest((name + target + "zip").encode("utf-8")),
                "original_archive_size_bytes": 1100,
                "source_commit_sha": "a" * 40,
                "upstream_source_repository": "https://github.com/libretro/" + name,
                "redistribution_approved": True,
                "corresponding_source_verified": True,
            }
            source_cores[name] = {
                "source_commit_sha": cores[name]["source_commit_sha"],
                "native_sha256": core_sha,
                "source_archive_sha256": digest((name + "source").encode()),
                "source_build_dependencies_reviewed": True,
            }
        sys_sha = digest((target + "Sys").encode("utf-8"))
        targets[target] = {
            "approved_for_distribution": True,
            "cores": cores,
            "dolphin_sys": {
                "original_archive_sha256": sys_sha,
                "original_archive_size_bytes": 100,
                "source_correspondence_verified": True,
                "redistribution_approved": True,
            },
        }
        source_targets[target] = {
            "cores": source_cores,
            "dolphin_sys": {
                "original_archive_sha256": sys_sha,
                "source_and_license_reviewed": True,
            },
        }
    lock = {
        "schema_version": 1,
        "approved_for_binary_distribution": True,
        "license_compatibility_reviewed": True,
        "corresponding_source_inventory_verified": True,
        "native_core_count": 11,
        "system_profile_count": 18,
        "targets": targets,
    }
    inventory = {
        "schema_version": 1,
        "native_core_count": 11,
        "approved_for_public_binary_distribution": True,
        "corresponding_source_inventory_verified": True,
        "targets": source_targets,
    }
    return lock, inventory


def bundle_manifest(lock, target):
    row = lock["targets"][NATIVE_MAP[target]]
    cores = [
        {
            "name": name,
            "file": core["file"],
            "sha256": core["native_sha256"],
            "size_bytes": core["native_size_bytes"],
            "archive_sha256": core["original_archive_sha256"],
            "archive_size_bytes": core["original_archive_size_bytes"],
            "source_repository_url": core["upstream_source_repository"],
        }
        for name, core in row["cores"].items()
    ]
    return {
        "build_platform": "linux",
        "build_architecture": "x86_64",
        "cores": cores,
        "dolphin_system_assets": {
            "archive_sha256": row["dolphin_sys"]["original_archive_sha256"],
            "archive_size_bytes": row["dolphin_sys"]["original_archive_size_bytes"],
        },
    }


class ProductionArtifactEvidenceTests(unittest.TestCase):
    def test_emits_exact_two_file_release_artifact_with_pinned_source(self):
        lock, source = synthetic_evidence()
        with TemporaryDirectory() as temp:
            root = Path(temp)
            filename = expected_installers("3.0.0")[3]
            installer = root / filename
            installer.write_bytes(b"synthetic release candidate " * 70000)
            record = prepare_production_artifact(
                target="linux-x64", version="3.0.0",
                source_commit="a" * 40, installer=installer,
                bundle_manifest=bundle_manifest(lock, "linux-x64"),
                lock=lock, inventory=source,
                review_text="APPROVED-3.0-DISTRIBUTION " + ("reviewed synthetic test only " * 20),
                output=root/"production", lock_digest="b"*64, source_digest="c"*64,
            )
            self.assertEqual(
                {p.name for p in (root/"production").iterdir()},
                {filename, "PRODUCTION_PROVENANCE.json"},
            )
            self.assertEqual(record["installer_sha256"], digest(installer.read_bytes()))
            self.assertEqual(record["release_mode"], "APPROVED-IMMUTABLE-PRODUCTION")
            self.assertTrue(record["public_binary_distribution_approved"])
            self.assertEqual(record["native_cores_bundled"], 11)

    def test_refuses_missing_source_or_unverified_dependencies(self):
        lock, source = synthetic_evidence()
        source["approved_for_public_binary_distribution"] = False
        with self.assertRaisesRegex(ValueError, "Missing approved"):
            validate_source_inventory(lock, source)
        source["approved_for_public_binary_distribution"] = True
        source["targets"]["linux-x86_64"]["cores"]["mgba"][
            "source_build_dependencies_reviewed"
        ] = False
        with self.assertRaisesRegex(ValueError, "Unreviewed source"):
            validate_source_inventory(lock, source)

    def test_rejects_wrong_architecture_and_unapproved_review(self):
        lock, source = synthetic_evidence()
        with TemporaryDirectory() as temp:
            root = Path(temp)
            name = expected_installers("3.0.0")[3]
            installer = root/name
            installer.write_bytes(b"synthetic " * 150000)
            common = dict(target="linux-x64", version="3.0.0",
                          source_commit="a"*40, installer=installer,
                          lock=lock, inventory=source,
                          output=root/"production",
                          lock_digest="b"*64, source_digest="c"*64)
            with self.assertRaisesRegex(ValueError, "Missing reviewed"):
                prepare_production_artifact(
                    **common, review_text="not approved",
                    bundle_manifest=bundle_manifest(lock, "linux-x64"),
                )
            wrong = bundle_manifest(lock, "macos-x64")
            with self.assertRaisesRegex(ValueError, "another target|bundle core mismatch"):
                prepare_production_artifact(
                    **common,
                    review_text="APPROVED-3.0-DISTRIBUTION " + ("review text "*24),
                    bundle_manifest=wrong,
                )
            self.assertFalse((root/"production").exists())

    def test_real_cli_stays_blocked_with_current_unapproved_manifest(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-m", "tools.emit_v30_production_provenance",
             "--help"],
            cwd=root, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--core-provenance", result.stdout)
        self.assertEqual(len(CORE_NAMES), 11)
        self.assertEqual(len(NATIVE_TARGETS), 4)


if __name__ == "__main__":
    unittest.main()
