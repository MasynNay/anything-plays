"""GPL replacement candidates require source-built native and full notices."""
from __future__ import annotations
import hashlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import tarfile
import unittest
from unittest.mock import patch

from tools.capture_v30_gpl_alternative_source_build import (
    EXT, MAGIC, SOURCE, capture_source_built_candidate,
)


class PinnedGPLSourceBuildContracts(unittest.TestCase):
    def test_two_immutable_gpl_sources_cover_all_five_profiles(self):
        self.assertEqual(set(SOURCE),{"bsnes","blastem"})
        self.assertEqual(set(EXT),{"windows-x64","linux-x64","macos-arm64","macos-x64"})
        self.assertEqual(SOURCE["bsnes"]["commit"],
                         "63ee22f7af8f5d1ada295c2c98fd7bf261fa62a7")
        self.assertEqual(SOURCE["blastem"]["commit"],
                         "2230addc4dd74dd094fd264987fd808abba32d0e")

    def test_real_git_checked_in_source_is_archived_and_binary_sha_bound(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            upstream=root/"upstream"
            upstream.mkdir()
            subprocess.run(["git","init","-q"],cwd=upstream,check=True)
            subprocess.run(["git","config","user.email","qa@example.invalid"],cwd=upstream,check=True)
            subprocess.run(["git","config","user.name","QA fixture"],cwd=upstream,check=True)
            (upstream/"COPYING").write_text(
                "GNU GENERAL PUBLIC LICENSE\nVersion 3\nTEST ONLY\n","utf-8")
            (upstream/"Makefile.libretro").write_text("all:\n\t@echo fixture\n","utf-8")
            subprocess.run(["git","add","."],cwd=upstream,check=True)
            subprocess.run(["git","commit","-qm","fixture source"],cwd=upstream,check=True)
            git_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=upstream,
                                            text=True).strip()
            subprocess.run(["git","remote","add","origin",
                            "https://github.com/libretro/blastem"],cwd=upstream,check=True)
            binary=upstream/"blastem_libretro.so"
            body=b"\x7fELF"+b"TEST-ONLY-FAKE-ELF-"*4000
            binary.write_bytes(body)
            with patch.dict(SOURCE["blastem"],{"commit":git_sha}):
                out=root/"evidence"
                record=capture_source_built_candidate(
                    source=upstream,native=binary,output=out,
                    candidate="blastem",target="linux-x64")
            self.assertEqual(record["native_sha256"],hashlib.sha256(body).hexdigest())
            self.assertEqual(record["source_commit"],git_sha)
            self.assertTrue(record["compiled_from_exact_pinned_source_checkout"])
            self.assertFalse(record["combined_gpl_2_and_gpl_3_license_reviewed"])
            self.assertFalse(record["public_binary_distribution_approved"])
            self.assertFalse(record["source_to_binary_independently_reproducible"])
            self.assertEqual({p.name for p in out.iterdir()},{
                "blastem_libretro.so",
                "blastem-GPLv3-NOTICE.txt",
                "PINNED_GPL_ALTERNATIVE_SOURCE_BUILD_UNAPPROVED.json",
                f"blastem-{git_sha}-source.tar.gz",
                "SHA256SUMS.txt",
            })
            for line in (out/"SHA256SUMS.txt").read_text("ascii").splitlines():
                digest,name=line.split("  ")
                self.assertEqual(hashlib.sha256((out/name).read_bytes()).hexdigest(),digest)
            with tarfile.open(out/f"blastem-{git_sha}-source.tar.gz","r:gz") as archive:
                self.assertIn("COPYING",archive.getnames())
                self.assertNotIn("blastem_libretro.so",archive.getnames())

    def test_rejects_wrong_architecture_unknown_core_and_unsafe_output(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            core=root/"bsnes_libretro.so"
            core.write_bytes(b"MZ" + b"x"*50000)
            with self.assertRaisesRegex(ValueError,"Unsupported"):
                capture_source_built_candidate(
                    source=root,native=core,output=root/"out",
                    candidate="bad",target="linux-x64")
            with self.assertRaisesRegex(ValueError,"Unsupported"):
                capture_source_built_candidate(
                    source=root,native=core,output=root/"out",
                    candidate="bsnes",target="linux-arm")
            with self.assertRaisesRegex(ValueError,"Source checkout or actual compiled"):
                capture_source_built_candidate(
                    source=root,native=root/"missing.so",output=root/"out",
                    candidate="bsnes",target="linux-x64")

    def test_linux_source_build_workflow_never_releases_or_fakes_approval(self):
        root=Path(__file__).resolve().parents[1]
        workflow=(root/"docs/history/workflows/v30-gpl-pinned-source-build.yml").read_text("utf-8")
        self.assertIn("pull_request:",workflow)
        self.assertIn("libretro/bsnes",workflow)
        self.assertIn("libretro/blastem",workflow)
        self.assertIn(SOURCE["bsnes"]["commit"],workflow)
        self.assertIn(SOURCE["blastem"]["commit"],workflow)
        self.assertIn("make -C research/bsnes-src",workflow)
        self.assertIn("make -C research/blastem-src",workflow)
        self.assertIn("capture_v30_gpl_alternative_source_build",workflow)
        self.assertIn("probe_snes_homebrew.py",workflow)
        self.assertIn("probe_v30_blastem_genesis_variant.py",workflow)
        self.assertIn("probe_sega8_homebrew.py",workflow)
        self.assertNotIn("gh release create",workflow)
        self.assertNotIn("APPROVED-3.0-DISTRIBUTION",workflow)


if __name__=="__main__":
    unittest.main()
