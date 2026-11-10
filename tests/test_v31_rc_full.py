"""Prove the full-library RC1 QA assembler refuses mixed-source inputs.

These synthetic tests don't claim real controller or retail-game verification.
The candidate's GUI is built from the pinned current source revision on
all four hosts; eleven emulator binaries come from the exact public 3.0
native bundle with independently checked hashes.
"""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import (
    assemble_v31_full_linux as linux,
    assemble_v31_full_windows as windows,
    assemble_v31_full_macos as mac,
)

RC_SHA = "86baa6972ed923540f6ab49b636652a0f499d45c"


class FullReleaseCandidateInputs(unittest.TestCase):
    def test_rc_source_revision_is_exactly_pinned_across_four_hosts(self):
        self.assertEqual(linux.RC_SOURCE_REVISION, RC_SHA)
        self.assertEqual(windows.RC_SOURCE_REVISION, RC_SHA)
        self.assertEqual(mac.RC_SOURCE_REVISION, RC_SHA)

    def test_rc_linux_accepts_only_matching_source_and_public_native_hash(self):
        with TemporaryDirectory() as temp:
            p = Path(temp)
            old, new = p/linux.STABLE, p/linux.RC_PREVIEW
            old.write_bytes(b"stable-native")
            new.write_bytes(b"source-built-rc-app")
            sums, receipt = p/"SHA256SUMS.txt", p/"RC1_APP_STAGE_RECEIPT.json"
            sums.write_text(linux.sha(old)+"  "+linux.STABLE+"\n", "utf-8")
            manifest = {
                "installer": new.name, "target": "linux-x64",
                "sha256": linux.sha(new), "source_revision": RC_SHA,
            }
            receipt.write_text(json.dumps(manifest), "utf-8")
            self.assertEqual(
                linux.validate_inputs(old, new, sums, receipt, rc1=True),
                linux.sha(old),
            )
            manifest["source_revision"] = linux.SOURCE_REVISION
            receipt.write_text(json.dumps(manifest), "utf-8")
            with self.assertRaises(ValueError):
                linux.validate_inputs(old, new, sums, receipt, rc1=True)
            with self.assertRaises(ValueError):
                linux.validate_inputs(old, new, sums, receipt, rc1=False)

    def test_rc_windows_accepts_only_source_receipt_and_known_stable_hash(self):
        with TemporaryDirectory() as temp:
            p = Path(temp)
            old, new = p/windows.STABLE, p/windows.RC_PREVIEW
            old.write_bytes(b"stable-win")
            new.write_bytes(b"MZ" + b"fresh")
            sums, receipt = p/"SHA256SUMS.txt", p/"RC1_APP_STAGE_RECEIPT.json"
            sums.write_text(windows.hash_file(old)+"  "+windows.STABLE+"\n", "utf-8")
            record = {
                "target": "windows-x64", "installer": new.name,
                "source_revision": RC_SHA, "sha256": windows.hash_file(new),
            }
            receipt.write_text(json.dumps(record), "utf-8")
            self.assertEqual(
                windows.check_inputs(old, new, sums, receipt, rc1=True),
                windows.hash_file(old),
            )
            new.write_bytes(new.read_bytes()+b"bad")
            with self.assertRaises(ValueError):
                windows.check_inputs(old, new, sums, receipt, rc1=True)

    def test_both_macs_use_genuine_rc_source_dmg_identity_and_reject_mismatch(self):
        for arch in ("arm64", "x64"):
            with self.subTest(arch=arch), TemporaryDirectory() as temp:
                p = Path(temp)
                old = p/("AnythingPlays-3.0.0-macos-"+arch+".dmg")
                new = p/("AnythingPlays-3.1.0-rc1-macos-"+arch+".dmg")
                old.write_bytes(b"stable-mac")
                new.write_bytes(b"rc-mac")
                sums, receipt = p/"SHA256SUMS.txt", p/"RC1_APP_STAGE_RECEIPT.json"
                sums.write_text(mac.digest(old)+"  "+old.name+"\n", "utf-8")
                record = {
                    "target": "macos-"+arch, "installer": new.name,
                    "source_revision": RC_SHA, "sha256": mac.digest(new),
                }
                receipt.write_text(json.dumps(record), "utf-8")
                self.assertEqual(
                    mac.verify_inputs(arch, old, new, sums, receipt, rc1=True),
                    mac.digest(old),
                )
                record["target"] = "macos-"+("x64" if arch=="arm64" else "arm64")
                receipt.write_text(json.dumps(record), "utf-8")
                with self.assertRaises(ValueError):
                    mac.verify_inputs(arch, old, new, sums, receipt, rc1=True)

    def test_rc_staging_cannot_use_production_or_wrong_channel(self):
        inputs = [Path("not-present")]*5
        settings = {
            "AP_V31_FULL_TEST_CORES": "1", "AP_V31_RC": "1",
            "AP_V31_PREVIEW": "0", "AP_RELEASE_BUILD": "1",
            "AP_V30_APPROVED_RELEASE": "0",
        }
        with patch.dict(os.environ, settings):
            for make in (linux.build, windows.build):
                with self.subTest(platform=make.__module__), self.assertRaises(ValueError):
                    make(*inputs, rc1=True)
            with self.assertRaises(ValueError):
                mac.build("arm64", *inputs, rc1=True)

    def test_full_rc_workflows_only_generate_unreleased_qa_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        workflow = root/".github/workflows/v31-full-rc1-qa.yml"
        contents = workflow.read_text("utf-8")
        self.assertIn("42863846059", contents)
        self.assertIn("AP_V31_RC: '1'", contents)
        self.assertIn("AP_V31_FULL_TEST_CORES: '1'", contents)
        self.assertIn("--rc1", contents)
        self.assertIn("actions/upload-artifact@v4", contents)
        self.assertNotIn("contents: write", contents)
        self.assertNotIn("gh release create", contents)
        self.assertNotIn("softprops/action-gh-release", contents)
        self.assertNotIn("AP_RELEASE_BUILD: '1'", contents)


if __name__ == "__main__":
    unittest.main()
