"""Synthetic, non-executable test for authentic original MPL2 mGBA capture.

Every fixture here is synthetic metadata, never binary redistribution approval.
Real Windows/Linux/Mac mGBA compilation + original cartridge A/V is CI-only.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.capture_v30_mgba_original_source import (
    SOURCE_REVISION, SOURCE_REPOSITORY, EXTENSIONS, capture,
    validate_binary, STATUS,
)


class PinnedMGBASourceContracts(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def _prepare(self, target="linux-x64", revision=SOURCE_REVISION):
        source=self.root/"original-mgba"
        source.mkdir()
        subprocess.run(["git","init","-q",str(source)],check=True)
        (source/"src").mkdir()
        (source/"src"/"synthetic-original-code.c").write_text(
            "/* SOURCE-ONLY-SYNTHETIC, never a real emulator */\n"+
            ("int original_source_fixture_counter = 123;\n"*11000),encoding="utf-8")
        (source/"LICENSE").write_text(
            "Mozilla Public License Version 2.0\n1. Definitions\n3. Responsibilities\n"
            "SYNTHETIC TEST ONLY. No distribution permission implied.\n",
            encoding="utf-8")
        subprocess.run(["git","-C",str(source),"add","."],check=True)
        subprocess.run(["git","-C",str(source),
                        "-c","user.name=Source-Only-Test",
                        "-c","user.email=noreply@example.invalid",
                        "commit","-qm","synthetic original source only"],check=True)
        actual=subprocess.check_output(["git","-C",str(source),"rev-parse","HEAD"],
                                        text=True).strip()
        raw={"windows-x64":b"MZ", "linux-x64":b"\x7fELF",
             "macos-arm64":b"\xcf\xfa\xed\xfe",
             "macos-x64":b"\xcf\xfa\xed\xfe"}[target]+b"FAKE NATIVE NOT EXECUTABLE"*3600
        image=self.root/("mgba_libretro"+EXTENSIONS[target])
        image.write_bytes(raw)
        return source,image,actual

    def test_real_source_revision_must_match_and_preserve_mpl(self):
        src,img,sha=self._prepare()
        with patch("tools.capture_v30_mgba_original_source.SOURCE_REVISION",sha),\
             patch.dict(os.environ,{"AP_RELEASE_BUILD":"0","AP_V30_APPROVED_RELEASE":"0"},clear=True):
            out=self.root/"record"
            result=capture(src,img,out,"linux-x64")
        self.assertEqual(result["status"],STATUS)
        self.assertEqual(result["license_family"],"MPL-2.0")
        self.assertEqual(result["original_upstream"],SOURCE_REPOSITORY)
        self.assertEqual(result["native_sha256"],hashlib.sha256(img.read_bytes()).hexdigest())
        self.assertEqual(result["exact_upstream_revision"],sha)
        self.assertEqual(result["source_checkout_verified"],True)
        self.assertEqual(result["native_sha256"],hashlib.sha256((out/img.name).read_bytes()).hexdigest())
        self.assertEqual(result, json.loads((out/"PINNED_MGBA_SOURCE_NATIVE_UNAPPROVED.json").read_text()))
        self.assertTrue((out/result["original_source_tar"]).is_file())
        for flag in ("binary_redistribution_approved","combined_gpl_license_review_approved",
                     "third_party_compiler_and_link_deps_rights_reviewed",
                     "physical_qa_approved"):
            self.assertIs(result[flag],False)

    def test_unmatched_source_and_would_be_release_fail_before_writes(self):
        src,img,sha=self._prepare()
        with patch.dict(os.environ,{"AP_RELEASE_BUILD":"0","AP_V30_APPROVED_RELEASE":"0"},clear=True):
            with self.assertRaises(ValueError):
                capture(src,img,self.root/"bad","linux-x64")
        self.assertFalse((self.root/"bad").exists())
        with patch("tools.capture_v30_mgba_original_source.SOURCE_REVISION",sha):
            for mode in ({"AP_RELEASE_BUILD":"1","AP_V30_APPROVED_RELEASE":"0"},
                         {"AP_RELEASE_BUILD":"0","AP_V30_APPROVED_RELEASE":"1"}):
                with patch.dict(os.environ,mode,clear=True):
                    with self.assertRaises(ValueError):
                        capture(src,img,self.root/"blocked","linux-x64")
        self.assertFalse((self.root/"blocked").exists())

    def test_wrong_original_license_rejected(self):
        src,img,sha=self._prepare()
        (src/"LICENSE").write_text("Not MPL")
        with patch("tools.capture_v30_mgba_original_source.SOURCE_REVISION",sha), \
             patch.dict(os.environ,{"AP_RELEASE_BUILD":"0","AP_V30_APPROVED_RELEASE":"0"},clear=True):
            with self.assertRaises(ValueError):
                capture(src,img,self.root/"badlicense","linux-x64")
        self.assertFalse((self.root/"badlicense").exists())

    def test_bad_native_format_rejected(self):
        for target in EXTENSIONS:
            expected={"windows-x64":"dll","linux-x64":"so",
                      "macos-arm64":"dylib","macos-x64":"dylib"}[target]
            self.assertEqual(EXTENSIONS[target],"."+expected)
            with self.assertRaises(ValueError):
                validate_binary("mgba_libretro"+EXTENSIONS[target],b"FAKE"*30000,target)

    def test_true_upstream_source_safeguards_and_four_os_ci(self):
        yml=(Path(__file__).resolve().parents[1]/
             ".github/workflows/v30-mgba-original-source-four-os.yml").read_text("utf-8")
        for name in EXTENSIONS:
            self.assertIn("target: "+name,yml)
        self.assertIn(SOURCE_REVISION,yml)
        self.assertIn("persist-credentials: false",yml)
        self.assertIn("BUILD_LIBRETRO=ON",yml)
        self.assertIn("tools/probe_gb_homebrew.py --system gb",yml)
        self.assertIn("tools/probe_gb_homebrew.py --system gbc",yml)
        self.assertIn("tools/probe_gba_homebrew.py --core",yml)
        self.assertNotIn("gh release create",yml)
        self.assertNotIn("git push",yml)
        self.assertNotIn("gh issue create",yml)


if __name__=="__main__":
    unittest.main()
