"""Private 3.2 full macOS packaging source gates (no DMGs mounted here)."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.stage_v32_full_macos import (
    ARCHITECTURES, STATUS, assemble, names, source_gate,
)
from tools.stage_v32_full_linux import sha256


class FullMacNativeGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="ap32-mac-full-gate-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.arch = "arm64"
        self.sha = "c" * 40
        baseline, preview, _ = names(self.arch)
        self.stable = self.root/baseline
        self.minimal = self.root/preview
        self.stable.write_bytes(b"public-mac-original" * 70000)
        self.minimal.write_bytes(b"private-3.2-new" * 80000)
        self.sums = self.root/"SHA256SUMS.txt"
        self.sums.write_text(sha256(self.stable) + "  " + baseline + "\n")
        self.receipt = self.root/"V32_PRIVATE_PREVIEW_RECEIPT.json"
        self.data = {
            "status": "UNRELEASED_PRIVATE_QA_ONLY",
            "channel": "v32_preview",
            "version": "3.2.0-preview1",
            "target": "macos-arm64",
            "installer": preview,
            "source_revision": self.sha,
            "sha256": sha256(self.minimal),
            "size_bytes": self.minimal.stat().st_size,
            "settings_namespace": "anything-plays-32-preview",
            "bundled_console_profiles": ["gb", "gbc", "gba"],
            "bundled_core_names": ["mgba"],
            "public_release_approved": False,
            "all_18_consoles_verified": False,
            "notarized": False,
        }
        self.save()

    def save(self):
        self.receipt.write_text(json.dumps(self.data), encoding="utf-8")

    def check(self):
        return source_gate(self.arch, self.stable, self.minimal,
                           self.sums, self.receipt, self.sha)

    def test_both_architectures_have_separate_private_installer_names(self):
        self.assertEqual(ARCHITECTURES, ("arm64", "x64"))
        self.assertEqual(names("arm64")[2],
                         "AnythingPlays-3.2.0-fullqa1-macos-arm64.dmg")
        self.assertEqual(names("x64")[2],
                         "AnythingPlays-3.2.0-fullqa1-macos-x64.dmg")
        self.assertIn("NOT_RELEASE", STATUS)
        with self.assertRaisesRegex(ValueError, "architecture"):
            names("universal")

    def test_current_arm64_source_receipt_hashes_are_valid(self):
        self.assertEqual(self.check(), (self.stable, self.minimal))

    def test_matching_intel_revision_and_receipt_pass(self):
        self.arch = "x64"
        old, new, _ = names(self.arch)
        self.stable.rename(self.root/old)
        self.minimal.rename(self.root/new)
        self.stable = self.root/old
        self.minimal = self.root/new
        self.sums.write_text(sha256(self.stable) + "  " + old + "\n")
        self.data["target"] = "macos-x64"
        self.data["installer"] = new
        self.save()
        self.assertEqual(self.check(), (self.stable, self.minimal))

    def test_modified_baseline_fails_original_public_checksum(self):
        self.stable.write_bytes(b"X" + self.stable.read_bytes()[1:])
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.check()

    def test_modified_3_2_preview_fails_source_receipt(self):
        self.minimal.write_bytes(b"X" + self.minimal.read_bytes()[1:])
        with self.assertRaisesRegex(ValueError, "receipt"):
            self.check()

    def test_wrong_source_revision_rejected_before_disk_image_mount(self):
        with self.assertRaisesRegex(ValueError, "Git source revision"):
            source_gate(self.arch, self.stable, self.minimal,
                        self.sums, self.receipt, "invalid")

    def test_false_public_release_and_gameplay_flags_rejected(self):
        for key, forged in (
            ("public_release_approved", True),
            ("all_18_consoles_verified", True),
            ("notarized", True),
            ("bundled_core_names", ["mgba", "dolphin"]),
            ("settings_namespace", "anything-plays-31"),
            ("source_revision", "f" * 40),
            ("installer", "AnythingPlays-3.1.1-macos-arm64.dmg"),
        ):
            with self.subTest(key=key):
                old = self.data[key]
                self.data[key] = forged
                self.save()
                with self.assertRaisesRegex(ValueError, "receipt"):
                    self.check()
                self.data[key] = old
        self.save()
        self.check()

    def test_wrong_architecture_and_symlinked_baseline_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "wrongly named"):
            source_gate("x64", self.stable, self.minimal,
                        self.sums, self.receipt, self.sha)
        real = self.root/"baseline_real"
        self.stable.rename(real)
        self.stable.symlink_to(real)
        with self.assertRaisesRegex(ValueError, "linked"):
            self.check()

    def test_public_release_flags_fail_before_any_disk_image_mount(self):
        output = self.root/"full"
        with patch.dict("os.environ", {
                "AP_V32_PREVIEW_BUILD": "1", "AP_RELEASE_BUILD": "1"}):
            with self.assertRaisesRegex(ValueError, "non-release"):
                assemble(self.arch, self.stable, self.minimal, self.sums,
                         self.receipt, self.sha, output)
        self.assertFalse(output.exists())

    def test_existing_destination_never_replaced(self):
        out = self.root/"existing"
        out.mkdir()
        with patch.dict("os.environ", {
                "AP_V32_PREVIEW_BUILD": "1", "AP_RELEASE_BUILD": "0",
                "AP_V30_APPROVED_RELEASE": "0"}):
            with self.assertRaisesRegex(ValueError, "overwrite"):
                assemble(self.arch, self.stable, self.minimal, self.sums,
                         self.receipt, self.sha, out)
        self.assertEqual(list(out.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
