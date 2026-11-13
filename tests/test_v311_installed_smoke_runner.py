"""OS installer smoke runner refuses counterfeit or source-only packages."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.run_v311_stable_installed_smoke import launch
from tools.verify_v311_installed_smoke import QA_STATUS
from tools.verify_v311_stable_source_stage import INSTALLERS

SHA = "a" * 40


class RealNativeInstallSmokeGateTests(unittest.TestCase):
    def fixture(self, root, target="linux-x64"):
        root = Path(root)
        archive = root / INSTALLERS[target]
        archive.write_bytes(b"0" * (1024*1024 + 5))
        receipt = root / "full.json"
        receipt.write_text(json.dumps({
            "status": QA_STATUS[target],
            "target": target,
            "installer": archive.name,
            "native_core_count": 11,
            "console_profiles": 18,
            "identity_channel": "v311_stable_candidate",
            "public_release_approved": False,
        }), "utf-8")
        return archive, receipt, root/"evidence"

    def test_no_mislabeled_qa_or_one_core_installer_reaches_unzip(self):
        with TemporaryDirectory() as tmp:
            archive,receipt,output=self.fixture(tmp)
            for key,value in (
                ("native_core_count",1),
                ("console_profiles",3),
                ("identity_channel","v311_candidate"),
                ("public_release_approved",True),
            ):
                with self.subTest(key=key):
                    original=json.loads(receipt.read_text("utf-8"))
                    receipt.write_text(json.dumps({**original,key:value}),"utf-8")
                    with patch("tools.run_v311_stable_installed_smoke.subprocess.run") as command:
                        with self.assertRaises(ValueError):
                            launch("linux-x64",archive,receipt,SHA,output)
                        command.assert_not_called()
                    receipt.write_text(json.dumps(original),"utf-8")

    def test_wrong_version_and_symlinked_receipt_do_not_launch_binary(self):
        with TemporaryDirectory() as tmp:
            archive,receipt,output=self.fixture(tmp)
            old=archive.with_name("anything-plays-31_3.1.0_amd64.deb")
            archive.rename(old)
            with patch("tools.run_v311_stable_installed_smoke.subprocess.run") as command:
                with self.assertRaises(ValueError):
                    launch("linux-x64",old,receipt,SHA,output)
                command.assert_not_called()
            old.rename(archive)
            shadow=receipt.with_name("linked.json")
            shadow.symlink_to(receipt)
            with self.assertRaises(ValueError):
                launch("linux-x64",archive,shadow,SHA,output)

    def test_prior_installed_desktop_evidence_is_never_overwritten(self):
        with TemporaryDirectory() as tmp:
            archive,receipt,output=self.fixture(tmp)
            output.mkdir()
            with patch("tools.run_v311_stable_installed_smoke.subprocess.run") as command:
                with self.assertRaises(ValueError):
                    launch("linux-x64",archive,receipt,SHA,output)
                command.assert_not_called()


if __name__=="__main__":
    unittest.main()
