"""Read-only native macOS linkage review must never overstate approval."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from tools.inspect_v31_macos_linkage import (
    dependencies_from_otool, inspect, sha256, RC_SHA,
)


def setup_case(root):
    root = Path(root)
    app = root / "AnythingPlays31RC.app"
    lib = app / "Contents/Frameworks/libSDL2-2.0.0.dylib"
    lib.parent.mkdir(parents=True)
    lib.write_bytes(b"Mac native SDL library synthetic fixture")
    dmg = root / "AnythingPlays-3.1.0-rc1-full-macos-arm64.dmg"
    dmg.write_bytes(b"DMG synthetic fixture")
    receipt = {
        "target": "macos-arm64",
        "source_preview_revision": RC_SHA,
        "public_release_approved": False,
        "final_release_approved": False,
        "native_core_count": 11, "console_profiles": 18,
        "installer": dmg.name, "sha256": sha256(dmg),
    }
    audit = {
        "target": "macos-arm64",
        "status": "UNRELEASED_3_1_SDL_RUNTIME_INVENTORY",
        "redistribution_approved": False,
        "pygame_version": "2.5.8",
        "native_candidates": [{
            "path": "Contents/Frameworks/libSDL2-2.0.0.dylib",
            "sha256": sha256(lib)
        }],
    }
    return app, dmg, audit, receipt, lib


def fake_runner(command, **_):
    if command[0] == "otool":
        stdout = (
            "libSDL2.dylib:\n"
            "    @rpath/libSDL2-2.0.0.dylib "
            "(compatibility version 1.0.0, current version 2.32.0)\n"
        )
    elif command[0] == "lipo":
        stdout = "arm64 x86_64\n"
    else:
        stdout = ""
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="")


class MacNativeLinkageReviewContracts(unittest.TestCase):
    def test_parse_dependency_and_source_version_without_inference(self):
        rows = dependencies_from_otool(
            "binary.dylib:\n"
            "\t@rpath/libSDL2-2.0.0.dylib "
            "(compatibility version 1.0.0, current version 2.32.0)\n"
        )
        self.assertEqual(rows, [{
            "name": "@rpath/libSDL2-2.0.0.dylib",
            "compatibility_version": "1.0.0",
            "current_version": "2.32.0",
        }])

    def test_exact_installed_native_digest_and_unapproved_linking(self):
        with TemporaryDirectory() as d:
            app, dmg, audit, receipt, _ = setup_case(d)
            result = inspect(app, audit, receipt, dmg, "macos-arm64",
                             runner=fake_runner)
            self.assertEqual(result["native_file_count"], 1)
            self.assertEqual(result["expected_architecture"], "arm64")
            self.assertTrue(result["native_files"][0]["signed_metadata_available"])
            self.assertEqual(result["native_files"][0]["otool_dependencies"][0]
                             ["current_version"], "2.32.0")
            self.assertFalse(result["redistribution_approved"])
            self.assertFalse(result["lgpl_relinking_reviewed"])
            self.assertFalse(result["upstream_sdl_sources_correspondence_verified"])

    def test_rejects_wrong_source_installer_native_hash_and_unsafe_paths(self):
        with TemporaryDirectory() as d:
            app, dmg, audit, receipt, lib = setup_case(d)
            for field, tamper in (
                ("source_preview_revision", "0" * 40),
                ("native_core_count", 10),
                ("public_release_approved", True),
            ):
                with self.subTest(field=field):
                    altered = dict(receipt, **{field: tamper})
                    with self.assertRaises(ValueError):
                        inspect(app, audit, altered, dmg, "macos-arm64",
                                runner=fake_runner)
            with self.assertRaises(ValueError):
                inspect(app, audit, receipt, dmg, "macos-x64",
                        runner=fake_runner)
            original = lib.read_bytes()
            lib.write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                inspect(app, audit, receipt, dmg, "macos-arm64",
                        runner=fake_runner)
            lib.write_bytes(original)
            for path in ("../etc/passwd", "/etc/passwd"):
                record = dict(audit, native_candidates=[
                    {"path": path, "sha256": sha256(lib)}
                ])
                with self.assertRaises(ValueError):
                    inspect(app, record, receipt, dmg, "macos-arm64",
                            runner=fake_runner)

    def test_source_review_workflow_is_readonly_and_pins_qa(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/v31-macos-native-linkage-review.yml")
        contents = workflow.read_text("utf-8")
        self.assertIn("42886791394", contents)
        self.assertIn("2e59c7c46c6d7700ef5d98523d96d4ab2a5db39d", contents)
        self.assertIn("actions/upload-artifact@v4", contents)
        self.assertNotIn("gh release create", contents)
        self.assertNotIn("contents: write", contents)


if __name__ == "__main__":
    unittest.main()
