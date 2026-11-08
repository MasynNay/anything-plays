"""Four real-platform QA packets must match four installer byte hashes."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import v30_physical_qa as qa
from tools import v30_physical_qa_matrix as matrix


def create_fixture(root: Path, *, complete=False):
    installers = {}
    records = root / "owner-packets"
    records.mkdir()
    for target in sorted(qa.TARGETS):
        ext = matrix.TARGET_SUFFIX[target]
        name = f"AnythingPlays-3.0.0-{target}{ext}"
        candidate = root / name
        candidate.write_bytes((target + "\n").encode() * 70)
        installers[target] = candidate
        with patch.object(qa, "detected_target", return_value=target):
            report = qa.create_report(candidate, commit="a"*40)
        if complete:
            for check in qa.HOST_CHECKS:
                report["host_checks"][check] = "pass"
            for system in report["console_checks"]:
                for check in qa.CONSOLE_CHECKS:
                    report["console_checks"][system][check] = "pass"
        # Both records are *only* owner reports; don't forge review rights.
        qa.export_review(report, records / target)
    return matrix.hash_four_installers("a"*40, installers), records, installers


class FourOSPhysicalQATests(unittest.TestCase):
    def test_hash_real_frozen_four_local_installers_and_source_commit(self):
        with TemporaryDirectory() as folder:
            catalog, packets, installers = create_fixture(Path(folder))
            self.assertEqual(set(catalog["targets"]), qa.TARGETS)
            self.assertEqual(catalog["source_revision"], "a"*40)
            self.assertEqual(catalog["status"], matrix.CATALOG_STATUS)
            self.assertIs(catalog["public_release_approved"], False)
            for target, path in installers.items():
                row = catalog["targets"][target]
                self.assertEqual(row["installer_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertEqual(row["installer_size_bytes"], path.stat().st_size)
                self.assertEqual(row["installer_filename"], path.name)
            self.assertEqual(matrix.validate_catalog(catalog), catalog)
            self.assertEqual(len(list(packets.iterdir())), 4)

    def test_initial_unperformed_600_checks_are_reported_not_passed(self):
        with TemporaryDirectory() as folder:
            catalog, packets, _ = create_fixture(Path(folder))
            result = matrix.reconcile(catalog, packets)
            self.assertEqual(result["platform_count"], 4)
            self.assertEqual(result["required_observations"], 600)
            self.assertEqual(result["counts"], {"fail": 0, "not-tested": 600, "pass": 0})
            self.assertEqual(set(result["targets"]), qa.TARGETS)
            for target in qa.TARGETS:
                row = result["targets"][target]
                self.assertEqual(row["total_required_observations"], 150)
                self.assertEqual(len(row["outstanding_manual_checks"]), 150)
                self.assertFalse(row["all_owner_observations_pass"])
                self.assertFalse(row["independently_verified_on_hardware"])
            self.assertFalse(result["owner_reports_complete_for_independent_review"])
            self.assertFalse(result["public_release_approved"])
            self.assertFalse(result["external_license_redistribution_reviewed"])

    def test_all_owner_reports_pass_but_independent_rights_remain_false(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            catalog, packets, _ = create_fixture(folder, complete=True)
            result = matrix.reconcile(catalog, packets)
            self.assertEqual(result["counts"], {"fail": 0, "not-tested": 0, "pass": 600})
            self.assertTrue(result["owner_reports_complete_for_independent_review"])
            for key in ("independent_hardware_reviewed",
                        "source_to_binary_correspondence_reviewed",
                        "external_license_redistribution_reviewed",
                        "production_approval", "public_release_approved"):
                self.assertIs(result[key], False)
            out = folder / "evidence"
            summary = matrix.export_summary(result, out)
            self.assertEqual({p.name for p in out.iterdir()},
                             {matrix.SUMMARY_NAME, matrix.HASHFILE})
            self.assertEqual(
                (out / matrix.HASHFILE).read_bytes(),
                (hashlib.sha256(summary.read_bytes()).hexdigest()
                 + "  " + matrix.SUMMARY_NAME + "\n").encode("ascii"),
            )
            self.assertNotIn(str(folder), summary.read_text("utf-8"))
            with self.assertRaisesRegex(ValueError, "new or empty"):
                matrix.export_summary(result, out)

    def test_single_other_version_or_wrong_installer_sha_blocks_all_report_merging(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            catalog, packets, _ = create_fixture(folder, complete=True)
            bad = copy.deepcopy(catalog)
            bad["source_revision"] = "b"*40
            with self.assertRaisesRegex(ValueError, "another source revision"):
                matrix.reconcile(bad, packets)
            bad = copy.deepcopy(catalog)
            bad["targets"]["macos-arm64"]["installer_sha256"] = "0"*64
            with self.assertRaisesRegex(ValueError, "installer differs"):
                matrix.reconcile(bad, packets)
            bad = copy.deepcopy(catalog)
            bad["targets"]["windows-x64"]["installer_size_bytes"] += 1
            with self.assertRaisesRegex(ValueError, "installer differs"):
                matrix.reconcile(bad, packets)

    def test_tampered_owner_json_or_checksum_cannot_enter_four_os_summary(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            catalog, packets, _ = create_fixture(folder)
            p = packets/"linux-x64"/matrix.REPORT_NAME
            original = p.read_bytes()
            p.write_bytes(original.replace(b"not-tested", b"pass"))
            with self.assertRaisesRegex(ValueError, "altered SHA256SUMS"):
                matrix.reconcile(catalog, packets)

    def test_missing_duplicate_extra_symlinks_and_cross_os_are_rejected(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            catalog, packets, _ = create_fixture(folder)
            old = packets/"windows-x64"
            renamed = packets/"windows-x64-missing"
            old.rename(renamed)
            with self.assertRaisesRegex(ValueError, "exactly four"):
                matrix.reconcile(catalog, packets)
            renamed.rename(old)
            (old/"unrelated-data.json").write_text("secret", "utf-8")
            with self.assertRaisesRegex(ValueError, "exactly one private"):
                matrix.reconcile(catalog, packets)
            (old/"unrelated-data.json").unlink()
            original = old/matrix.REPORT_NAME
            copy = folder/"copied.json"
            copy.write_bytes(original.read_bytes())
            original.unlink()
            original.symlink_to(copy)
            with self.assertRaisesRegex(ValueError, "nonempty regular"):
                matrix.reconcile(catalog, packets)

    def test_rejects_approvals_metadata_extras_unknown_targets_and_paths(self):
        with TemporaryDirectory() as folder:
            catalog, packets, _ = create_fixture(Path(folder))
            for field in ("public_release_approved",
                          "binary_to_source_independently_reviewed",
                          "external_license_rights_approved"):
                bad = copy.deepcopy(catalog)
                bad[field] = True
                with self.assertRaisesRegex(ValueError, "cannot assert"):
                    matrix.validate_catalog(bad)
            bad = copy.deepcopy(catalog)
            bad["license_checker_notes"] = "private user files"
            with self.assertRaisesRegex(ValueError, "schema"):
                matrix.validate_catalog(bad)
            bad = copy.deepcopy(catalog)
            bad["targets"]["linux-x64"]["installer_filename"] = "../../private.deb"
            with self.assertRaisesRegex(ValueError, "unsafe"):
                matrix.validate_catalog(bad)
            bad = copy.deepcopy(catalog)
            bad["targets"].pop("macos-x86_64")
            with self.assertRaisesRegex(ValueError, "schema"):
                matrix.validate_catalog(bad)
            with self.assertRaisesRegex(ValueError, "exactly four"):
                matrix.hash_four_installers("a"*40, {"linux-x64": "example.deb"})

    def test_wont_export_personal_paths_from_a_modified_qa_record(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            catalog, packets, _ = create_fixture(folder)
            filename = packets/"windows-x64"/matrix.REPORT_NAME
            report = json.loads(filename.read_text("utf-8"))
            report["private_rom_path"] = "C:\\Users\\private\\game.z64"
            with self.assertRaisesRegex(ValueError, "private extra"):
                qa.validate_report(report)
            with self.assertRaisesRegex(ValueError, "private extra"):
                qa.export_review(report, folder/"should-never-exist")
            self.assertFalse((folder/"should-never-exist").exists())
            report.pop("private_rom_path")
            report["statement"] = "My private ROM is C:\\\\Users\\\\someone\\\\game.z64"
            with self.assertRaisesRegex(ValueError, "private user"):
                qa.validate_report(report)

    def test_catalog_file_creation_is_write_once(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            catalog, packets, _ = create_fixture(folder)
            path = folder/"catalog.json"
            matrix.save_record(catalog, path)
            self.assertEqual(json.loads(path.read_text("utf-8")), catalog)
            with self.assertRaisesRegex(ValueError, "never overwrite"):
                matrix.save_record(catalog, path)
            self.assertNotIn(str(folder), path.read_text("utf-8"))

    def test_no_automated_public_release_workflow_or_game_binaries(self):
        root = Path(__file__).resolve().parents[1]
        x = (root/"tools/v30_physical_qa_matrix.py").read_text("utf-8")
        self.assertNotIn("gh release create", x)
        self.assertNotIn("APPROVED-IMMUTABLE-PRODUCTION", x)
        self.assertIn("public_release_approved", x)
        self.assertIn("owner_reports_complete_for_independent_review", x)
        self.assertIn("source_to_binary_correspondence_reviewed", x)


if __name__ == "__main__":
    unittest.main()
