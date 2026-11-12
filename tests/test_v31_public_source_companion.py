"""Adversarial source-archive and third-party-rights tests for 3.1."""
from __future__ import annotations

import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import tarfile
import unittest
from unittest.mock import patch

from tools import stage_v31_public_source_companion as src


def tar_bytes(members, mode="w:gz"):
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode=mode) as t:
        for name, data in members.items():
            payload = data.encode()
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            t.addfile(member, io.BytesIO(payload))
    return result.getvalue()


class SourceCompanionTests(unittest.TestCase):
    def fixture(self, folder):
        root = Path(folder)
        incoming = root / "incoming"
        incoming.mkdir()
        pygame = tar_bytes({
            "pygame-ce-2.5.8/docs/LGPL.txt": "LGPL",
            "pygame-ce-2.5.8/docs/licenses/LICENSE.mpg123.txt": "mpg123 LGPL",
            "pygame-ce-2.5.8/src_c/base.c": "C source",
        })
        mpg = tar_bytes({
            "mpg123-1.33.7/COPYING": "LGPL",
            "mpg123-1.33.7/src/libmpg123/frame.c": "C source",
        }, "w:bz2")
        hashes = {}
        for relative in src.SOURCE_ARCHIVES:
            path = (root / "mpg123-1.33.7.tar.bz2" if relative.endswith(".bz2")
                    else incoming / relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = mpg if relative.endswith(".bz2") else (
                pygame if relative.startswith("pygame-ce-") else b"original SDL source archive" * 200
            )
            path.write_bytes(payload)
            hashes[relative] = src.sha(path)
        for name in src.EVIDENCE:
            path = incoming / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({
                    "status": "UNRELEASED_3_1_SDL_OBSERVED_VERSION_SOURCE_CANDIDATES",
                    "original_binary_source_correspondence_verified": False,
                    "redistribution_approved": False,
                }) if name.endswith("SDL_CANDIDATE_SOURCE_MANIFEST.json")
                else "original license/manifest",
                "utf-8",
            )
        return incoming, root / "mpg123-1.33.7.tar.bz2", hashes, root / "out"

    def test_genuine_source_candidates_stage_with_per_file_sha(self):
        with TemporaryDirectory() as tmp:
            folder, mpg, hashes, dest = self.fixture(tmp)
            with patch.object(src, "SOURCE_ARCHIVES", hashes):
                manifest = src.stage(folder, mpg, dest)
            self.assertEqual(manifest["exact_application_source_revision"], src.APP_SOURCE)
            self.assertFalse(manifest["public_release_approved"])
            self.assertFalse(manifest["complete_lgpl_redistribution_approved"])
            self.assertEqual(len(manifest["source_archives"]), 7)
            self.assertEqual(len(list((dest / "original-sources").iterdir())), 7)
            self.assertIn("mpg123-1.33.7.tar.bz2", manifest["source_archives"])
            for line in (dest / "SHA256SUMS.txt").read_text().splitlines():
                digest, name = line.split("  ", 1)
                self.assertEqual(src.sha(dest / name), digest)

    def test_reject_mutated_source_or_missing_lgpl_notices(self):
        with TemporaryDirectory() as tmp:
            folder, mpg, hashes, dest = self.fixture(tmp)
            with patch.object(src, "SOURCE_ARCHIVES", hashes):
                mpg.write_bytes(mpg.read_bytes() + b"tampered")
                with self.assertRaisesRegex(ValueError, "SHA"):
                    src.stage(folder, mpg, dest)
                self.assertFalse(dest.exists())
                mpg.write_bytes(tar_bytes({
                    "mpg123-1.33.7/COPYING": "LGPL",
                    "mpg123-1.33.7/src/libmpg123/frame.c": "C source",
                }, "w:bz2"))
                entry = folder / src.EVIDENCE[1]
                entry.unlink()
                with self.assertRaises(ValueError):
                    src.stage(folder, mpg, dest)
                self.assertFalse(dest.exists())

    def test_reject_forged_binary_source_provenance_and_approval(self):
        with TemporaryDirectory() as tmp:
            folder, mpg, hashes, dest = self.fixture(tmp)
            manifest_path = folder / src.EVIDENCE[0]
            for key, val in (
                ("status", "PUBLIC_APPROVED"),
                ("original_binary_source_correspondence_verified", True),
                ("redistribution_approved", True),
            ):
                with self.subTest(key=key), patch.object(src, "SOURCE_ARCHIVES", hashes):
                    info = json.loads(manifest_path.read_text())
                    info[key] = val
                    manifest_path.write_text(json.dumps(info), "utf-8")
                    with self.assertRaises(ValueError):
                        src.stage(folder, mpg, dest)
                    info[key] = {
                        "status": "UNRELEASED_3_1_SDL_OBSERVED_VERSION_SOURCE_CANDIDATES",
                        "original_binary_source_correspondence_verified": False,
                        "redistribution_approved": False,
                    }[key]
                    manifest_path.write_text(json.dumps(info), "utf-8")
                self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
