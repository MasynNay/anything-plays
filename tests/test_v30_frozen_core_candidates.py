"""Candidate release locks prove identities, never rights or source correspondence."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from tools.create_v30_candidate_lock import CORES, PLATFORMS, build_candidate


SOURCE_SHA = "f" * 40


def make_bundle(path, target, *, source_sha=SOURCE_SHA, tamper=False):
    """Make a tiny independent four-platform native archive fixture."""
    ext = PLATFORMS[target][1]
    core_records = []
    zip_records = []
    zip_bytes = {}
    for core in sorted(CORES):
        filename = core + "_libretro" + ext
        payload = (f"{core}/{target}/native".encode("utf-8")) * 100
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w") as inner:
            inner.writestr(filename, payload)
        archive = memory.getvalue()
        name = filename + ".zip"
        zip_records.append({
            "name": name, "sha256": hashlib.sha256(archive).hexdigest(),
            "size_bytes": len(archive),
        })
        core_records.append({
            "name": core,
            "file": filename,
            "archive_sha256": hashlib.sha256(archive).hexdigest(),
            "archive_size_bytes": len(archive),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "reported_source_revision": "1234567",
            "source_repository_url": "https://github.com/libretro/" + core,
            "libretro_library_version": "1.0-1234567",
        })
        zip_bytes[name] = archive
    dolphin = b"test original Dolphin Sys archive"
    zip_records.append({
        "name": "Dolphin.zip", "sha256": hashlib.sha256(dolphin).hexdigest(),
        "size_bytes": len(dolphin),
    })
    zip_bytes["Dolphin.zip"] = dolphin
    if tamper:
        zip_bytes[sorted(CORES)[0] + "_libretro" + ext + ".zip"] += b"altered"
    provenance = {
        "target": target,
        "status": "UNAPPROVED-TEST-INPUTS",
        "public_distribution_approved": False,
        "source_revision": source_sha,
        "original_archive_count": 12,
        "files": zip_records,
        "source_core_provenance": {
            "cores": core_records,
            "dolphin_system_assets": {
                "archive_sha256": hashlib.sha256(dolphin).hexdigest(),
                "archive_size_bytes": len(dolphin),
            },
        },
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as outer:
        for name, value in zip_bytes.items():
            outer.writestr(name, value)
        outer.writestr("PRESERVED_NATIVE_INPUTS.json", json.dumps(provenance))


class FrozenV30CandidateTests(unittest.TestCase):
    def test_four_platform_lock_is_complete_and_unapproved(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {key: root / (key + ".zip") for key in PLATFORMS}
            for target, path in paths.items():
                make_bundle(path, target)
            result = build_candidate(paths)
            self.assertEqual(result["source_commit"], SOURCE_SHA)
            self.assertEqual(len(result["targets"]), 4)
            self.assertEqual(result["native_core_count"], 11)
            self.assertFalse(result["approved_for_binary_distribution"])
            for record in result["targets"].values():
                self.assertEqual(set(record["cores"]), CORES)
                self.assertFalse(record["approved_for_distribution"])
                self.assertTrue(all(
                    not core["redistribution_approved"]
                    and not core["corresponding_source_verified"]
                    for core in record["cores"].values()
                ))

    def test_reject_modified_original_zip_with_recorded_old_hash(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {key: root / (key + ".zip") for key in PLATFORMS}
            for target, path in paths.items():
                make_bundle(path, target, tamper=target == "linux-x64")
            with self.assertRaisesRegex(ValueError, "changed original archive"):
                build_candidate(paths)

    def test_reject_mixed_source_revision_and_missing_platform(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {key: root / (key + ".zip") for key in PLATFORMS}
            for target, path in paths.items():
                make_bundle(path, target, source_sha="a" * 40 if target == "macos-x64" else SOURCE_SHA)
            with self.assertRaisesRegex(ValueError, "share a source commit"):
                build_candidate(paths)
            with self.assertRaisesRegex(ValueError, "exactly four platforms"):
                build_candidate({key: path for key, path in paths.items()
                                 if key != "linux-x64"})


if __name__ == "__main__":
    unittest.main()
