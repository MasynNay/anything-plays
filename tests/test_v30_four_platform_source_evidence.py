"""Four-platform original-source installer evidence is strict and non-approving."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from anything_plays.v30_approved_core_map import ELEVEN_EXPECTED, ELEVEN_REPOSITORIES
from tools.compile_v30_four_platform_source_evidence import (
    ARTIFACT_PREFIX, ARTIFACT_SUFFIX, INSTALL_STATUS, INSTALLED,
    STAGED, STAGING_STATUS, TARGETS, consolidate_evidence,
)


def make_fake_evidence(root):
    for pos, target in enumerate(TARGETS):
        folder = root / (ARTIFACT_PREFIX + target + ARTIFACT_SUFFIX)
        folder.mkdir()
        cores = {name: ("%064x" % (pos * 20 + i + 1))
                 for i, name in enumerate(sorted(ELEVEN_EXPECTED))}
        (folder / INSTALLED).write_text(json.dumps({
            "target": target, "status": INSTALL_STATUS,
            "installed_core_count": 11, "console_profiles": 18,
            "actual_core_sha256": cores,
            "source_alternative_manifest_sha256": "e" * 64,
            "dolphin_sys_bundled": True, "source_provenance_recorded": True,
            "all_eleven_original_source_families_verified": True,
            "physical_hardware_acceptance": False,
            "legal_review_and_redistribution_approved": False,
            "unapproved_installer_uploaded": False,
        }), "utf-8")
        (folder / STAGED).write_text(json.dumps({
            "target": target, "status": STAGING_STATUS,
            "native_core_count": 11, "source_built_families": 11,
            "old_buildbot_dolphin_excluded": True,
            "public_binary_distribution_approved": False,
            "source_built_dolphin": {
                "native_sha256": cores["dolphin"],
                "native_archive_sha256": "d" * 64,
                "source_build_report_sha256": "c" * 64,
                "source_commit": ELEVEN_EXPECTED["dolphin"],
                "source_repository": ELEVEN_REPOSITORIES["dolphin"],
                "old_unverified_buildbot_replaced": True,
                "pristine_unmodified_original_source_compiled": True,
                "public_binary_distribution_approved": False,
                "direct_original_gitlinks": 34,
                "nested_original_gitlinks": 3,
                "original_source_notices": {str(i): {} for i in range(5)},
            },
        }), "utf-8")


def edit_report(folder, target, name, change):
    path = folder / (ARTIFACT_PREFIX + target + ARTIFACT_SUFFIX) / name
    data = json.loads(path.read_text("utf-8"))
    change(data)
    path.write_text(json.dumps(data), "utf-8")


class FourPlatformSourceEvidenceTests(unittest.TestCase):
    def test_44_real_hash_slots_without_implied_licensing(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_fake_evidence(root)
            result = consolidate_evidence(root, "42568420431")
            self.assertEqual(result["total_platform_native_sha256"], 44)
            self.assertEqual(set(result["targets"]), set(TARGETS.values()))
            self.assertEqual(result["source_actions_run_id"], 42568420431)
            self.assertFalse(result["public_binary_distribution_approved"])
            for target in result["targets"].values():
                self.assertEqual(set(target["cores"]), set(ELEVEN_EXPECTED))
                self.assertFalse(target["public_binary_distribution_approved"])
                self.assertFalse(target["cores"]["dolphin"]["redistribution_license_reviewed"])

    def test_missing_platform_fails(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_fake_evidence(root)
            import shutil
            shutil.rmtree(root / (ARTIFACT_PREFIX + "macos-x64" + ARTIFACT_SUFFIX))
            with self.assertRaisesRegex(ValueError, "four"):
                consolidate_evidence(root, "42568420431")

    def test_unverified_installed_flags_fail(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_fake_evidence(root)
            edit_report(root, "linux-x64", INSTALLED,
                        lambda d: d.update(legal_review_and_redistribution_approved=True))
            with self.assertRaisesRegex(ValueError, "installed"):
                consolidate_evidence(root, "42568420431")

    def test_changed_dolphin_binary_fails(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_fake_evidence(root)
            edit_report(root, "windows-x64", STAGED,
                        lambda d: d["source_built_dolphin"].update(native_sha256="0" * 64))
            with self.assertRaisesRegex(ValueError, "does not match"):
                consolidate_evidence(root, "42568420431")

    def test_missing_gpl_original_source_notices_fail(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_fake_evidence(root)
            edit_report(root, "macos-arm64", STAGED,
                        lambda d: d["source_built_dolphin"].update(original_source_notices={}))
            with self.assertRaisesRegex(ValueError, "notices"):
                consolidate_evidence(root, "42568420431")

    def test_missing_core_or_malformed_sha_fails(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_fake_evidence(root)
            edit_report(root, "linux-x64", INSTALLED,
                        lambda d: d["actual_core_sha256"].update(mgba="garbage"))
            with self.assertRaisesRegex(ValueError, "SHA256"):
                consolidate_evidence(root, "42568420431")

    def test_run_id_must_be_numeric(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_fake_evidence(root)
            for bad in ("0", "missing", "../22"):
                with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "run ID"):
                    consolidate_evidence(root, bad)


if __name__ == "__main__":
    unittest.main()
