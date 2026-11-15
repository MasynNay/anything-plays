"""Source/receipt checks for private Windows same-identity full-native staging."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.stage_v32_stable_full_windows import (
    BASELINE, SOURCE, checked_windows_source,
)
from tools.stage_v32_full_linux import sha256
from tools.verify_v32_stable_upgrade_source import STATUS


class WindowsStageGateTests(unittest.TestCase):
    def make_data(self, root):
        root=Path(root)
        old=root/BASELINE
        new=root/SOURCE
        old.write_bytes(b"b" * (1024*1024+10))
        new.write_bytes(b"n" * (1024*1024+10))
        sums=root/"SHA256SUMS.txt"
        sums.write_text(sha256(old)+"  "+BASELINE+"\n","utf-8")
        evidence=root/"receipt.json"
        record={
            "schema_version":1,"status":STATUS,"target":"windows-x64",
            "source_revision":"a"*40,"installer":SOURCE,
            "installer_sha256":sha256(new),"installer_bytes":new.stat().st_size,
            "identity_channel":"v32_stable_candidate",
            "identity_marker":"_internal/assets/v31_build_identity.json",
            "stable_settings_namespace":"anything-plays-31",
            "stable_package_identity_matches_311":True,"native_core_count":1,
            "full_native_release_tested":False,
            "real_user_settings_migration_tested":False,
            "physical_hardware_tested":False,"redistribution_approved":False,
            "public_release_approved":False,
        }
        evidence.write_text(json.dumps(record),"utf-8")
        return old,new,sums,evidence,record

    def test_complete_valid_windows_source(self):
        with TemporaryDirectory() as td:
            old,new,sums,receipt,_=self.make_data(td)
            self.assertEqual(
                checked_windows_source(old,new,sums,receipt,"a"*40),(old,new)
            )

    def test_reject_modified_stable_binary(self):
        with TemporaryDirectory() as td:
            old,new,sums,receipt,_=self.make_data(td)
            old.write_bytes(b"changed"*160000)
            with self.assertRaisesRegex(ValueError,"SHA256"):
                checked_windows_source(old,new,sums,receipt,"a"*40)

    def test_reject_forged_source_identity_and_approval(self):
        with TemporaryDirectory() as td:
            old,new,sums,receipt,original=self.make_data(td)
            for key,value in (
                ("native_core_count",11),
                ("public_release_approved",True),
                ("stable_settings_namespace","anything-plays-32-preview"),
                ("source_revision","f"*40),
                ("installer_sha256","b"*64),
                ("identity_marker","../../rogue.json"),
            ):
                with self.subTest(key=key):
                    altered=dict(original)
                    altered[key]=value
                    receipt.write_text(json.dumps(altered),"utf-8")
                    with self.assertRaises(ValueError):
                        checked_windows_source(old,new,sums,receipt,"a"*40)


if __name__=="__main__":
    unittest.main()
