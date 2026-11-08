"""Pinned GPLv2 PCE source-to-new-binary record does not clear mixed-core rights."""
from __future__ import annotations

import gzip
import hashlib
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.capture_v30_pce_source_build import (
    PINNED_COMMIT, PINNED_REPOSITORY, PLATFORM_FILES, capture_pinned_build,
)


def tar_with_license():
    with BytesIO() as buffer:
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            data = b"GNU GENERAL PUBLIC LICENSE\nVersion 2, June 1991\n"
            header = tarfile.TarInfo("COPYING")
            header.size = len(data)
            tar.addfile(header, BytesIO(data))
        return buffer.getvalue()


def fake_git(source, *args, raw=False):
    if args == ("rev-parse", "HEAD"):
        return PINNED_COMMIT
    if args == ("remote", "get-url", "origin"):
        return PINNED_REPOSITORY + ".git"
    if args == ("status", "--porcelain", "--untracked-files=no"):
        return ""
    if args == ("archive", "--format=tar", "HEAD"):
        return tar_with_license()
    raise AssertionError(f"Unexpected git operation {args}")


class PCEOriginalSourceLabTests(unittest.TestCase):
    def test_exact_source_capture_with_independent_unapproved_binary_hash(self):
        with TemporaryDirectory() as rootname:
            base = Path(rootname)
            root = base / "pinned-source"
            root.mkdir()
            (root/"COPYING").write_text("GNU GENERAL PUBLIC LICENSE\nVersion 2, June 1991\n")
            binary = root / PLATFORM_FILES["linux-x64"]
            binary.write_bytes(b"ORIGINAL SOURCE BUILT TEST " * 6000)
            with patch("tools.capture_v30_pce_source_build._git", side_effect=fake_git):
                data = capture_pinned_build(root, binary, base/"out", target="linux-x64")
            self.assertEqual(data["source_commit"], PINNED_COMMIT)
            self.assertEqual(data["native_core_sha256"], hashlib.sha256(binary.read_bytes()).hexdigest())
            self.assertEqual(data["target"], "linux-x64")
            self.assertFalse(data["third_party_distribution_approved"])
            self.assertFalse(data["mixed_core_licenses_reviewed"])
            self.assertFalse(data["current_3_0_core_replaced"])
            self.assertFalse(data["gameplay_native_video_audio_verified"])
            output = base/"out"
            self.assertEqual(len(list(output.iterdir())), 4)
            archive = output / data["source_archive"]
            self.assertEqual(data["source_archive_sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
            with tarfile.open(fileobj=BytesIO(gzip.decompress(archive.read_bytes())), mode="r:") as tar:
                self.assertIn("COPYING", tar.getnames())
            self.assertEqual(json.loads((output/"PCE_SOURCE_BUILD_UNAPPROVED.json").read_text()), data)

    def test_wrong_commit_or_modified_license_blocks_capture_before_output(self):
        with TemporaryDirectory() as rootname:
            base = Path(rootname)
            root = base/"pce"
            root.mkdir()
            (root/"COPYING").write_text("GNU GENERAL PUBLIC LICENSE\nVersion 2\n")
            binary = root/"mednafen_pce_fast_libretro.so"
            binary.write_bytes(b"A"*90000)
            def wrong_git(source, *args, raw=False):
                return "b"*40 if args == ("rev-parse", "HEAD") else fake_git(source, *args, raw=raw)
            with patch("tools.capture_v30_pce_source_build._git", side_effect=wrong_git):
                with self.assertRaisesRegex(ValueError, "exact approved research commit"):
                    capture_pinned_build(root, binary, base/"output", target="linux-x64")
            self.assertFalse((base/"output").exists())
            with self.assertRaisesRegex(ValueError, "Unknown PC Engine native target"):
                capture_pinned_build(root, binary, base/"bad", target="gamecube")
            (root/"COPYING").write_text("NOT AN APPROVED LICENSE TEXT")
            with patch("tools.capture_v30_pce_source_build._git", side_effect=fake_git):
                with self.assertRaisesRegex(ValueError, "GPLv2"):
                    capture_pinned_build(root, binary, base/"out2", target="linux-x64")

    def test_all_four_target_names_are_native_and_explicit(self):
        self.assertEqual(set(PLATFORM_FILES), {
            "windows-x64", "linux-x64", "macos-arm64", "macos-x64",
        })
        self.assertEqual(len(PINNED_COMMIT), 40)
        self.assertEqual(len(set(PLATFORM_FILES.values())), 3)

    def test_workflow_never_publishes_binaries_and_requires_real_original_psg(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root/".github/workflows/v30-pce-pinned-source.yml").read_text("utf-8")
        self.assertIn(PINNED_COMMIT, workflow)
        self.assertIn("repository: libretro/beetle-pce-fast-libretro", workflow)
        self.assertIn("msys2/setup-msys2@v2", workflow)
        for target in PLATFORM_FILES:
            self.assertIn("target: " + target, workflow)
        self.assertIn('EXTRA_INCLUDES="-include stdio.h"', workflow)
        self.assertIn('platform=osx', workflow)
        self.assertIn("probe_pce_homebrew.py", workflow)
        self.assertIn("native_nonzero_pcm_samples", workflow)
        self.assertIn("gameplay_native_video_audio_verified", workflow)
        self.assertIn("UNAPPROVED", workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("gh release upload", workflow)
        self.assertNotIn("AP_V30_APPROVED_RELEASE: '1'", workflow)

    def test_capture_cli_can_run_without_upstream_network(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-m", "tools.capture_v30_pce_source_build", "--help"],
            cwd=root, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--source", result.stdout)
        self.assertIn("--native-core", result.stdout)


if __name__ == "__main__":
    unittest.main()
