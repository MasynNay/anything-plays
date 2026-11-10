"""Source-only 3.1 SDL native/wheel notice inventory adversarial tests."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from tools.audit_v31_sdl_runtime import VERSION, TARGETS, inspect_bundle


def fixture(root, target="linux-x64"):
    root = Path(root)
    licenses = (root / "Contents/Resources/licenses" if target.startswith("macos-")
                else root / "licenses")
    notices = licenses / "python-distribution-notices" / ("pygame-ce-" + VERSION)
    notices.mkdir(parents=True)
    notice = notices / "000_license"
    notice.write_text("This is synthetic license text for a test fixture.", "utf-8")
    (licenses / "PYTHON_DISTRIBUTIONS.json").write_text(json.dumps({
        "schema_version": 1,
        "distributions": [{"name": "pygame-ce", "version": VERSION,
                           "license_files": [{"bundled_path":
                               "python-distribution-notices/pygame-ce-" + VERSION +
                               "/000_license"}]}]
    }), "utf-8")
    native = root / "_internal" / "pygame"
    native.mkdir(parents=True)
    (native / "base.pyd").write_bytes(b"MZ" + b"test")
    return licenses, native


class SDLRuntimeAuditTests(unittest.TestCase):
    def test_all_four_platform_identifiers_are_supported(self):
        self.assertEqual(len(TARGETS), 4)
        for target in TARGETS:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as d:
                license_root, native = fixture(d, target)
                report = inspect_bundle(d, target)
                self.assertEqual(report["pygame_version"], "2.5.8")
                self.assertEqual(len(report["wheel_notices"]), 1)
                self.assertEqual(len(report["native_candidates"]), 1)
                self.assertRegex(report["native_candidates"][0]["sha256"],
                                 r"^[a-f0-9]{64}$")
                self.assertFalse(report["redistribution_approved"])
                self.assertFalse(report["original_sources_verified"])
                self.assertFalse(report["sdl_linkage_reviewed"])

    def test_rejects_no_notice_missing_notice_or_modified_inventory(self):
        for mode in ("missing", "empty", "wrong-version", "bad-schema"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d:
                licenses, _ = fixture(d)
                manifest = licenses / "PYTHON_DISTRIBUTIONS.json"
                record = json.loads(manifest.read_text("utf-8"))
                if mode == "missing":
                    (licenses / "python-distribution-notices" /
                     "pygame-ce-2.5.8" / "000_license").unlink()
                elif mode == "empty":
                    record["distributions"][0]["license_files"] = []
                elif mode == "wrong-version":
                    record["distributions"][0]["version"] = "2.5.7"
                else:
                    record["distributions"] = None
                manifest.write_text(json.dumps(record), "utf-8")
                with self.assertRaises(ValueError):
                    inspect_bundle(d, "linux-x64")

    def test_rejects_missing_native_or_duplicated_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            licenses, native = fixture(d)
            (native / "base.pyd").unlink()
            with self.assertRaises(ValueError):
                inspect_bundle(d, "linux-x64")
            (native / "base.pyd").write_bytes(b"MZ")
            manifest = licenses / "PYTHON_DISTRIBUTIONS.json"
            data = json.loads(manifest.read_text("utf-8"))
            data["distributions"].append(data["distributions"][0])
            manifest.write_text(json.dumps(data), "utf-8")
            with self.assertRaises(ValueError):
                inspect_bundle(d, "linux-x64")

    def test_rejects_path_traversal_and_external_notice_links(self):
        for path in ("../escape", "/etc/passwd", "python-distribution-notices/../outside",
                     "python-distribution-notices/pygame-ce-2.5.8/../../oops"):
            with self.subTest(path=path), tempfile.TemporaryDirectory() as d:
                licenses, _ = fixture(d)
                manifest = licenses / "PYTHON_DISTRIBUTIONS.json"
                data = json.loads(manifest.read_text("utf-8"))
                data["distributions"][0]["license_files"][0]["bundled_path"] = path
                manifest.write_text(json.dumps(data), "utf-8")
                with self.assertRaises(ValueError):
                    inspect_bundle(d, "linux-x64")

    def test_rejects_native_symlink_without_following(self):
        with tempfile.TemporaryDirectory() as d:
            _, native = fixture(d)
            (native / "base.pyd").unlink()
            try:
                (native / "base.pyd").symlink_to(Path(d) / "missing.dll")
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unavailable on this OS")
            with self.assertRaises(ValueError):
                inspect_bundle(d, "linux-x64")

    def test_source_workflow_fails_closed_and_does_not_publish(self):
        root = Path(__file__).resolve().parents[1]
        for path in (".github/workflows/v31-full-linux-qa.yml",
                     ".github/workflows/v31-full-windows-qa.yml",
                     ".github/workflows/v31-full-macos-qa.yml"):
            with self.subTest(path=path):
                workflow = (root / path).read_text("utf-8")
                self.assertIn("SDL_RUNTIME_AUDIT.json", workflow)
                self.assertNotIn("gh release create", workflow)
                self.assertNotIn("contents: write", workflow)


if __name__ == "__main__":
    unittest.main()
