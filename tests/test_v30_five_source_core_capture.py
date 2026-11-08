"""Check only exact native/source evidence is captured for five 2D cores.

All bytes in these fixtures are fake non-executable test files. The tests do
not grant redistribution rights or issue permissions to external maintainers.
"""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.capture_v30_2d_five_source_build import (
    CANDIDATES, EXTENSIONS, capture,
)


def make_git_source(root, candidate):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True, stdout=subprocess.DEVNULL)
    (root/"src").mkdir()
    (root/"src"/"testing-original.c").write_text(
        "/* synthetic Git test source, not an emulator */\n" + ("int test_source_%s = 42;\n" % candidate)*5000,
        encoding="utf-8")
    license_name = CANDIDATES[candidate][1]
    if license_name:
        (root / license_name).write_text(
            "GNU GENERAL PUBLIC LICENSE\nVersion 2, June 1991\n"
            "Synthetic fixture. Not for redistribution.\n", encoding="utf-8")
    subprocess.run(["git","-C",str(root),"add","."],check=True)
    subprocess.run([
        "git","-C",str(root),"-c","user.email=test@example.invalid",
        "-c","user.name=Only-Synthetic-CI","commit","-qm","initial exact synthetic checkout",
    ],check=True)
    return subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                   text=True).strip()


class PinnedOriginalFive2DSourceCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _fixture(self, candidate="fceumm", target="linux-x64"):
        source = self.root/"original"
        revision = make_git_source(source, candidate)
        core = source / (candidate + "_libretro" + EXTENSIONS[target])
        magic = (b"MZ" if target == "windows-x64" else
                 b"\x7fELF" if target == "linux-x64" else b"\xcf\xfa\xed\xfe")
        core.write_bytes(magic + b"synthetic-not-a-real-native-binary" * 3000)
        return source, core, revision

    def test_all_five_captured_with_verbatim_source_git_and_gpl_notices(self):
        for candidate in CANDIDATES:
            with self.subTest(candidate=candidate), TemporaryDirectory() as fresh:
                # Independent nested temp per candidate, no synthetic commit
                # shared across distinct source repo names.
                self.root = Path(fresh)
                source, binary, revision = self._fixture(candidate)
                out = self.root/"evidence"
                with patch.dict(os.environ, {
                    "AP_RELEASE_BUILD": "0", "AP_V30_APPROVED_RELEASE": "0",
                }):
                    result = capture(source,binary,candidate,"linux-x64",revision,out)
                self.assertEqual(result["exact_source_revision"], revision)
                self.assertEqual(result["native_sha256"],
                                 hashlib.sha256(binary.read_bytes()).hexdigest())
                self.assertEqual(result["original_license_notice_copied"],
                                 CANDIDATES[candidate][1] is not None)
                self.assertFalse(result["combined_gpl_version_license_review_approved"])
                self.assertFalse(result["binary_redistribution_approved"])
                self.assertFalse(result["source_submodules_and_deps_independently_reviewed"])
                self.assertEqual(json.loads(
                    (out/"PINNED_ORIGINAL_SOURCE_RESEARCH_UNAPPROVED.json").read_text()),
                    result)
                self.assertEqual(len(list(out.glob("*SOURCE.tar"))),1)
                self.assertEqual((out/binary.name).read_bytes(),binary.read_bytes())

    def test_missing_or_unpinned_source_refuses_evidence_output(self):
        source, binary, revision = self._fixture()
        with patch.dict(os.environ, {"AP_RELEASE_BUILD": "0",
                                     "AP_V30_APPROVED_RELEASE": "0"}):
            with self.assertRaises(ValueError):
                capture(source,binary,"fceumm","linux-x64","0"*40,self.root/"bad")
        self.assertFalse((self.root/"bad").exists())

    def test_fake_approved_production_environment_refused(self):
        source, binary, revision = self._fixture()
        for key in ("AP_RELEASE_BUILD", "AP_V30_APPROVED_RELEASE"):
            with patch.dict(os.environ, {"AP_RELEASE_BUILD": "0",
                                         "AP_V30_APPROVED_RELEASE": "0",
                                         key: "1"}):
                with self.assertRaises(ValueError):
                    capture(source,binary,"fceumm","linux-x64",revision,self.root/"blocked")
        self.assertFalse((self.root/"blocked").exists())

    def test_source_license_and_native_tamper_refused_without_output(self):
        source, binary, revision = self._fixture()
        (source/"Copying").unlink()
        with patch.dict(os.environ, {"AP_RELEASE_BUILD": "0",
                                     "AP_V30_APPROVED_RELEASE": "0"}):
            with self.assertRaises(ValueError):
                capture(source,binary,"fceumm","linux-x64",revision,self.root/"notice")
        self.assertFalse((self.root/"notice").exists())
        (source/"Copying").write_text("Wrong version",encoding="utf-8")
        with patch.dict(os.environ, {"AP_RELEASE_BUILD": "0",
                                     "AP_V30_APPROVED_RELEASE": "0"}):
            with self.assertRaises(ValueError):
                capture(source,binary,"fceumm","linux-x64",revision,self.root/"wrong")
        self.assertFalse((self.root/"wrong").exists())

    def test_wrong_core_binary_name_or_magic_refused(self):
        source, binary, revision = self._fixture()
        binary.write_bytes(b"not-a-shared-library"*3000)
        with patch.dict(os.environ, {"AP_RELEASE_BUILD": "0",
                                     "AP_V30_APPROVED_RELEASE": "0"}):
            with self.assertRaises(ValueError):
                capture(source,binary,"fceumm","linux-x64",revision,self.root/"wrong-magic")
        self.assertFalse((self.root/"wrong-magic").exists())

    def test_actions_covers_5_cores_on_4_real_os_and_no_upstream_submission(self):
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/v30-five-remaining-source-cores.yml").read_text("utf-8")
        for name in CANDIDATES:
            self.assertIn("candidate: "+name, workflow)
        for system in ("linux-x64","windows-x64","macos-arm64","macos-x64"):
            self.assertIn("target: "+system, workflow)
        self.assertEqual(workflow.count("runner: "),20)
        self.assertIn("persist-credentials: false",workflow)
        self.assertNotIn("gh release create",workflow)
        self.assertNotIn("gh issue create",workflow)
        self.assertNotIn("git push",workflow)
        self.assertIn("AP_RELEASE_BUILD: '0'", workflow)
        self.assertIn("AP_V30_APPROVED_RELEASE: '0'", workflow)


if __name__ == "__main__":
    unittest.main()
