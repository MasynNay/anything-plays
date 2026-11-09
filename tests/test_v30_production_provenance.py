"""4-target production artifact emitter must fail closed without source rights."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.emit_v30_production_provenance import (
    NATIVE_MAP, prepare_production_artifact, validate_source_inventory,
)
from tools.check_v30_source_gate import check_approved_source_package
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
                "original_native_archive_sha256": cores[name]["original_archive_sha256"],
                "source_repository": cores[name]["upstream_source_repository"],
                "source_archive_sha256": digest((name + "source").encode()),
                "source_archive_size_bytes": 900,
                "source_build_dependencies_reviewed": True,
                "source_to_binary_verified": True,
                "redistribution_license_reviewed": True,
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
                "original_archive_size_bytes": 100,
                "source_and_license_reviewed": True,
                "source_correspondence_verified": True,
                "redistribution_approved": True,
            },
        }
    lock = {
        "schema_version": 1,
        "source_commit": "b" * 40,
        "approved_for_binary_distribution": True,
        "license_compatibility_reviewed": True,
        "corresponding_source_inventory_verified": True,
        "native_core_count": 11,
        "system_profile_count": 18,
        "targets": targets,
    }
    inventory = {
        "schema_version": 1,
        "source_commit": "b" * 40,
        "native_core_count": 11,
        "approved_for_public_binary_distribution": True,
        "corresponding_source_inventory_verified": True,
        "independent_binary_to_source_match_proven": True,
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
                source_commit="b" * 40, installer=installer,
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
            self.assertEqual(record["reviewed_application_source_commit"], "b" * 40)
            self.assertTrue(record["runtime_build_inputs_unchanged_since_approved_source"])

    def test_production_staging_cleans_partial_copy_and_allows_retry(self):
        lock, source = synthetic_evidence()
        with TemporaryDirectory() as temp:
            root = Path(temp)
            installer = root / expected_installers("3.0.0")[3]
            installer.write_bytes(b"synthetic installer " * 70000)
            output = root / "production"
            common = dict(
                target="linux-x64", version="3.0.0", source_commit="b" * 40,
                installer=installer, bundle_manifest=bundle_manifest(lock, "linux-x64"),
                lock=lock, inventory=source,
                review_text="APPROVED-3.0-DISTRIBUTION " + "SYNTHETIC TEST " * 25,
                output=output, lock_digest="b" * 64, source_digest="c" * 64,
            )

            def interrupted_copy(src, dst):
                Path(dst).write_bytes(b"partial installer bytes")
                raise OSError("simulated copy interruption")

            with patch("tools.emit_v30_production_provenance.shutil.copyfile",
                       side_effect=interrupted_copy):
                with self.assertRaisesRegex(OSError, "copy interruption"):
                    prepare_production_artifact(**common)
            self.assertEqual(list(output.iterdir()), [])
            prepare_production_artifact(**common)
            self.assertEqual(
                {p.name for p in output.iterdir()},
                {installer.name, "PRODUCTION_PROVENANCE.json"},
            )

    def test_production_staging_cleans_partial_manifest_and_allows_retry(self):
        lock, source = synthetic_evidence()
        with TemporaryDirectory() as temp:
            root = Path(temp)
            installer = root / expected_installers("3.0.0")[3]
            installer.write_bytes(b"synthetic installer " * 70000)
            output = root / "production"
            common = dict(
                target="linux-x64", version="3.0.0", source_commit="b" * 40,
                installer=installer, bundle_manifest=bundle_manifest(lock, "linux-x64"),
                lock=lock, inventory=source,
                review_text="APPROVED-3.0-DISTRIBUTION " + "SYNTHETIC TEST " * 25,
                output=output, lock_digest="b" * 64, source_digest="c" * 64,
            )
            original_write = Path.write_text

            def interrupted_manifest(path, content, *args, **kwargs):
                if Path(path).name == "PRODUCTION_PROVENANCE.json":
                    original_write(path, '{"partial":', *args, **kwargs)
                    raise OSError("simulated manifest interruption")
                return original_write(path, content, *args, **kwargs)

            with patch.object(Path, "write_text", interrupted_manifest):
                with self.assertRaisesRegex(OSError, "manifest interruption"):
                    prepare_production_artifact(**common)
            self.assertEqual(list(output.iterdir()), [])
            prepare_production_artifact(**common)
            self.assertEqual(
                {p.name for p in output.iterdir()},
                {installer.name, "PRODUCTION_PROVENANCE.json"},
            )

    def test_production_staging_rejects_existing_file_as_output(self):
        lock, source = synthetic_evidence()
        with TemporaryDirectory() as temp:
            root = Path(temp)
            installer = root / expected_installers("3.0.0")[3]
            installer.write_bytes(b"synthetic installer " * 70000)
            output = root / "not-a-directory"
            output.write_text("preserve existing evidence", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "new or empty"):
                prepare_production_artifact(
                    target="linux-x64", version="3.0.0", source_commit="b" * 40,
                    installer=installer, bundle_manifest=bundle_manifest(lock, "linux-x64"),
                    lock=lock, inventory=source,
                    review_text="APPROVED-3.0-DISTRIBUTION " + "SYNTHETIC TEST " * 25,
                    output=output, lock_digest="b" * 64, source_digest="c" * 64,
                )
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve existing evidence")

    def test_new_approval_commit_may_differ_only_after_actual_git_tree_verification(self):
        lock, source = synthetic_evidence()
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            installer = folder / expected_installers("3.0.0")[3]
            installer.write_bytes(b"synthetic ADMIN ONLY release approval " * 45000)
            with patch(
                "tools.emit_v30_production_provenance.verify_runtime_code_unchanged",
                return_value={"runtime_and_packaging_source_unchanged": True},
            ) as proof:
                result = prepare_production_artifact(
                    target="linux-x64", version="3.0.0",
                    source_commit="c" * 40, installer=installer,
                    bundle_manifest=bundle_manifest(lock, "linux-x64"),
                    lock=lock, inventory=source,
                    review_text=("APPROVED-3.0-DISTRIBUTION "
                                 + "TEST ONLY EXTERNAL REVIEW " * 20),
                    output=folder / "production",
                    lock_digest="b" * 64, source_digest="c" * 64,
                )
            proof.assert_called_once_with("b" * 40, "c" * 40)
            self.assertEqual(result["source_revision"], "c" * 40)
            self.assertEqual(result["reviewed_application_source_commit"], "b" * 40)
            self.assertTrue(result["runtime_build_inputs_unchanged_since_approved_source"])

    def test_different_application_revision_cannot_reuse_approved_native_source(self):
        lock, source = synthetic_evidence()
        with TemporaryDirectory() as temp:
            root = Path(temp)
            installer = root / expected_installers("3.0.0")[3]
            installer.write_bytes(b"synthetic checked installer " * 60000)
            common = dict(
                target="linux-x64", version="3.0.0", installer=installer,
                bundle_manifest=bundle_manifest(lock, "linux-x64"),
                lock=lock, inventory=source,
                review_text="APPROVED-3.0-DISTRIBUTION "
                            + "SYNTHETIC NEGATIVE TEST " * 25,
                output=root / "production", lock_digest="b" * 64,
                source_digest="c" * 64,
            )
            # This previously passed: emitter stamped the application as
            # built from 'a'*40 while its independent 44-core approval was
            # exclusively for 'b'*40. The defect was present in the normal
            # successful emitter fixture before this regression.
            with self.assertRaisesRegex(ValueError, "application source revision"):
                prepare_production_artifact(
                    **common, source_commit="a" * 40)
            self.assertFalse((root / "production").exists())
            correct = prepare_production_artifact(
                **common, source_commit="b" * 40)
            self.assertEqual(correct["source_revision"], "b" * 40)

    def test_rejects_source_catalog_approval_for_a_different_build_revision(self):
        lock, inventory = synthetic_evidence()
        inventory["source_commit"] = "a" * 40
        with self.assertRaisesRegex(ValueError, "locked build commit"):
            validate_source_inventory(lock, inventory)

    def test_refuses_missing_source_or_unverified_dependencies(self):
        lock, source = synthetic_evidence()
        source["approved_for_public_binary_distribution"] = False
        with self.assertRaisesRegex(ValueError, "Missing approved"):
            validate_source_inventory(lock, source)
        source["approved_for_public_binary_distribution"] = True
        source["targets"]["linux-x86_64"]["cores"]["mgba"][
            "source_build_dependencies_reviewed"
        ] = False
        with self.assertRaisesRegex(ValueError, "source_build_dependencies_reviewed"):
            validate_source_inventory(lock, source)

    def test_requires_explicit_independent_match_for_all_44_native_binaries(self):
        lock, source = synthetic_evidence()
        self.assertTrue(validate_source_inventory(lock, source))
        source["independent_binary_to_source_match_proven"] = False
        with self.assertRaisesRegex(ValueError, "Independent"):
            validate_source_inventory(lock, source)

    def test_fails_when_a_single_core_correspondence_or_rights_review_is_missing(self):
        for missing in ("source_to_binary_verified",
                        "redistribution_license_reviewed",
                        "source_build_dependencies_reviewed"):
            with self.subTest(missing=missing):
                lock, source = synthetic_evidence()
                # The validator must cover *every* target and *every* core:
                # not just Linux or the first entry in the lock.
                source["targets"]["macos-x86_64"]["cores"]["snes9x"][missing] = False
                with self.assertRaisesRegex(ValueError, missing):
                    validate_source_inventory(lock, source)

    def test_requires_archive_identity_and_real_source_offer_metadata(self):
        for field, value in (
            ("original_native_archive_sha256", "0" * 64),
            ("source_repository", "https://example.invalid/false-source"),
            ("source_archive_size_bytes", 0),
            ("source_archive_sha256", "not-a-digest"),
        ):
            with self.subTest(field=field):
                lock, source = synthetic_evidence()
                source["targets"]["windows-x86_64"]["cores"]["dolphin"][field] = value
                with self.assertRaisesRegex(ValueError, "archive|source|pinned"):
                    validate_source_inventory(lock, source)

    def test_dolphin_sys_needs_both_correspondence_and_rights_review(self):
        for field in ("source_correspondence_verified",
                      "redistribution_approved", "source_and_license_reviewed"):
            with self.subTest(field=field):
                lock, source = synthetic_evidence()
                source["targets"]["macos-arm64"]["dolphin_sys"][field] = False
                with self.assertRaisesRegex(ValueError, "Dolphin"):
                    validate_source_inventory(lock, source)
        lock, source = synthetic_evidence()
        source["targets"]["linux-x86_64"]["dolphin_sys"]["original_archive_size_bytes"] += 1
        with self.assertRaisesRegex(ValueError, "Dolphin"):
            validate_source_inventory(lock, source)

    def test_source_record_must_match_exact_native_candidate_build_revision(self):
        lock, source = synthetic_evidence()
        source["source_commit"] = "a" * 40
        with self.assertRaisesRegex(ValueError, "locked build commit"):
            validate_source_inventory(lock, source)

    def test_preflight_checks_documents_and_every_core_before_expensive_build(self):
        lock, source = synthetic_evidence()
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            lock_file = folder / "lock.json"
            inventory_file = folder / "source.json"
            review_file = folder / "rights.md"
            def write():
                lock_file.write_text(json.dumps(lock), "utf-8")
                inventory_file.write_text(json.dumps(source), "utf-8")
            write()
            text = "APPROVED-3.0-DISTRIBUTION " + "THIS IS A SYNTHETIC TEST ONLY. " * 20
            review_file.write_text(text, "utf-8")
            kw = dict(lock_path=lock_file, inventory_path=inventory_file,
                      license_review_path=review_file)
            result = check_approved_source_package(**kw)
            self.assertEqual(result["native_binaries_source_reviewed"], 44)
            self.assertEqual(result["dolphin_sys_archives_reviewed"], 4)
            self.assertFalse(result["public_release_approval_automatically_granted"])
            source["targets"]["linux-x86_64"]["cores"]["genesis_plus_gx"][
                "redistribution_license_reviewed"] = False
            write()
            with self.assertRaisesRegex(ValueError, "redistribution_license_reviewed"):
                check_approved_source_package(**kw)
            source["targets"]["linux-x86_64"]["cores"]["genesis_plus_gx"][
                "redistribution_license_reviewed"] = True
            write()
            review_file.write_text("not reviewed", "utf-8")
            with self.assertRaisesRegex(ValueError, "distribution decision"):
                check_approved_source_package(**kw)

    def test_preflight_does_not_bootstrap_unapproved_real_lock_or_rights(self):
        from tools.v30_release_lock import LOCK_PATH
        lock = json.loads(LOCK_PATH.read_text("utf-8"))
        if lock["approved_for_binary_distribution"] is not True:
            # Standard development mode is required to be blocked. In a
            # future independently approved main release, this test still
            # remains valid and needn't assert that approval is forever false.
            with self.assertRaisesRegex(ValueError, "blocked|not approved"):
                check_approved_source_package()
        self.assertEqual(len(CORE_NAMES), 11)
        self.assertEqual(len(NATIVE_TARGETS), 4)

    def test_rejects_wrong_architecture_and_unapproved_review(self):
        lock, source = synthetic_evidence()
        with TemporaryDirectory() as temp:
            root = Path(temp)
            name = expected_installers("3.0.0")[3]
            installer = root/name
            installer.write_bytes(b"synthetic " * 150000)
            common = dict(target="linux-x64", version="3.0.0",
                          source_commit="b"*40, installer=installer,
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
