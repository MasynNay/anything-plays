"""Offline regression tests for the staged platform bundle verifier.

These fixtures test packaging integrity only, not third-party license clearance.
"""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from verify_bundle import CORE_NAMES, EXTENSIONS, REQUIRED_DOCUMENTS, verify_bundle


class VerifyBundleTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)

    def make_bundle(self, platform_name):
        bundle = self.root / ("AnythingPlays.app" if platform_name == "macos" else "AnythingPlays")
        if platform_name == "macos":
            licenses = bundle / "Contents" / "Resources" / "licenses"
            cores = bundle / "Contents" / "MacOS" / "cores"
        else:
            licenses = bundle / "licenses"
            cores = bundle / "cores"
        licenses.mkdir(parents=True, exist_ok=True)
        cores.mkdir(parents=True, exist_ok=True)
        for name in REQUIRED_DOCUMENTS:
            (licenses / name).write_text(f"Test fixture for {name}\n", encoding="utf-8")

        records = []
        for name in CORE_NAMES:
            filename = f"{name}_libretro{EXTENSIONS[platform_name]}"
            payload = (name + platform_name).encode("ascii")
            (cores / filename).write_bytes(payload)
            records.append({
                "name": name,
                "file": filename,
                "source_url": f"https://example.invalid/{filename}.zip",
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            })
        manifest_path = cores / "CORE_PROVENANCE.json"
        manifest_path.write_text(json.dumps({"cores": records}), encoding="utf-8")
        return bundle, licenses, cores, manifest_path

    def test_valid_staged_bundles_on_all_three_platforms(self):
        for platform_name in EXTENSIONS:
            with self.subTest(platform=platform_name):
                bundle, _, _, _ = self.make_bundle(platform_name)
                verify_bundle(bundle, platform_name)

    def test_native_core_check_can_be_requested_explicitly(self):
        bundle, _, cores, _ = self.make_bundle("linux")
        with patch("verify_bundle._validate_mgba_core") as check:
            verify_bundle(bundle, "linux", check_native=True)
        check.assert_called_once_with(cores / "mgba_libretro.so")

    def test_missing_license_document_fails(self):
        bundle, licenses, _, _ = self.make_bundle("macos")
        (licenses / "Snes9x-LICENSE.txt").unlink()
        with self.assertRaisesRegex(ValueError, "Missing bundled license"):
            verify_bundle(bundle, "macos")

    def test_empty_license_document_fails(self):
        bundle, licenses, _, _ = self.make_bundle("windows")
        (licenses / "mGBA-MPL-2.0.txt").write_text("   ")
        with self.assertRaisesRegex(ValueError, "Empty bundled license"):
            verify_bundle(bundle, "windows")

    def test_changed_binary_fails(self):
        bundle, _, cores, _ = self.make_bundle("linux")
        (cores / "mgba_libretro.so").write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            verify_bundle(bundle, "linux")

    def test_missing_manifest_fails(self):
        bundle, _, _, manifest = self.make_bundle("macos")
        manifest.unlink()
        with self.assertRaisesRegex(ValueError, "Missing core manifest"):
            verify_bundle(bundle, "macos")

    def test_duplicate_core_entry_fails(self):
        bundle, _, _, manifest = self.make_bundle("linux")
        data = json.loads(manifest.read_text())
        data["cores"][1] = dict(data["cores"][0])
        manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "duplicated core"):
            verify_bundle(bundle, "linux")

    def test_missing_source_url_fails(self):
        bundle, _, _, manifest = self.make_bundle("windows")
        data = json.loads(manifest.read_text())
        data["cores"][0].pop("source_url")
        manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "Missing HTTPS source URL"):
            verify_bundle(bundle, "windows")

    def test_unsupported_platform_fails(self):
        with self.assertRaisesRegex(ValueError, "Unsupported platform"):
            verify_bundle(self.root, "unknown")


if __name__ == "__main__":
    unittest.main()
