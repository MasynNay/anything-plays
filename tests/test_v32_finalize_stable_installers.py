"""Private-to-public 3.2 installer metadata gates, no native package building."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.finalize_v32_stable_installers import TARGETS, validate_qa_receipt, STATUS
from tools.stage_v32_full_linux import sha256


class FinalizeV32Tests(unittest.TestCase):
    def fixture(self, td, target):
        stage, public, status = TARGETS[target]
        source=Path(td)/stage
        source.write_bytes(b"Q"*1100000)
        report=Path(td)/"receipt.json"
        flags={
            "schema_version":1,"status":status,"target":target,
            "source_revision":"a"*40,"installer":stage,
            "installer_sha256":sha256(source),"native_core_count":11,
            "console_profiles":18,"native_core_bytes_preserved":True,
            "stable_settings_namespace":"anything-plays-31",
            "public_release_approved":False,
            "redistribution_approved":False,
        }
        report.write_text(json.dumps(flags),"utf-8")
        return source, report, flags

    def test_all_four_require_11_core_verified_original_sources(self):
        for target in TARGETS:
            with self.subTest(target=target), TemporaryDirectory() as td:
                source, report, _=self.fixture(td,target)
                actual, public=validate_qa_receipt(target,source,report,"a"*40)
                self.assertEqual(actual,source)
                self.assertIn("3.2.0",public)
                self.assertNotIn("QA",public)
        self.assertIn("NOT_YET_PUBLISHED",STATUS)

    def test_reject_forged_approval_core_count_and_digest(self):
        with TemporaryDirectory() as td:
            source, report, original=self.fixture(td,"linux-x64")
            for key,bad in (
                ("native_core_count",1),("console_profiles",19),
                ("native_core_bytes_preserved",False),
                ("public_release_approved",True),
                ("redistribution_approved",True),
                ("source_revision","b"*40),
                ("installer_sha256","0"*64),
            ):
                with self.subTest(key=key):
                    changed={**original,key:bad}
                    report.write_text(json.dumps(changed),"utf-8")
                    with self.assertRaises(ValueError):
                        validate_qa_receipt("linux-x64",source,report,"a"*40)


if __name__=="__main__":
    unittest.main()
