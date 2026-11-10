"""Safety and regression tests for dual SDL2 library loader ambiguity."""
import copy
import json
from pathlib import Path
import unittest

from tools.audit_v31_sdl_collision import audit, EXPECTED_COUNTS, SOURCE_COMMIT


def fixture(target, collision=False):
    arch = "arm64" if target.endswith("arm64") else "x86_64"
    size = EXPECTED_COUNTS[target]
    entries = []
    for i in range(size):
        if i == 0:
            path = "Contents/Frameworks/pygame/__dot__dylibs/libSDL2-2.0.0.dylib"
            sha = "1" * 64
            version = "3201.10.0"
        elif i == 1:
            path = "Contents/Frameworks/cv2/__dot__dylibs/libSDL2-2.0.0.dylib"
            sha = ("2" if collision else "1") * 64
            version = "3201.8.0" if collision else "3201.10.0"
        else:
            path = f"Contents/Frameworks/pygame/__dot__dylibs/libsample_{i:03d}.dylib"
            sha = f"{i:064x}"
            version = "1.0.0"
        entry = {
            "path": path, "sha256": sha,
            "lipo_result": {"return_code": 0, "stdout": arch + "\n"},
            "codesign_metadata": {"return_code": 0,
                                   "stderr": "flags=0x2(adhoc) Signature=adhoc"},
            "otool_result": {"return_code": 0},
            "otool_dependencies": [{
                "name": "@rpath/libSDL2-2.0.0.dylib",
                "current_version": version,
            }] if i < 2 else [],
        }
        entries.append(entry)
    return {
        "target": target,
        "status": "UNRELEASED_3_1_MACOS_NATIVE_LINKAGE_REVIEW",
        "source_app_commit": SOURCE_COMMIT,
        "redistribution_approved": False,
        "upstream_sdl_sources_correspondence_verified": False,
        "lgpl_relinking_reviewed": False,
        "native_file_count": size, "native_files": entries,
    }


class SDLCollisionReviewTests(unittest.TestCase):
    def test_apple_silicon_mismatched_sdl_versions_flagged(self):
        report = audit(fixture("macos-arm64", collision=True))
        self.assertEqual(report["signed_native_files_checked"], 121)
        self.assertEqual(report["potential_loader_conflict_count"], 1)
        item = report["conflicting_sdl_basenames"][0]
        self.assertEqual(item["basename"], "libSDL2-2.0.0.dylib")
        self.assertEqual({x["macho_current_version"] for x in item["variants"]},
                         {"3201.8.0", "3201.10.0"})
        self.assertFalse(item["runtime_resolution_proven"])
        self.assertFalse(report["actual_runtime_conflict_verified"])
        self.assertFalse(report["redistribution_approved"])

    def test_identical_intel_sdl_duplicates_not_conflicting(self):
        report = audit(fixture("macos-x64"))
        self.assertEqual(report["signed_native_files_checked"], 120)
        self.assertEqual(report["potential_loader_conflict_count"], 0)
        self.assertEqual(report["conflicting_sdl_basenames"], [])

    def test_reject_unsafe_paths_digests_and_missing_signed_metadata(self):
        for key, value in (
            ("path", "../outside/libSDL2.dylib"),
            ("path", "/usr/lib/libSDL2.dylib"),
            ("sha256", "invalid"),
            ("lipo_result", {"return_code": 0, "stdout": "x86_64\n"}),
            ("codesign_metadata", {"return_code": 1, "stderr": ""}),
            ("otool_result", {"return_code": 1}),
        ):
            with self.subTest(key=key):
                source = fixture("macos-arm64", collision=True)
                source["native_files"][0][key] = value
                with self.assertRaises(ValueError):
                    audit(source)

    def test_reject_wrong_revision_approval_or_incomplete_records(self):
        for key, value in (
            ("source_app_commit", "0" * 40),
            ("redistribution_approved", True),
            ("lgpl_relinking_reviewed", True),
            ("upstream_sdl_sources_correspondence_verified", True),
            ("native_file_count", 1),
            ("target", "linux-x64"),
        ):
            with self.subTest(key=key):
                source = fixture("macos-arm64")
                source[key] = value
                with self.assertRaises(ValueError):
                    audit(source)
        source = fixture("macos-arm64")
        source["native_files"][1]["path"] = source["native_files"][0]["path"]
        with self.assertRaises(ValueError):
            audit(source)

    def test_readonly_source_collision_workflow(self):
        flow = (Path(__file__).resolve().parents[1]
                / ".github/workflows/v31-sdl-collision-audit.yml").read_text("utf-8")
        self.assertIn("42875616776", flow)
        self.assertIn("actions/upload-artifact@v4", flow)
        self.assertNotIn("contents: write", flow)
        self.assertNotIn("gh release create", flow)


if __name__ == "__main__":
    unittest.main()
