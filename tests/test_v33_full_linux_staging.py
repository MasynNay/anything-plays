"""Source/receipt gates for staging a private full-core 3.3 Linux candidate.

No real installer/ROM/native core is invoked by these unit tests. A distinct
GitHub Actions Linux job does the full Debian repack and verification.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.stage_v33_full_linux import (
    BASELINE, FULL, SOURCE, STATUS, require_private_stage, source_gate,
)


SHA = "a" * 40


class PrivateFullLinuxV33Tests(unittest.TestCase):
    def fixture(self, parent):
        parent = Path(parent)
        stable, candidate = parent / BASELINE, parent / SOURCE
        stable.write_bytes(b"v32-published-exact-baseline" * 60000)
        candidate.write_bytes(b"private-3.3-only-mgba" * 60000)
        stable_hash = hashlib.sha256(stable.read_bytes()).hexdigest()
        current_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
        sums = parent / "SHA256SUMS.txt"
        sums.write_text(stable_hash + "  " + BASELINE + "\n", encoding="utf-8")
        receipt = parent / "V33_CANDIDATE_QA_RECEIPT.json"
        fields = {
            "format": "anything-plays-v33-owner-qa",
            "target": "linux-x64", "source_sha": SHA,
            "channel": "v33_candidate", "version": "3.3.0-qa",
            "settings_namespace": "anything-plays-33-candidate",
            "installer_filename": SOURCE,
            "installer_sha256": current_hash,
            "bundled_core_names": ["mgba_libretro.so"],
            "bundled_core_count": 1,
            "public_release_approved": False,
            "hardware_input_tested": False,
            "physical_camera_tested": False,
            "gamecube_bundled": False,
            "full_18_console_gameplay_tested": False,
            "installer_fully_tested_on_real_host": False,
        }
        receipt.write_text(json.dumps(fields), encoding="utf-8")
        return stable, candidate, sums, receipt, fields

    def test_pinned_v32_baseline_plus_private_33_receipt(self):
        with TemporaryDirectory() as directory:
            stable, candidate, sums, receipt, _ = self.fixture(directory)
            self.assertEqual(
                source_gate(stable, candidate, sums, receipt, SHA),
                (stable, candidate),
            )
            self.assertIn("fullqa1", FULL)
            self.assertIn("UNRELEASED", STATUS)
            self.assertNotIn("3.2.0", FULL)
            self.assertEqual(BASELINE, "anything-plays-31_3.2.0_amd64.deb")

    def test_corrupt_baseline_or_candidate_hash_fails_closed(self):
        with TemporaryDirectory() as directory:
            stable, candidate, sums, receipt, fields = self.fixture(directory)
            stable.write_bytes(b"tampered public 3.2" * 90000)
            with self.assertRaisesRegex(ValueError, "SHA256"):
                source_gate(stable, candidate, sums, receipt, SHA)
            sums.write_text(
                hashlib.sha256(stable.read_bytes()).hexdigest()
                + "  " + BASELINE + "\n", encoding="utf-8",
            )
            candidate.write_bytes(b"tampered 3.3 QA" * 100000)
            with self.assertRaisesRegex(ValueError, "reviewed"):
                source_gate(stable, candidate, sums, receipt, SHA)
            fields["installer_sha256"] = hashlib.sha256(
                candidate.read_bytes()
            ).hexdigest()
            receipt.write_text(json.dumps(fields), encoding="utf-8")
            self.assertEqual(
                source_gate(stable, candidate, sums, receipt, SHA),
                (stable, candidate),
            )

    def test_public_build_flag_identity_and_scope_forgery_rejected(self):
        with TemporaryDirectory() as directory:
            stable, candidate, sums, receipt, record = self.fixture(directory)
            for field, bad in (
                ("source_sha", "b" * 40),
                ("channel", "v32_stable_candidate"),
                ("settings_namespace", "anything-plays-31"),
                ("bundled_core_count", 11),
                ("gamecube_bundled", True),
                ("public_release_approved", True),
                ("physical_camera_tested", True),
                ("untrusted_key", "/Users/private"),
            ):
                with self.subTest(field=field):
                    modified = {**record, field: bad}
                    receipt.write_text(json.dumps(modified), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        source_gate(stable, candidate, sums, receipt, SHA)
            for bad_sha in ("invalid", SHA[:39], SHA.upper(), None):
                with self.subTest(bad_sha=bad_sha):
                    with self.assertRaises(ValueError):
                        source_gate(stable, candidate, sums, receipt, bad_sha)

    def test_requires_private_flags_and_blocks_stable_release(self):
        env = {
            "AP_V33_CANDIDATE": "1", "AP_V30_MINIMAL_CORE_BUILD": "1",
            "AP_RELEASE_BUILD": "0", "AP_V30_APPROVED_RELEASE": "0",
            "AP_V32_PREVIEW_BUILD": "0", "AP_V32_STABLE_CANDIDATE": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            require_private_stage()
        for name, value in (
            ("AP_V33_CANDIDATE", "0"), ("AP_V30_MINIMAL_CORE_BUILD", "0"),
            ("AP_RELEASE_BUILD", "1"), ("AP_V30_APPROVED_RELEASE", "1"),
            ("AP_V32_STABLE_CANDIDATE", "1"), ("AP_V32_PREVIEW_BUILD", "1"),
        ):
            with self.subTest(name=name):
                with patch.dict(os.environ, {**env, name: value}, clear=True):
                    with self.assertRaisesRegex(ValueError, "PRIVATE"):
                        require_private_stage()

    def test_rejects_hardlinked_receipts_and_wrong_filenames(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            stable, candidate, sums, receipt, _ = self.fixture(root)
            linked = root / "linked.json"
            os.link(receipt, linked)
            with self.assertRaisesRegex(ValueError, "verification"):
                source_gate(stable, candidate, sums, receipt, SHA)
            linked.unlink()
            wrong = root / "wrong-private-candidate.deb"
            candidate.rename(wrong)
            with self.assertRaisesRegex(ValueError, "QA input"):
                source_gate(stable, wrong, sums, receipt, SHA)


if __name__ == "__main__":
    unittest.main()
