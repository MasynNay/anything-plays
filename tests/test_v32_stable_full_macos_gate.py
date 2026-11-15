"""Private stable-upgrade Mac provenance/identity gate unit tests."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.stage_v32_stable_full_macos import (
    names, source_gate, STATUS,
)
from tools.stage_v32_full_linux import sha256
from tools.verify_v32_stable_upgrade_source import STATUS as SOURCE_STATUS


class MacStableFullGateTests(unittest.TestCase):
    def fixture(self, root, arch):
        root=Path(root)
        stable_name,source_name,_=names(arch)
        stable=root/stable_name
        newer=root/source_name
        stable.write_bytes(b"s" * (1024*1024+10))
        newer.write_bytes(b"n" * (1024*1024+10))
        sums=root/"SHA256SUMS.txt"
        sums.write_text(sha256(stable)+"  "+stable_name+"\n","utf-8")
        receipt=root/"source.json"
        record={
            "schema_version":1,
            "status":SOURCE_STATUS,
            "target":"macos-"+arch,
            "source_revision":"a"*40,
            "installer":source_name,"installer_sha256":sha256(newer),
            "installer_bytes":newer.stat().st_size,
            "identity_channel":"v32_stable_candidate",
            "identity_marker":"_internal/assets/v31_build_identity.json",
            "stable_settings_namespace":"anything-plays-31",
            "stable_package_identity_matches_311":True,
            "native_core_count":1,
            "full_native_release_tested":False,
            "real_user_settings_migration_tested":False,
            "physical_hardware_tested":False,
            "redistribution_approved":False,
            "public_release_approved":False,
        }
        receipt.write_text(json.dumps(record),"utf-8")
        return stable,newer,sums,receipt,record

    def test_real_upgrade_names_and_provenance_accept_originals(self):
        with TemporaryDirectory() as td:
            for arch in ("x64","arm64"):
                stable,newer,sums,receipt,_=self.fixture(Path(td)/arch if False else td, arch)
                self.assertEqual(
                    source_gate(arch,stable,newer,sums,receipt,"a"*40),(stable,newer)
                )
                if arch=="x64":
                    # files live in one synthetic root; remove to avoid a
                    # second SHA256SUMS file writing over the same source.
                    pass
        self.assertIn("STABLE_UPGRADE",STATUS)

    def test_modified_public_binary_fails_checksum(self):
        with TemporaryDirectory() as td:
            old,new,sums,receipt,_=self.fixture(td,"arm64")
            old.write_bytes(b"x" * (1024*1024+10))
            with self.assertRaisesRegex(ValueError,"checksum"):
                source_gate("arm64",old,new,sums,receipt,"a"*40)

    def test_forged_receipt_or_approval_never_succeeds(self):
        with TemporaryDirectory() as td:
            old,new,sums,receipt,original=self.fixture(td,"x64")
            for key,value in (
                ("native_core_count",11),
                ("public_release_approved",True),
                ("identity_channel","v32_preview"),
                ("identity_marker","../../unsafe"),
                ("installer_sha256","z"*64),
            ):
                with self.subTest(key=key):
                    wrong=dict(original)
                    wrong[key]=value
                    receipt.write_text(json.dumps(wrong),"utf-8")
                    with self.assertRaises(ValueError):
                        source_gate("x64",old,new,sums,receipt,"a"*40)


if __name__=="__main__":
    unittest.main()
