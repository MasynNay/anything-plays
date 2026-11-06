"""Tests for the metadata-only frozen binary inventory."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.binary_inventory import collect_bundle_inventory, main


class BundleInventoryTests(unittest.TestCase):
    def test_detects_native_bytes_and_records_all_file_hashes(self):
        with TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "app"
            (bundle / "native").mkdir(parents=True)
            (bundle / "native" / "mgba.so").write_bytes(b"\x7fELFtest native")
            (bundle / "README.txt").write_text("hello", encoding="utf-8")

            report = collect_bundle_inventory(bundle, "linux-x86_64", "123abc")
            self.assertEqual(report["target"], "linux-x86_64")
            self.assertEqual(report["file_count"], 2)
            self.assertEqual(report["native_file_count"], 1)
            self.assertEqual(report["native_files"][0]["binary_format"], "ELF")
            self.assertEqual(report["native_files"][0]["path"], "native/mgba.so")
            self.assertEqual(report["source_sha"], "123abc")
            self.assertFalse(report["redistribution_approved"])
            by_path = {x["path"]: x for x in report["files"]}
            self.assertEqual(by_path["README.txt"]["sha256"],
                             hashlib.sha256(b"hello").hexdigest())

    def test_ignores_safe_symlink_target_without_duplicate_hash(self):
        with TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "app"
            bundle.mkdir()
            (bundle / "native.so").write_bytes(b"\x7fELFtest")
            (bundle / "alias.so").symlink_to("native.so")
            report = collect_bundle_inventory(bundle, "linux-x86_64")
            self.assertEqual(report["file_count"], 1)
            self.assertEqual(report["symlink_count"], 1)
            self.assertEqual(report["symlinks"][0]["target"], "native.so")

    def test_external_symlink_fails(self):
        with TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "app"
            bundle.mkdir()
            outside = Path(tmp) / "outside"
            outside.write_bytes(b"contents")
            (bundle / "outside").symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "External symlink"):
                collect_bundle_inventory(bundle, "linux-x86_64")

    def test_rejects_empty_bundle_or_invalid_target(self):
        with TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            with self.assertRaisesRegex(ValueError, "Empty"):
                collect_bundle_inventory(bundle, "linux-x86_64")
            (bundle / "file").write_bytes(b"hello")
            with self.assertRaisesRegex(ValueError, "Invalid target"):
                collect_bundle_inventory(bundle, "../escape")

    def test_matches_staged_cores_against_manifest(self):
        with TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            cores = bundle / "cores"
            cores.mkdir()
            records = []
            for name in ("mgba", "snes9x"):
                payload = (b"\x7fELF" + name.encode("ascii"))
                (cores / f"{name}_libretro.so").write_bytes(payload)
                records.append({
                    "name": name, "file": f"{name}_libretro.so",
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                })
            (cores / "CORE_PROVENANCE.json").write_text(
                json.dumps({"cores": records}), encoding="utf-8")
            report = collect_bundle_inventory(bundle, "linux-x86_64")
            self.assertEqual({x["name"] for x in report["verified_cores"]},
                             {"mgba", "snes9x"})
            (cores / "mgba_libretro.so").write_bytes(b"changed after signing")
            with self.assertRaisesRegex(ValueError, "Post-packaging core integrity mismatch"):
                collect_bundle_inventory(bundle, "linux-x86_64")

    def test_reports_python_versions_from_build_environment(self):
        with TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            licenses = bundle / "licenses"
            licenses.mkdir()
            (licenses / "PYTHON_DISTRIBUTIONS.json").write_text(json.dumps({
                "distributions": [
                    {"name": "Pillow", "version": "12.0", "license_expression": "MIT",
                     "license_files": [{"bundled_path": "license.txt"}]},
                ],
            }), encoding="utf-8")
            report = collect_bundle_inventory(bundle, "windows-x86_64")
            self.assertEqual(report["python_distributions"][0]["name"], "Pillow")
            self.assertEqual(report["python_distributions"][0]["version"], "12.0")
            self.assertEqual(report["python_distributions"][0]["bundled_notice_count"], 1)

    def test_headless_cv2_inventory_rejects_bundled_qt(self):
        with TemporaryDirectory() as temp:
            bundle = Path(temp)
            licenses = bundle / "licenses"
            licenses.mkdir()
            (licenses / "PYTHON_DISTRIBUTIONS.json").write_text(
                json.dumps({"distributions": [
                    {"name": "opencv-python-headless", "version": "4.14.0.94",
                     "license_files": []}
                ]}), encoding="utf-8"
            )
            qt = bundle / "_internal" / "opencv_python_headless.libs"
            qt.mkdir(parents=True)
            file = qt / "libQt5Core-example.so"
            file.write_bytes(b"\x7fELF")
            with self.assertRaisesRegex(ValueError, "Unexpected Qt GUI binaries"):
                collect_bundle_inventory(bundle, "linux-x86_64")
            file.unlink()
            report = collect_bundle_inventory(bundle, "linux-x86_64")
            self.assertEqual(report["python_distributions"][0]["name"],
                             "opencv-python-headless")

    def test_reports_macos_and_pe_magic(self):
        with TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            (bundle / "mac").write_bytes(b"\xcf\xfa\xed\xfe" + b"x" * 10)
            (bundle / "win.exe").write_bytes(b"MZ" + b"x" * 10)
            report = collect_bundle_inventory(bundle, "macos-arm64")
            self.assertEqual({x["binary_format"] for x in report["native_files"]},
                             {"Mach-O", "PE"})


if __name__ == "__main__":
    unittest.main()
