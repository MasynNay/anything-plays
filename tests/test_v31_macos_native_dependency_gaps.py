"""Adversarial checks for review-only 3.1 Mac native dependency triage."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.report_v31_macos_native_dependency_gaps import (
    REPORT_STATUS,
    SOURCE_REVISION,
    TARGET_ARCHES,
    _read_report,
    assemble_gap_report,
    inspect_linkage_report,
)


def fixture(target):
    arch = TARGET_ARCHES[target]
    native = []
    for path, digest in (
        ("Contents/Frameworks/pygame/libSDL2-2.0.0.dylib", "a" * 64),
        ("Contents/Frameworks/cv2/libSDL2-2.0.0.dylib", "b" * 64),
        ("Contents/Frameworks/pygame/base.so", "c" * 64),
    ):
        native.append({
            "path": path,
            "sha256": digest,
            "size_bytes": 1024,
            "otool_result": {"return_code": 0, "stdout": path},
            "otool_dependencies": [
                {"name": "@rpath/libSDL2-2.0.0.dylib",
                 "current_version": "3201.10.0"},
                {"name": "/usr/lib/libSystem.B.dylib"},
                {"name": "@loader_path/libFLAC.12.dylib"},
                {"name": "@rpath/base.so"},
            ],
        })
    return {
        "schema_version": 1,
        "status": REPORT_STATUS,
        "target": target,
        "source_app_commit": SOURCE_REVISION,
        "expected_architecture": arch,
        "native_file_count": len(native),
        "native_files": native,
        "redistribution_approved": False,
        "lgpl_relinking_reviewed": False,
        "upstream_sdl_sources_correspondence_verified": False,
    }


class NativeDependencyGapTests(unittest.TestCase):
    def test_both_architectures_generate_unapproved_gap_report(self):
        result = assemble_gap_report(
            fixture("macos-arm64"), fixture("macos-x64")
        )
        self.assertEqual(set(result["reports"]), set(TARGET_ARCHES))
        self.assertFalse(result["lgpl_compliance_approved"])
        self.assertFalse(result["stable_3_1_release_approved"])
        self.assertFalse(result["corresponding_source_complete"])
        for target in TARGET_ARCHES:
            with self.subTest(target=target):
                report = result["reports"][target]
                self.assertEqual(report["native_files_examined"], 3)
                self.assertEqual(report["dependency_name_count"], 4)
                by_name = {
                    dep["dependency"]: dep for dep in report["dependencies"]
                }
                self.assertEqual(
                    by_name["@rpath/libSDL2-2.0.0.dylib"]["classification"],
                    "ambiguous_same_basename_different_binaries",
                )
                self.assertEqual(
                    len(by_name["@rpath/libSDL2-2.0.0.dylib"]["possible_audited_files"]),
                    2,
                )
                self.assertEqual(
                    by_name["@loader_path/libFLAC.12.dylib"]["classification"],
                    "not_found_in_audited_native_subset",
                )
                self.assertEqual(
                    by_name["@rpath/base.so"]["classification"],
                    "audited_basename_match_only",
                )
                self.assertEqual(
                    by_name["/usr/lib/libSystem.B.dylib"]["classification"],
                    "observed_system_library_path",
                )
                self.assertEqual(
                    len(by_name["@rpath/base.so"]["referenced_by"]), 3
                )
                self.assertFalse(
                    by_name["@rpath/base.so"]["actual_loader_resolution_verified"]
                )
                self.assertIn(
                    "@rpath/libSDL2-2.0.0.dylib",
                    report["unresolved_or_ambiguous_names"],
                )

    def test_rejects_approved_wrong_revision_and_architecture(self):
        for key, new_value in (
            ("redistribution_approved", True),
            ("lgpl_relinking_reviewed", True),
            ("upstream_sdl_sources_correspondence_verified", True),
            ("source_app_commit", "0" * 40),
            ("expected_architecture", "x86_64"),
            ("status", "STABLE_3_1_APPROVED"),
            ("schema_version", 2),
            ("native_file_count", 5),
        ):
            with self.subTest(key=key):
                report = fixture("macos-arm64")
                report[key] = new_value
                with self.assertRaises(ValueError):
                    inspect_linkage_report(report, "macos-arm64")

    def test_rejects_duplicate_unsafe_and_unverifiable_native_files(self):
        invalid = [
            ("path", "../escape.dylib"),
            ("path", "/etc/passwd"),
            ("path", "Contents//Frameworks/libSDL.dylib"),
            ("path", "Contents\\Frameworks\\libSDL.dylib"),
            ("sha256", "ab"),
            ("size_bytes", 0),
            ("size_bytes", True),
        ]
        for field, replacement in invalid:
            with self.subTest(field=field, replacement=replacement):
                report = fixture("macos-arm64")
                report["native_files"][0][field] = replacement
                with self.assertRaises(ValueError):
                    inspect_linkage_report(report, "macos-arm64")
        report = fixture("macos-arm64")
        report["native_files"][1]["path"] = report["native_files"][0]["path"]
        with self.assertRaises(ValueError):
            inspect_linkage_report(report, "macos-arm64")

    def test_rejects_failed_missing_or_invalid_otool_evidence(self):
        for variant in ("missing", "failed", "empty", "unsafe-dependency"):
            with self.subTest(variant=variant):
                report = fixture("macos-x64")
                item = report["native_files"][0]
                if variant == "missing":
                    item.pop("otool_result")
                elif variant == "failed":
                    item["otool_result"]["return_code"] = 1
                elif variant == "empty":
                    item["otool_dependencies"] = []
                else:
                    item["otool_dependencies"][0]["name"] = "bad\ninjected"
                with self.assertRaises(ValueError):
                    inspect_linkage_report(report, "macos-x64")

    def test_explicit_absolute_external_dylib_not_assumed_bundled(self):
        report = fixture("macos-x64")
        report["native_files"][0]["otool_dependencies"].append(
            {"name": "/opt/custom/libSDL2-2.0.0.dylib"}
        )
        result = inspect_linkage_report(report, "macos-x64")
        entry = next(
            dep for dep in result["dependencies"]
            if dep["dependency"] == "/opt/custom/libSDL2-2.0.0.dylib"
        )
        self.assertEqual(
            entry["classification"], "external_absolute_path_requires_review"
        )
        self.assertEqual(entry["possible_audited_files"], [])

    def test_same_basename_same_digest_still_does_not_claim_loader_resolution(self):
        report = fixture("macos-arm64")
        report["native_files"][1]["sha256"] = "a" * 64
        result = inspect_linkage_report(report, "macos-arm64")
        entry = next(
            dep for dep in result["dependencies"]
            if dep["dependency"] == "@rpath/libSDL2-2.0.0.dylib"
        )
        self.assertEqual(entry["classification"], "audited_basename_match_only")
        self.assertFalse(entry["actual_loader_resolution_verified"])

    def test_report_file_rejects_symlinks_and_malformed_json(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            source = root / "qa.json"
            source.write_text(json.dumps(fixture("macos-x64")), "utf-8")
            self.assertEqual(_read_report(source)["target"], "macos-x64")
            source.write_text("{bad json", "utf-8")
            with self.assertRaises(ValueError):
                _read_report(source)
            source.write_text(json.dumps(fixture("macos-x64")), "utf-8")
            link = root / "linked.json"
            try:
                link.symlink_to(source)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unavailable on this platform")
            with self.assertRaises(ValueError):
                _read_report(link)


if __name__ == "__main__":
    unittest.main()
