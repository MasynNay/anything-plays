"""Fail-closed Windows 3.2 original-source native package preflight tests.

No Inno installer is extracted, compiled or executed by these unit tests.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.stage_v32_full_windows import (
    BASELINE, FULL, STATUS, assemble, source_gate,
)
from tools.stage_v32_full_linux import sha256
from tools.verify_v32_preview import FILES

SHA = "b" * 40


class V32FullWindowsGateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="ap32-fullwin-preflight-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.old = self.root/BASELINE
        self.new = self.root/FILES["windows-x64"]
        self.old.write_bytes(b"oldWindows" * 120000)
        self.new.write_bytes(b"newWindows" * 120000)
        self.sums = self.root/"SHA256SUMS.txt"
        self.sums.write_text(sha256(self.old) + "  " + BASELINE + "\n")
        self.receipt = self.root/"V32_PRIVATE_PREVIEW_RECEIPT.json"
        self.record = {
            "status": "UNRELEASED_PRIVATE_QA_ONLY",
            "channel": "v32_preview",
            "version": "3.2.0-preview1",
            "target": "windows-x64",
            "installer": FILES["windows-x64"],
            "source_revision": SHA,
            "sha256": sha256(self.new),
            "size_bytes": self.new.stat().st_size,
            "settings_namespace": "anything-plays-32-preview",
            "bundled_console_profiles": ["gb", "gbc", "gba"],
            "bundled_core_names": ["mgba"],
            "public_release_approved": False,
            "all_18_consoles_verified": False,
        }
        self.save()

    def save(self):
        self.receipt.write_text(json.dumps(self.record), encoding="utf-8")

    def check(self):
        return source_gate(self.old, self.new, self.sums, self.receipt, SHA)

    def test_real_name_and_matching_exact_source_pass(self):
        self.assertEqual(self.check(), (self.old, self.new))
        self.assertEqual(FULL, "AnythingPlaysSetup-3.2.0-fullqa1.exe")
        self.assertIn("NOT_RELEASE", STATUS)

    def test_published_stable_bytes_must_match_SHA256SUMS(self):
        self.old.write_bytes(b"!" + self.old.read_bytes()[1:])
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.check()

    def test_private_source_bytes_and_commit_cannot_change(self):
        self.new.write_bytes(b"!" + self.new.read_bytes()[1:])
        with self.assertRaisesRegex(ValueError, "receipt"):
            self.check()
        with self.assertRaisesRegex(ValueError, "Git source"):
            source_gate(self.old, self.new, self.sums, self.receipt, "wrong")

    def test_never_accept_false_full_build_approval(self):
        for key, forged in (
            ("public_release_approved", True),
            ("all_18_consoles_verified", True),
            ("settings_namespace", "anything-plays-31"),
            ("bundled_core_names", ["mgba", "dolphin"]),
            ("source_revision", "0" * 40),
        ):
            with self.subTest(key=key):
                old = self.record[key]
                self.record[key] = forged
                self.save()
                with self.assertRaisesRegex(ValueError, "receipt"):
                    self.check()
                self.record[key] = old
        self.save()
        self.check()

    def test_rejects_linked_input_and_wrong_asset_name(self):
        other = self.root/"SomethingSetup.exe"
        other.symlink_to(self.old)
        with self.assertRaisesRegex(ValueError, "wrongly named"):
            source_gate(other, self.new, self.sums, self.receipt, SHA)
        self.old.unlink()
        self.old.symlink_to(other)
        with self.assertRaisesRegex(ValueError, "linked"):
            self.check()

    def test_public_or_missing_private_flags_fail_before_install(self):
        dest = self.root/"output"
        with patch.dict("os.environ", {
            "AP_V32_PREVIEW_BUILD": "1", "AP_RELEASE_BUILD": "1",
        }):
            with self.assertRaisesRegex(ValueError, "non-release"):
                assemble(self.old, self.new, self.sums, self.receipt, SHA, dest)
        with patch.dict("os.environ", {"AP_V32_PREVIEW_BUILD": "0"}):
            with self.assertRaisesRegex(ValueError, "non-release"):
                assemble(self.old, self.new, self.sums, self.receipt, SHA, dest)
        self.assertFalse(dest.exists())

    def test_existing_output_is_never_overwritten(self):
        dest = self.root/"output"
        dest.mkdir()
        with patch.dict("os.environ", {
            "AP_V32_PREVIEW_BUILD": "1", "AP_RELEASE_BUILD": "0",
            "AP_V30_APPROVED_RELEASE": "0",
        }):
            with self.assertRaisesRegex(ValueError, "overwrite"):
                assemble(self.old, self.new, self.sums, self.receipt, SHA, dest)
        self.assertEqual(list(dest.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
