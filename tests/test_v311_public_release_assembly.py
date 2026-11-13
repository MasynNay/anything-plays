"""Published v3.1.1 assets require all four authenticated source and GUI reports.

Uses artificial 1MB binaries and a mocked legacy-source hash; none of these
fixtures can ever enter a real release.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.prepare_v311_public_release import (
    OUTPUT_FILES, package, read_review,
)
from tools.stage_v311_private_release_review import (
    SOURCE_ZIP, SOURCE_ZIP_SHA, STAGED_STATUS,
)
from tools.verify_v311_stable_source_stage import INSTALLERS

SHA="a"*40
RUN=43355665931


def sha(path):
    with Path(path).open("rb") as h:
        return hashlib.file_digest(h,"sha256").hexdigest()


class PublicReleasePreparationTests(unittest.TestCase):
    def fixture(self,dirname):
        root=Path(dirname)/"private"
        root.mkdir()
        entries=[]
        checks=[]
        for target,name in INSTALLERS.items():
            path=root/name
            path.write_bytes(b"synthetic test installer"*(1024*1024//24+1))
            digest=sha(path)
            checks.append(f"{digest}  {name}")
            entries.append({
                "target":target,"installer":name,"sha256":digest,
                "app_source_sha":SHA,"native_core_count":11,
                "console_profiles":18,"installed_frozen_gui_verified":True,
            })
        source=root/SOURCE_ZIP
        source.write_bytes(b"fake old source zip")
        checks.append(f"{SOURCE_ZIP_SHA}  {SOURCE_ZIP}")
        manifest={
            "status":STAGED_STATUS,"source_revision":SHA,
            "version":"3.1.1","public_release_approved":False,
            "complete_corresponding_source_and_relink_review_approved":False,
            "real_frozen_gui_tests_passed_on_four_native_hosts":True,
            "native_installers":entries,
        }
        p=root/"V311_PRIVATE_RELEASE_REVIEW_MANIFEST.json"
        p.write_text(json.dumps(manifest),"utf-8")
        checks.append(f"{sha(p)}  {p.name}")
        p=root/"V311_SOURCE_ACCESS_REVIEW_DRAFT.md"
        p.write_text("Synthetic private source limitations; NOT legal clearance","utf-8")
        checks.append(f"{sha(p)}  {p.name}")
        (root/"SHA256SUMS.txt").write_text("\n".join(checks)+"\n","ascii")
        return root,Path(dirname)/"public"

    def signed(self, root, out, *, authorization=True, sha_value=SHA):
        original=sha
        def digest(p):
            return SOURCE_ZIP_SHA if Path(p).name==SOURCE_ZIP else original(p)
        with patch("tools.prepare_v311_public_release.digest", side_effect=digest):
            return package(root,out,sha_value,RUN,authorized=authorization)

    def test_requires_explicit_owner_publication_authorization(self):
        with TemporaryDirectory() as temp:
            root,out=self.fixture(temp)
            with self.assertRaisesRegex(ValueError,"not explicitly authorized"):
                self.signed(root,out,authorization=False)
            self.assertFalse(out.exists())

    def test_all_four_and_same_source_generate_exact_eight_release_items(self):
        with TemporaryDirectory() as temp:
            root,out=self.fixture(temp)
            manifest=self.signed(root,out)
            self.assertEqual({p.name for p in out.iterdir()},OUTPUT_FILES)
            self.assertEqual(len((out/"SHA256SUMS.txt").read_text().splitlines()),7)
            self.assertEqual(manifest["source_revision"],SHA)
            self.assertTrue(manifest["owner_scoped_release_authorized"])
            self.assertFalse(manifest["physical_controller_hardware_accepted"])
            self.assertFalse(manifest["complete_native_corresponding_source_proven_reproducible"])
            self.assertEqual(len(manifest["native_installers"]),4)

    def test_forged_native_qa_hash_or_failed_gui_stops_before_output(self):
        for key,value in (("native_core_count",1),
                          ("installed_frozen_gui_verified",False),
                          ("app_source_sha","0"*40),
                          ("sha256","f"*64)):
            with TemporaryDirectory() as temp:
                root,out=self.fixture(temp)
                marker=root/"V311_PRIVATE_RELEASE_REVIEW_MANIFEST.json"
                body=json.loads(marker.read_text("utf-8"))
                body["native_installers"][0][key]=value
                marker.write_text(json.dumps(body),"utf-8")
                # Test private source checksum must also be re-signed to
                # reach deep logic and still reject the malformed native QA.
                checks=root/"SHA256SUMS.txt"
                lines=checks.read_text("ascii").splitlines()
                lines=[f"{sha(marker)}  {marker.name}" if x.endswith(marker.name)
                       else x for x in lines]
                checks.write_text("\n".join(lines)+"\n","ascii")
                with self.assertRaises(ValueError):
                    self.signed(root,out)
                self.assertFalse(out.exists())

    def test_wrong_source_commit_does_not_pretend_to_match_installed_binaries(self):
        with TemporaryDirectory() as temp:
            root,out=self.fixture(temp)
            with self.assertRaises(ValueError):
                self.signed(root,out,sha_value="b"*40)
            self.assertFalse(out.exists())

    def test_missing_source_checksums_or_unlisted_files_are_not_public(self):
        for change in ("extra","missing","symlink"):
            with self.subTest(change=change),TemporaryDirectory() as temp:
                root,out=self.fixture(temp)
                if change=="extra":
                    (root/"unsafe.txt").write_text("bad","utf-8")
                elif change=="missing":
                    (root/"FINAL_QA_MANIFEST.json").write_text("bad","utf-8")
                else:
                    p=root/next(iter(INSTALLERS.values()))
                    p.unlink()
                    p.symlink_to(root/"SHA256SUMS.txt")
                with self.assertRaises(ValueError):
                    self.signed(root,out)
                self.assertFalse(out.exists())


if __name__=="__main__":
    unittest.main()
