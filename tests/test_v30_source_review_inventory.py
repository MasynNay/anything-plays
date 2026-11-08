"""Review inventory is complete by identity but NEVER authorizes binary release."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from tools.create_v30_source_review_inventory import (
    SOURCE_MANIFEST, capture_index, make_inventory,
)
from tools.v30_release_lock import CORE_NAMES, TARGETS


REV = "a" * 40


def h(data):
    return hashlib.sha256(data).hexdigest()


def sample():
    snapshots = {}
    for name in CORE_NAMES:
        sha = None if name == "mednafen_pce_fast" else REV
        data = (name + ": pinned original source").encode("utf-8")
        snapshots[name] = {
            "repository": "https://github.com/libretro/" + name,
            "reported_commit": sha,
            "sha256": h(data) if sha else None,
            "size_bytes": len(data) if sha else None,
            "status": (
                "NO_REPORTED_SOURCE_REVISION" if sha is None
                else "REPORTED-COMMIT-SNAPSHOT-CAPTURED-NOT-APPROVED"
            ),
            "redistribution_reviewed": False,
            "source_to_binary_independently_verified": False,
        }
    targets = {}
    for target in TARGETS:
        targets[target] = {
            "approved_for_distribution": False,
            "cores": {},
            "dolphin_sys": {
                "original_archive_sha256": h(("Dolphin Sys" + target).encode()),
                "original_archive_size_bytes": 1024,
                "source_correspondence_verified": False,
            },
        }
        for name in CORE_NAMES:
            targets[target]["cores"][name] = {
                "native_sha256": h((name + target).encode()),
                "original_archive_sha256": h((name + target + ".zip").encode()),
                "upstream_source_repository": snapshots[name]["repository"],
                "upstream_reported_revision": None if name == "mednafen_pce_fast" else REV[:7],
                "redistribution_approved": False,
                "corresponding_source_verified": False,
            }
    lock = {
        "schema_version": 1,
        "status": "UNAPPROVED-FOUR-PLATFORM-3.0-CANDIDATE",
        "approved_for_binary_distribution": False,
        "native_core_count": 11,
        "system_profile_count": 18,
        "source_commit": REV,
        "targets": targets,
    }
    return lock, snapshots


class SourceReviewCandidateTests(unittest.TestCase):
    def test_generated_inventory_has_44_native_identities_but_zero_approvals(self):
        lock, snapshots = sample()
        data = make_inventory(lock, snapshots)
        self.assertEqual(len(data["targets"]), 4)
        self.assertEqual(sum(len(row["cores"]) for row in data["targets"].values()), 44)
        self.assertEqual(data["source_snapshots_captured"], 10)
        self.assertEqual(data["source_snapshots_missing"], ["mednafen_pce_fast"])
        self.assertFalse(data["approved_for_public_binary_distribution"])
        self.assertFalse(data["corresponding_source_inventory_verified"])
        for row in data["targets"].values():
            self.assertFalse(row["dolphin_sys"]["source_and_license_reviewed"])
            for core in row["cores"].values():
                self.assertFalse(core["source_build_dependencies_reviewed"])
                self.assertFalse(core["redistribution_license_reviewed"])

    def test_unknown_pce_revision_and_changed_cross_platform_binary_are_rejected(self):
        lock, snap = sample()
        lock["targets"]["macos-arm64"]["cores"]["mgba"]["upstream_reported_revision"] = "bad1234"
        with self.assertRaisesRegex(ValueError, "doesn't match archived source"):
            make_inventory(lock, snap)
        lock, snap = sample()
        lock["targets"]["windows-x86_64"]["cores"]["mednafen_pce_fast"]["upstream_reported_revision"] = "deadbee"
        with self.assertRaisesRegex(ValueError, "unknown core revision"):
            make_inventory(lock, snap)
        lock, snap = sample()
        lock["targets"].pop("linux-x86_64")
        with self.assertRaisesRegex(ValueError, "four platform"):
            make_inventory(lock, snap)

    def test_original_source_archive_checksums_cannot_be_faked(self):
        lock, rows = sample()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            filename = root / "upstream-sources.zip"
            manifest = {
                "schema_version": 1,
                "approved_for_binary_distribution": False,
                "independent_binary_to_source_match_proven": False,
                "cores": rows,
            }
            with ZipFile(filename, "w", ZIP_DEFLATED) as archive:
                for name in sorted(CORE_NAMES):
                    if name == "mednafen_pce_fast":
                        continue
                    content = (name + ": pinned original source").encode("utf-8")
                    archive.writestr(f"source-{name}-{REV}.tar.gz", content)
                    rows[name]["archive_file"] = f"source-{name}-{REV}.tar.gz"
                archive.writestr(SOURCE_MANIFEST, json.dumps(manifest))
            self.assertEqual(len(capture_index(filename)), 11)
            with ZipFile(filename, "a") as archive:
                archive.writestr("unapproved-extra.tar.gz", b"unreviewed")
            with self.assertRaisesRegex(ValueError, "Unexpected/missing"):
                capture_index(filename)

    def test_real_cli_does_not_accept_early_binary_distribution(self):
        root = Path(__file__).resolve().parents[1]
        cmd = [sys.executable, "-m", "tools.create_v30_source_review_inventory", "--help"]
        out = subprocess.run(cmd, cwd=root, text=True, capture_output=True, timeout=15)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("--native-candidate", out.stdout)
        self.assertIn("--source-snapshots", out.stdout)
        self.assertIn("--output", out.stdout)


if __name__ == "__main__":
    unittest.main()
