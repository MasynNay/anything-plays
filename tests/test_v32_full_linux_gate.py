"""3.2 Linux full-core native assembly must fail closed before extracting."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.stage_v32_full_linux import (
    BASELINE, FULL, STATUS, assemble, sha256, source_gate,
)
from tools.verify_v32_preview import FILES

REV = "a" * 40


class V32FullLinuxGateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="ap32-full-native-test-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.old = self.root/BASELINE
        self.new = self.root/FILES["linux-x64"]
        self.old.write_bytes(b"oldsource" * 150000)
        self.new.write_bytes(b"preview32" * 150000)
        self.sums = self.root/"SHA256SUMS.txt"
        self.sums.write_text(sha256(self.old) + "  " + BASELINE + "\n")
        self.receipt = self.root/"V32_PRIVATE_PREVIEW_RECEIPT.json"
        self.record = {
            "status": "UNRELEASED_PRIVATE_QA_ONLY",
            "channel": "v32_preview",
            "version": "3.2.0-preview1",
            "target": "linux-x64",
            "installer": FILES["linux-x64"],
            "source_revision": REV,
            "sha256": sha256(self.new),
            "size_bytes": self.new.stat().st_size,
            "settings_namespace": "anything-plays-32-preview",
            "bundled_core_names": ["mgba"],
            "bundled_console_profiles": ["gb", "gbc", "gba"],
            "public_release_approved": False,
            "all_18_consoles_verified": False,
        }
        self.save()

    def save(self):
        self.receipt.write_text(json.dumps(self.record), "utf-8")

    def gate(self):
        return source_gate(self.old, self.new, self.sums, self.receipt, REV)

    def test_exact_source_preflight_and_private_installer_name(self):
        self.assertEqual(self.gate(), (self.old, self.new))
        self.assertEqual(FULL,
                         "anything-plays-32-preview_3.2.0~fullqa1_amd64.deb")
        self.assertIn("NOT_RELEASE", STATUS)

    def test_public_baseline_byte_mutation_is_rejected(self):
        self.old.write_bytes(b"corrupted" * 150000)
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.gate()

    def test_preview_mutation_and_unknown_source_revision_are_rejected(self):
        self.new.write_bytes(b"corrupted" * 150000)
        with self.assertRaisesRegex(ValueError, "receipt"):
            self.gate()
        with self.assertRaisesRegex(ValueError, "Git source SHA"):
            source_gate(self.old, self.new, self.sums, self.receipt, "invalid")

    def test_fake_full_console_claim_and_public_approval_are_rejected(self):
        for key, fake in (
                ("bundled_core_names", ["mgba", "dolphin"]),
                ("all_18_consoles_verified", True),
                ("public_release_approved", True),
                ("settings_namespace", "anything-plays-31"),
                ("source_revision", "e" * 40)):
            with self.subTest(key=key):
                original = self.record[key]
                self.record[key] = fake
                self.save()
                with self.assertRaisesRegex(ValueError, "receipt"):
                    self.gate()
                self.record[key] = original
        self.save()
        self.gate()

    def test_missing_or_linked_input_rejected_without_extracting(self):
        link = self.root/"linked"
        link.symlink_to(self.old)
        with self.assertRaisesRegex(ValueError, "wrongly named"):
            source_gate(link, self.new, self.sums, self.receipt, REV)
        self.old.unlink()
        self.old.symlink_to(link)
        with self.assertRaisesRegex(ValueError, "linked"):
            self.gate()

    def test_public_build_flags_forbid_assembly_without_side_effects(self):
        output = self.root/"output"
        with patch.dict("os.environ", {
                "AP_V32_PREVIEW_BUILD": "1", "AP_RELEASE_BUILD": "1"}):
            with self.assertRaisesRegex(ValueError, "non-release"):
                assemble(self.old, self.new, self.sums, self.receipt,
                         REV, output)
        self.assertFalse(output.exists())

    def test_explicit_preview_assembly_flag_is_mandatory(self):
        output = self.root/"output"
        with patch.dict("os.environ", {"AP_V32_PREVIEW_BUILD": "0"}):
            with self.assertRaisesRegex(ValueError, "non-release"):
                assemble(self.old, self.new, self.sums, self.receipt,
                         REV, output)
        self.assertFalse(output.exists())

    def test_existing_output_is_never_replaced(self):
        output = self.root/"existing"
        output.mkdir()
        with patch.dict("os.environ", {
                "AP_V32_PREVIEW_BUILD": "1", "AP_RELEASE_BUILD": "0",
                "AP_V30_APPROVED_RELEASE": "0"}):
            with self.assertRaisesRegex(ValueError, "overwrite"):
                assemble(self.old, self.new, self.sums, self.receipt,
                         REV, output)
        self.assertEqual(list(output.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
