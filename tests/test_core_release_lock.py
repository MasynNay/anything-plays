"""Offline tests for exact binary release-core lock verification."""

import copy
import hashlib
import unittest

from tools.core_release_lock import (
    candidate_fingerprint,
    release_target,
    verify_release_lock,
)

SOURCE_COMMITS = {
    "mgba": "7a12d6d4b9acb14c0ae62c9166b6a2f3d08007f6",
    "snes9x": "fae2fea08f74180759ef540ee94259213f503480",
}


class ReleaseCoreLockTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "build_platform": "linux",
            "build_architecture": "x86_64",
            "cores": [],
        }
        for name, revision in (("mgba", "7a12d6d"), ("snes9x", "fae2fea")):
            content = f"fixture-{name}".encode()
            self.manifest["cores"].append({
                "name": name,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size_bytes": len(content),
                "file": f"{name}_libretro.so",
                "source_url": f"https://example.invalid/{name}_libretro.so.zip",
                "libretro_library_version": f"fixture {revision}",
                "reported_source_revision": revision,
                "source_repository_url": f"https://github.com/libretro/{name}",
            })
        candidate = candidate_fingerprint(self.manifest)
        self.lock = {
            "schema_version": 1,
            "approved_for_binary_distribution": True,
            "targets": {
                candidate["target"]: {
                    name: {
                        **record,
                        "source_commit_sha": SOURCE_COMMITS[name],
                    }
                    for name, record in candidate["cores"].items()
                },
            },
        }

    def test_supported_release_architectures(self):
        self.assertEqual(release_target("win32", "AMD64"), "windows-x86_64")
        self.assertEqual(release_target("darwin", "arm64"), "macos-arm64")
        self.assertEqual(release_target("darwin", "x86_64"), "macos-x86_64")
        self.assertEqual(release_target("linux", "x86_64"), "linux-x86_64")
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            release_target("linux", "armv7l")

    def test_candidate_identifies_both_cores(self):
        candidate = candidate_fingerprint(self.manifest)
        self.assertEqual(candidate["target"], "linux-x86_64")
        self.assertEqual(set(candidate["cores"]), {"mgba", "snes9x"})

    def test_matching_approved_fingerprints_succeed(self):
        self.assertEqual(
            verify_release_lock(self.manifest, self.lock), "linux-x86_64"
        )

    def test_unapproved_lock_fails(self):
        lock = copy.deepcopy(self.lock)
        lock["approved_for_binary_distribution"] = False
        with self.assertRaisesRegex(ValueError, "not approved"):
            verify_release_lock(self.manifest, lock)

    def test_missing_target_fails(self):
        lock = copy.deepcopy(self.lock)
        lock["targets"] = {}
        with self.assertRaisesRegex(ValueError, "No approved"):
            verify_release_lock(self.manifest, lock)

    def test_changed_binary_hash_fails(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["cores"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "sha256"):
            verify_release_lock(manifest, self.lock)

    def test_changed_binary_version_fails(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["cores"][1]["libretro_library_version"] = "new upstream nightly"
        with self.assertRaisesRegex(ValueError, "libretro_library_version"):
            verify_release_lock(manifest, self.lock)

    def test_source_revision_mismatch_fails(self):
        lock = copy.deepcopy(self.lock)
        lock["targets"]["linux-x86_64"]["mgba"]["source_commit_sha"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "Source revision mismatch"):
            verify_release_lock(self.manifest, lock)

    def test_missing_corresponding_commit_fails(self):
        lock = copy.deepcopy(self.lock)
        lock["targets"]["linux-x86_64"]["mgba"].pop("source_commit_sha")
        with self.assertRaisesRegex(ValueError, "Full corresponding source commit"):
            verify_release_lock(self.manifest, lock)

    def test_duplicate_core_fails(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["cores"][1]["name"] = "mgba"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            candidate_fingerprint(manifest)


if __name__ == "__main__":
    unittest.main()
