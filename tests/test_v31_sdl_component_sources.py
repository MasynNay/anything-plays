"""SDL source-tag pinning contract; never assert full binary source match."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest

from tools.verify_v31_sdl_component_sources import (
    COMPONENTS, verify_archive, build_manifest,
)


def write_fixture(path, root, unsafe=False):
    with tarfile.open(path, "w:gz") as tar:
        for index in range(30):
            name = f"{root}/src/source_{index:02d}.c"
            if unsafe and index == 2:
                name = f"{root}/../../malicious.c"
            payload = os.urandom(1800)
            entry = tarfile.TarInfo(name)
            entry.size = len(payload)
            tar.addfile(entry, io.BytesIO(payload))


class SDLComponentSourcesTests(unittest.TestCase):
    def test_pins_real_official_git_commits_and_both_sdl2_variants(self):
        self.assertEqual(set(COMPONENTS), {
            "sdl2-2.32.8", "sdl2-2.32.10",
            "sdl2-image-2.8.12", "sdl2-mixer-2.8.2",
            "sdl2-ttf-2.24.0",
        })
        self.assertEqual(COMPONENTS["sdl2-2.32.8"]["commit"],
                         "98d1f3a45aae568ccd6ed5fec179330f47d4d356")
        for name, data in COMPONENTS.items():
            with self.subTest(name=name):
                self.assertRegex(data["commit"], r"^[a-f0-9]{40}$")
                self.assertTrue(data["repository"].startswith("libsdl-org/"))
                self.assertTrue(data["tag"].startswith("release-"))

    def test_detect_tampered_or_malicious_source_archives(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            good = root / "sdl2-2.32.8.tar.gz"
            write_fixture(good, "sdl2-2.32.8")
            report = verify_archive("sdl2-2.32.8", good)
            self.assertEqual(report["archive"], good.name)
            self.assertEqual(report["compiled_source_header_files"], 30)
            write_fixture(good, "sdl2-2.32.8", unsafe=True)
            with self.assertRaises(ValueError):
                verify_archive("sdl2-2.32.8", good)
            write_fixture(good, "something-else")
            with self.assertRaises(ValueError):
                verify_archive("sdl2-2.32.8", good)
            with self.assertRaises(ValueError):
                verify_archive("unknown-version", good)

    def test_manifest_preserves_no_approval_and_every_hash(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            source = root / "source"
            source.mkdir()
            for name in COMPONENTS:
                write_fixture(source / (name + ".tar.gz"), name)
            report = build_manifest(source, root / "report")
            self.assertEqual(len(report["components"]), 5)
            self.assertFalse(report["redistribution_approved"])
            self.assertFalse(report["lgpl_relinking_reviewed"])
            self.assertFalse(report["original_binary_source_correspondence_verified"])
            self.assertFalse(report["complete_transitive_source_verified"])
            for row in report["components"]:
                self.assertFalse(row["exact_binary_to_source_correspondence_verified"])
            self.assertEqual(
                len((root / "report/SDL_SOURCE_SHA256SUMS.txt").read_text().splitlines()),
                5,
            )

    def test_workflow_is_readonly_and_pins_source_tags(self):
        c = (Path(__file__).resolve().parents[1] /
             ".github/workflows/v31-sdl2-upstream-source-candidates.yml").read_text()
        self.assertIn("98d1f3a45aae568ccd6ed5fec179330f47d4d356", c)
        self.assertIn("5d249570393f7a37e037abf22cd6012a4cc56a71", c)
        self.assertIn("actions/upload-artifact@v4", c)
        self.assertNotIn("contents: write", c)
        self.assertNotIn("gh release create", c)


if __name__ == "__main__":
    unittest.main()
