"""Regression tests for exact 3.1.0 installed-native/license inventory."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.inventory_v31_final_native import EXPECTED, STATUS, digest, inspect, native

SHA = "a" * 40


class FinalNativeInventoryTests(unittest.TestCase):
    def setup_fixture(self, root, target="windows-x64"):
        root = Path(root)
        bundle = root/"installed"
        bundle.mkdir()
        installer = root/EXPECTED[target][0]
        installer.write_bytes(b"fully fake but checksum-verified package" * 35000)
        (bundle/"pygame").mkdir()
        (bundle/"pygame/SDL2.dll").write_bytes(b"first compiled SDL image")
        (bundle/"cv2").mkdir()
        (bundle/"cv2/SDL2.dll").write_bytes(b"other compiled SDL image")
        (bundle/"cv2/opencv.pyd").write_bytes(b"cv2 extension")
        (bundle/"cores").mkdir()
        (bundle/"cores/mgba_libretro.dll").write_bytes(b"libretro")
        (bundle/"_internal").mkdir()
        (bundle/"_internal/avcodec.dll").write_bytes(b"codec candidate")
        (bundle/"licenses").mkdir()
        (bundle/"licenses/Pygame-CE-LGPL-2.1.txt").write_text("LGPL copyright", "utf-8")
        (bundle/"licenses/SDL2-LICENSE.txt").write_text("SDL copyright", "utf-8")
        (bundle/"licenses/PYTHON_DISTRIBUTIONS.json").write_text('{"distributions":[]}',"utf-8")
        (bundle/"licenses/opencv-LICENSE.txt").write_text("OpenCV copyright","utf-8")
        receipt = root/EXPECTED[target][1]
        receipt.write_text(json.dumps({
            "target": target,
            "installer": installer.name,
            "sha256": digest(installer),
            "source_preview_revision": SHA,
            "identity_channel": "final_candidate",
            "settings_namespace": "anything-plays-31",
            "native_core_count": 11,
            "console_profiles": 18,
            "status": "PRIVATE_FULL_3_1_0_FINAL_IDENTITY_QA",
            "public_release_approved": False,
            "final_release_approved": False,
        }), "utf-8")
        return bundle, installer, receipt

    def test_exact_binary_inventory_and_license_signals_stay_unapproved(self):
        with TemporaryDirectory() as temp:
            bundle, installer, receipt = self.setup_fixture(temp)
            out = inspect(target="windows-x64", bundle=bundle, installer=installer,
                          receipt=receipt, source_sha=SHA)
            self.assertEqual(out["status"], STATUS)
            self.assertEqual(out["native_file_count"], 5)
            self.assertEqual(out["notice_file_count"], 4)
            self.assertFalse(out["public_release_approved"])
            self.assertFalse(out["all_redistribution_rights_reviewed"])
            self.assertFalse(out["source_to_binary_correspondence_verified"])
            self.assertEqual(len(out["codec_candidates"]), 1)
            self.assertEqual(len(out["duplicate_native_basenames_with_different_hashes"]), 1)
            self.assertEqual(out["duplicate_native_basenames_with_different_hashes"][0]["basename"],"sdl2.dll")
            self.assertEqual(out["native_family_counts"]["sdl"], 2)
            self.assertEqual(out["native_family_counts"]["libretro_core"], 1)
            self.assertTrue(all(out["notice_presence_signals_not_legal_conclusions"].values()))
            self.assertTrue(all(not x["path"].startswith("/") for x in out["native_files"]))

    def test_versioned_elf_soname_is_native_but_license_metadata_is_not(self):
        for filename in ("libSDL2-2.so.0.3200.10", "libSDL2.so.0",
                         "pygame/base.cpython-313-darwin.so", "sound.dll",
                         "core.dylib", "SDL.pyd"):
            with self.subTest(native=filename):
                self.assertTrue(native(filename))
        for filename in ("001_copying.cpython-313-darwin.so.yml",
                         "libSDL2.so.0.json", "libSDL2.so.backup",
                         "README.txt", "NOTICE.md", "LICENSE.so.yml"):
            with self.subTest(metadata=filename):
                self.assertFalse(native(filename))
        with TemporaryDirectory() as temp:
            bundle, installer, receipt = self.setup_fixture(temp)
            (bundle/"licenses"/"001_copying.cpython-313-darwin.so.yml").write_text(
                "Metadata, not a compiled extension", "utf-8")
            report = inspect(target="windows-x64", bundle=bundle,
                             installer=installer, receipt=receipt, source_sha=SHA)
            self.assertEqual(report["native_file_count"], 5)

    def test_reject_tampered_binary_and_receipt_fields(self):
        with TemporaryDirectory() as temp:
            bundle, installer, receipt = self.setup_fixture(temp)
            for field, value in (
                ("target", "linux-x64"), ("source_preview_revision", "b"*40),
                ("status", "APPROVED_FOR_PUBLIC_RELEASE"), ("native_core_count", 1),
                ("console_profiles", 3), ("public_release_approved", True),
                ("final_release_approved", True), ("identity_channel", "rc2"),
                ("settings_namespace", "anything-plays-31-rc2"),
            ):
                with self.subTest(field=field):
                    data = json.loads(receipt.read_text("utf-8"))
                    data[field] = value
                    receipt.write_text(json.dumps(data), "utf-8")
                    with self.assertRaises(ValueError):
                        inspect(target="windows-x64", bundle=bundle,
                                installer=installer, receipt=receipt, source_sha=SHA)
                    data[field] = {
                        "target": "windows-x64", "source_preview_revision": SHA,
                        "status": "PRIVATE_FULL_3_1_0_FINAL_IDENTITY_QA",
                        "native_core_count":11, "console_profiles":18,
                        "public_release_approved":False,"final_release_approved":False,
                        "identity_channel":"final_candidate",
                        "settings_namespace":"anything-plays-31",
                    }[field]
                    receipt.write_text(json.dumps(data), "utf-8")
            installer.write_bytes(installer.read_bytes()+b"malicious mutation")
            with self.assertRaises(ValueError):
                inspect(target="windows-x64", bundle=bundle,
                        installer=installer, receipt=receipt, source_sha=SHA)

    def test_missing_notices_and_symlinked_installers_fail_closed(self):
        with TemporaryDirectory() as temp:
            bundle, installer, receipt = self.setup_fixture(temp)
            for p in (bundle/"licenses").iterdir():
                p.unlink()
            with self.assertRaises(ValueError):
                inspect(target="windows-x64", bundle=bundle, installer=installer,
                        receipt=receipt, source_sha=SHA)
            with self.assertRaises(ValueError):
                inspect(target="windows-x64", bundle=bundle, installer=installer,
                        receipt=receipt, source_sha="invalid")
        with TemporaryDirectory() as temp:
            bundle, installer, receipt = self.setup_fixture(temp)
            source = installer.with_suffix(".original")
            installer.rename(source)
            try:
                installer.symlink_to(source)
            except (OSError, NotImplementedError):
                self.skipTest("No symlink support")
            with self.assertRaises(ValueError):
                inspect(target="windows-x64", bundle=bundle, installer=installer,
                        receipt=receipt, source_sha=SHA)


if __name__ == "__main__":
    unittest.main()
