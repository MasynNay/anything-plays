"""No public 3.1.1 package without four full native+GUI source receipts.

Synthetic native binary fixtures only; fake source source ZIP hashing is
mocked explicitly to test control flow, never to create a release package.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.stage_v311_private_release_review import (
    OLD_SHA, REPORT_NAMES, SOURCE_ZIP, SOURCE_ZIP_SHA, STAGED_STATUS,
    assemble,
)
from tools.verify_v311_installed_smoke import PASSED_STATUS, QA_STATUS
from tools.verify_v311_stable_source_stage import INSTALLERS

REV = "a" * 40


def digest(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


class StagePrivateReviewTests(unittest.TestCase):
    def sample(self, location):
        base = Path(location)
        root = base / "all-four"
        root.mkdir()
        source = base / SOURCE_ZIP
        source.write_bytes(b"FAKE unapproved test source")
        for target, name in INSTALLERS.items():
            folder = root / target
            folder.mkdir()
            file = folder / name
            file.write_bytes(b"A" * (1024*1024 + 5))
            h = digest(file)
            native = {
                "status":QA_STATUS[target],"target":target,"installer":name,
                "version":"3.1.1","identity_channel":"v311_stable_candidate",
                "settings_namespace":"anything-plays-31",
                "stable_in_place_update":True,"native_core_count":11,
                "console_profiles":18,"public_release_approved":False,
                "full_four_platform_311_verified":False,
                "sourcebuilt_ffmpeg_off_camera_wheel_sha256":"b"*64,
            }
            if target=="linux-x64":
                native.update({
                    "installer_sha256":h,"app_source_sha":REV,
                    "baseline_3_1_0_sha256":OLD_SHA[target],
                })
            else:
                native.update({
                    "sha256":h,"new_source_revision":REV,
                    "old_stable_sha256":OLD_SHA[target],
                })
            (folder/REPORT_NAMES[target]).write_text(json.dumps(native),"utf-8")
            installed = {
                "status":PASSED_STATUS,"target":target,"installer":name,
                "source_revision":REV,"installer_sha256":h,
                "native_core_count":11,"console_profiles":18,
                "frozen_desktop_started":True,
                "stream_mode_started_and_closed":True,
                "stable_settings_namespace_retained":True,
                "hardware_gameplay_verified":False,
                "physical_camera_verified":False,
                "physical_controller_verified":False,
                "third_party_relinking_verified":False,
                "public_release_approved":False,
            }
            (folder/"V311_INSTALLED_FULL_GUI_RECEIPT.json").write_text(
                json.dumps(installed),"utf-8")
        return root,source,base/"review"

    def checked_stage(self, root, source, output):
        # The input is an intentionally fake 30-byte source file; mock only
        # its digest to simulate the already independently pinned 3.1.0 ZIP.
        actual = digest
        def source_only_digest(p):
            return SOURCE_ZIP_SHA if Path(p).name==SOURCE_ZIP else actual(p)
        with patch("tools.stage_v311_private_release_review.digest",
                   side_effect=source_only_digest):
            return assemble(root,source,REV,output)

    def test_all_four_native_original_gui_receipts_stage_exact_8_unapproved_items(self):
        with TemporaryDirectory() as temp:
            root,src,out=self.sample(temp)
            result=self.checked_stage(root,src,out)
            self.assertEqual(result["status"],STAGED_STATUS)
            self.assertEqual(len(result["native_installers"]),4)
            self.assertFalse(result["public_release_approved"])
            self.assertFalse(result["complete_corresponding_source_and_relink_review_approved"])
            self.assertEqual(len(list(out.iterdir())),8)
            checks=(out/"SHA256SUMS.txt").read_text()
            self.assertEqual(len(checks.splitlines()),7)
            self.assertIn("AnythingPlaysSetup-3.1.1.exe",checks)
            self.assertIn(SOURCE_ZIP,checks)

    def test_no_one_core_tampered_gui_or_unsigned_forged_approval(self):
        for filename,key,val in (
            ("V311_FULL_LINUX_QA_RECEIPT.json","native_core_count",1),
            ("V311_INSTALLED_FULL_GUI_RECEIPT.json","frozen_desktop_started",False),
            ("V311_INSTALLED_FULL_GUI_RECEIPT.json","public_release_approved",True),
            ("V311_FULL_LINUX_QA_RECEIPT.json","app_source_sha","b"*40),
            ("V311_FULL_LINUX_QA_RECEIPT.json","baseline_3_1_0_sha256","0"*64),
            ("V311_FULL_LINUX_QA_RECEIPT.json","sourcebuilt_ffmpeg_off_camera_wheel_sha256","not-hash"),
        ):
            with self.subTest(filename=filename,key=key),TemporaryDirectory() as temp:
                root,src,out=self.sample(temp)
                path=root/"linux-x64"/filename
                original=json.loads(path.read_text())
                path.write_text(json.dumps({**original,key:val}),"utf-8")
                with self.assertRaises(ValueError):
                    self.checked_stage(root,src,out)
                self.assertFalse(out.exists())

    def test_original_source_must_not_be_relabelled_or_forged(self):
        with TemporaryDirectory() as temp:
            root,src,out=self.sample(temp)
            with self.assertRaisesRegex(ValueError,"original public 3.1.0"):
                assemble(root,src,REV,out)
            self.assertFalse(out.exists())
            renamed=src.with_name("AnythingPlays-3.1.1-ORIGINAL-SOURCE.zip")
            src.rename(renamed)
            with self.assertRaises(ValueError):
                self.checked_stage(root,renamed,out)


if __name__=="__main__":
    unittest.main()
