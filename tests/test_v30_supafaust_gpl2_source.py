"""Supafaust GPLv2-or-later source-build identity and rights regression tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import capture_v30_supafaust_source as s


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


class SupafaustSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.upstream = self.root / "upstream"
        self.upstream.mkdir()
        git(self.upstream, "init", "-q")
        git(self.upstream, "config", "user.email", "qa@example.invalid")
        git(self.upstream, "config", "user.name", "Original source test")
        git(self.upstream, "remote", "add", "origin", s.REPOSITORY)
        (self.upstream / "mednafen/snes_faust").mkdir(parents=True)
        (self.upstream / "COPYING").write_text(
            "GNU GENERAL PUBLIC LICENSE\nVersion 2\n", "utf-8")
        (self.upstream / "mednafen/snes_faust/snes.cpp").write_text(
            "This program is available under either version 2 or (at your option) "
            "any later version of the GNU GPL.\n", "utf-8")
        (self.upstream / "Makefile").write_text("all:\n\t@echo research-only\n", "utf-8")
        git(self.upstream, "add", ".")
        git(self.upstream, "commit", "-qm", "A synthetic pinned research source tree")
        self.revision = git(self.upstream, "rev-parse", "HEAD")
        self.native = self.upstream / s.BINARY
        self.native_bytes = b"\x7fELF" + b"original-source-test-bytes" * 2500
        self.native.write_bytes(self.native_bytes)

    def capture_fixture(self):
        with patch.object(s, "COMMIT", self.revision):
            return s.capture(source=self.upstream, native=self.native,
                             output=self.root / "evidence")

    def test_original_checked_out_source_and_native_hashes_are_both_captured(self):
        item = self.capture_fixture()
        dest = self.root / "evidence"
        self.assertEqual(item["source_commit"], self.revision)
        self.assertEqual(item["native_sha256"],
                         hashlib.sha256(self.native_bytes).hexdigest())
        self.assertTrue(item["compiled_from_exact_upstream_checkout"])
        for flag in (
            "replaces_current_snes9x_in_app",
            "independently_reproducible_binary_reviewed",
            "source_dependent_licenses_reviewed",
            "complete_combined_core_license_reviewed",
            "real_4_os_hardware_gameplay_approved",
            "public_binary_redistribution_approved",
        ):
            self.assertIs(item[flag], False, flag)
        self.assertEqual({
            p.name for p in dest.iterdir()
        }, {
            s.BINARY, "SUPAFAUST_ORIGINAL_GPL2_LICENSE.txt",
            f"supafaust-{self.revision}-source.tar.gz",
            "SUPAFAUST_SOURCE_BUILD_UNAPPROVED.json",
            "SHA256SUMS.txt",
        })
        for line in (dest / "SHA256SUMS.txt").read_text("ascii").splitlines():
            sha, name = line.split("  ")
            self.assertEqual(hashlib.sha256((dest/name).read_bytes()).hexdigest(),sha)
        with tarfile.open(dest / item["source_archive"], "r:gz") as archive:
            names = archive.getnames()
            self.assertIn("COPYING", names)
            self.assertIn("mednafen/snes_faust/snes.cpp", names)
            self.assertNotIn(s.BINARY, names)

    def test_original_gpl_or_later_grant_must_be_in_source_not_just_label(self):
        path = self.upstream / "mednafen/snes_faust/snes.cpp"
        path.write_text("We don't grant any later version.", encoding="utf-8")
        git(self.upstream, "add", ".")
        git(self.upstream, "commit", "-qm", "Changed source license permission")
        with self.assertRaisesRegex(ValueError, "exactly pinned"):
            self.capture_fixture()
        path.write_text("either version 2 or any later version", encoding="utf-8")
        with patch.object(s, "COMMIT", git(self.upstream, "rev-parse", "HEAD")):
            with self.assertRaisesRegex(ValueError, "Tracked upstream"):
                s.capture(source=self.upstream, native=self.native,
                          output=self.root/"evidence")

    def test_wrong_binary_architecture_filename_and_existing_evidence_fail(self):
        with patch.object(s, "COMMIT", self.revision):
            self.native.write_bytes(b"MZ" + b"x" * 60000)
            with self.assertRaisesRegex(ValueError, "Linux ELF"):
                s.capture(source=self.upstream, native=self.native,
                          output=self.root/"evidence")
            self.native.write_bytes(self.native_bytes)
            self.capture_fixture()
            with self.assertRaisesRegex(ValueError, "empty"):
                s.capture(source=self.upstream, native=self.native,
                          output=self.root/"evidence")
            wrong = self.upstream / "other_native.so"
            wrong.write_bytes(self.native_bytes)
            with self.assertRaisesRegex(ValueError, "name or size"):
                s.capture(source=self.upstream, native=wrong,
                          output=self.root/"separate")
            with self.assertRaisesRegex(ValueError, "distinct"):
                s.capture(source=self.upstream, native=self.native,
                          output=self.upstream/"new-evidence-inside-source")

    def test_research_ci_pins_real_source_and_runs_original_snes_audio_video(self):
        root=Path(__file__).resolve().parents[1]
        workflow=(root/"docs/history/workflows/v30-supafaust-gpl2-source.yml").read_text("utf-8")
        self.assertIn("pull_request:", workflow)
        self.assertIn("repository: libretro/supafaust", workflow)
        self.assertIn(s.COMMIT, workflow)
        self.assertIn("make -C research/supafaust-src", workflow)
        self.assertIn("probe_snes_homebrew.py", workflow)
        self.assertIn("capture_v30_supafaust_source", workflow)
        self.assertIn("native_nonzero_pcm_values", workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("APPROVED-IMMUTABLE-PRODUCTION", workflow)
        from anything_plays.systems import SYSTEMS
        self.assertEqual(SYSTEMS["snes"].core,"snes9x")
        self.assertEqual(len(SYSTEMS),18)


if __name__ == "__main__":
    unittest.main()
