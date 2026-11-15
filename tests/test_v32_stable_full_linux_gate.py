"""Fail-closed full-native stable-upgrade staging gates (no real RPM/ROM)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.stage_v32_stable_full_linux import (
    SOURCE, BASELINE, STATUS, source_gate,
)


class FullStableLinuxGateTests(unittest.TestCase):
    def fixture(self, root):
        root = Path(root)
        baseline = root / BASELINE
        source = root / SOURCE
        baseline.write_bytes(b"stable" * 180000)
        source.write_bytes(b"source" * 180000)
        from tools.stage_v32_full_linux import sha256
        sums = root / "SHA256SUMS.txt"
        sums.write_text(sha256(baseline) + "  " + BASELINE + "\n", "utf-8")
        receipt = root / "source.json"
        payload = {
            "schema_version": 1,
            "status": "PRIVATE_3_2_STABLE_UPGRADE_ONE_CORE_SOURCE_QA_NOT_RELEASE",
            "target": "linux-x64",
            "source_revision": "a" * 40,
            "installer": SOURCE, "installer_sha256": sha256(source),
            "installer_bytes": source.stat().st_size,
            "identity_channel": "v32_stable_candidate",
            "identity_marker": "_internal/assets/v31_build_identity.json",
            "stable_settings_namespace": "anything-plays-31",
            "stable_package_identity_matches_311": True,
            "native_core_count": 1,
            "full_native_release_tested": False,
            "real_user_settings_migration_tested": False,
            "physical_hardware_tested": False,
            "redistribution_approved": False,
            "public_release_approved": False,
        }
        receipt.write_text(json.dumps(payload), "utf-8")
        return baseline, source, sums, receipt, payload

    def test_valid_immutable_original_and_source_receipt_pass(self):
        with TemporaryDirectory() as td:
            a,b,c,d,_ = self.fixture(td)
            self.assertEqual(source_gate(a,b,c,d,"a"*40),(a,b))

    def test_reject_changed_public_stable_bytes(self):
        with TemporaryDirectory() as td:
            a,b,c,d,_ = self.fixture(td)
            a.write_bytes(b"changed" * 160000)
            with self.assertRaisesRegex(ValueError, "SHA256"):
                source_gate(a,b,c,d,"a"*40)

    def test_reject_forged_source_receipt_and_release_approval(self):
        with TemporaryDirectory() as td:
            a,b,c,d,data = self.fixture(td)
            for key,value in (
                ("source_revision","b"*40),
                ("native_core_count",11),
                ("public_release_approved",True),
                ("identity_marker","../../redirected.json"),
                ("settings_namespace","anything-plays-32-preview"),
                ("installer_sha256","0"*64),
            ):
                with self.subTest(key=key):
                    altered=dict(data)
                    altered[key]=value
                    d.write_text(json.dumps(altered),"utf-8")
                    with self.assertRaises(ValueError):
                        source_gate(a,b,c,d,"a"*40)


if __name__ == "__main__":
    unittest.main()
