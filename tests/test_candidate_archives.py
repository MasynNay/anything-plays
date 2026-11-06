"""Offline tests for immutable candidate ZIP evidence."""

import hashlib
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from tools.verify_candidate_archives import verify_candidate_archives


class CandidateArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.manifest = {
            "build_platform": "linux", "build_architecture": "x86_64", "cores": []
        }
        self.lock = {"schema_version": 1,
                     "approved_for_binary_distribution": False,
                     "targets": {"linux-x86_64": {}}}
        for name, revision in (("mgba", "7a12d6d"), ("snes9x", "fae2fea")):
            filename = f"{name}_libretro.so"
            payload = b"\x7fELF" + name.encode()
            mem = BytesIO()
            with zipfile.ZipFile(mem, "w") as z:
                z.writestr(filename, payload)
            archive_bytes = mem.getvalue()
            (self.folder / (filename + ".zip")).write_bytes(archive_bytes)
            identity = {
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
                "file": filename,
                "source_url": "https://example.invalid/latest/" + filename + ".zip",
                "libretro_library_version": f"test {revision}",
                "reported_source_revision": revision,
                "source_repository_url": "https://github.com/libretro/" + name,
            }
            self.lock["targets"]["linux-x86_64"][name] = {
                **identity,
                "source_commit_sha": revision + "a" * (40 - len(revision)),
            }
            self.manifest["cores"].append({
                "name": name, **identity,
                "archive_sha256": hashlib.sha256(archive_bytes).hexdigest(),
                "archive_size_bytes": len(archive_bytes),
            })

    def test_two_preserved_core_archives_match(self):
        report = verify_candidate_archives(self.manifest, self.lock, self.folder)
        self.assertEqual(report["target"], "linux-x86_64")
        self.assertEqual(len(report["cores"]), 2)
        self.assertFalse(report["redistribution_approved"])
        self.assertFalse(report["source_binary_correspondence_independently_verified"])

    def test_mismatched_zip_is_rejected(self):
        (self.folder / "mgba_libretro.so.zip").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "Preserved ZIP differs"):
            verify_candidate_archives(self.manifest, self.lock, self.folder)

    def test_mismatched_binary_lock_is_rejected(self):
        self.lock["targets"]["linux-x86_64"]["mgba"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Candidate core mismatch"):
            verify_candidate_archives(self.manifest, self.lock, self.folder)

    def test_missing_archive_is_rejected(self):
        (self.folder / "snes9x_libretro.so.zip").unlink()
        with self.assertRaisesRegex(ValueError, "Missing regular core archive"):
            verify_candidate_archives(self.manifest, self.lock, self.folder)


if __name__ == "__main__":
    unittest.main()
