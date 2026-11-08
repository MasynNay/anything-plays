"""Production 3.0 core gate refuses test-only, altered and incomplete ZIPs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.v30_release_lock import (
    CORE_NAMES, LOCK_PATH, TARGETS, load_approved_lock,
    verify_core_archive, verify_core_payload, verify_dolphin_archive,
    verify_native_bundle,
)
from fetch_mgba_core import CORE_NAMES as V2_CORE_NAMES, core_names_for_build


def sha(data):
    return hashlib.sha256(data).hexdigest()


def eligible_synthetic_lock():
    """In-memory test fixture: NEVER commit this mock approval to config/."""
    targets = {}
    for target in TARGETS:
        ext = (".dll" if target.startswith("windows") else
               ".so" if target.startswith("linux") else ".dylib")
        cores = {}
        for name in CORE_NAMES:
            cores[name] = {
                "file": name + "_libretro" + ext,
                "native_sha256": sha((name + "-payload").encode()),
                "native_size_bytes": len((name + "-payload").encode()),
                "original_archive_sha256": sha((name + "-archive").encode()),
                "original_archive_size_bytes": len((name + "-archive").encode()),
                "redistribution_approved": True,
                "corresponding_source_verified": True,
                "upstream_source_repository": "https://github.com/libretro/" + name,
                "source_commit_sha": "a" * 40,
            }
        targets[target] = {
            "approved_for_distribution": True,
            "cores": cores,
            "dolphin_sys": {
                "original_archive_sha256": sha(b"dolphin-sys"),
                "original_archive_size_bytes": len(b"dolphin-sys"),
                "redistribution_approved": True,
                "source_correspondence_verified": True,
            },
        }
    return {
        "schema_version": 1,
        "approved_for_binary_distribution": True,
        "license_compatibility_reviewed": True,
        "corresponding_source_inventory_verified": True,
        "native_core_count": 11,
        "system_profile_count": 18,
        "targets": targets,
    }


class V30ProductionCoreLockTests(unittest.TestCase):
    def test_approved_3_0_is_treated_as_full_offline_bundle_on_all_platforms(self):
        root = Path(__file__).resolve().parents[1]
        for path in (
            "packaging/build_linux_deb.sh",
            "packaging/build_macos_dmg.sh",
            "packaging/build_windows.bat",
        ):
            with self.subTest(platform=path):
                source = (root / path).read_text(encoding="utf-8")
                self.assertIn("AP_V30_APPROVED_RELEASE", source)
                self.assertIn("dolphin", source)
                self.assertIn("mednafen_wswan", source)
        source = (root / "fetch_mgba_core.py").read_text(encoding="utf-8")
        self.assertIn("verify_core_archive", source)
        self.assertIn("verify_core_payload", source)
        self.assertIn("verify_native_bundle", source)
        dolphin = (root / "tools/fetch_dolphin_sys.py").read_text("utf-8")
        self.assertIn("verify_dolphin_archive", dolphin)

    def test_checked_in_release_lock_is_not_approved(self):
        self.assertEqual(V2_CORE_NAMES, ("mgba", "snes9x"))
        self.assertEqual(len(CORE_NAMES), 11)
        with self.assertRaisesRegex(ValueError, "redistribution blocked"):
            load_approved_lock()
        with patch.dict(os.environ, {
            "AP_RELEASE_BUILD": "1", "AP_V30_APPROVED_RELEASE": "1",
        }):
            with self.assertRaisesRegex(ValueError, "redistribution blocked"):
                core_names_for_build()

    def test_synthetic_complete_lock_and_native_hashes(self):
        fixture = eligible_synthetic_lock()
        with TemporaryDirectory() as temp:
            file = Path(temp) / "approved-test-fixture.json"
            file.write_text(json.dumps(fixture), encoding="utf-8")
            loaded = load_approved_lock(file)
        self.assertEqual(len(loaded["targets"]), 4)
        name = "mgba"
        verify_core_archive(loaded, "linux", "x86_64", name, b"mgba-archive")
        verify_core_payload(
            loaded, "linux", "x86_64", name, "mgba_libretro.so",
            b"mgba-payload",
        )
        verify_dolphin_archive(loaded, "linux", "x86_64", b"dolphin-sys")
        with self.assertRaisesRegex(ValueError, "native core changed"):
            verify_core_payload(
                loaded, "linux", "x86_64", name, "mgba_libretro.so",
                b"modified-payload",
            )
        with self.assertRaisesRegex(ValueError, "preserved archive changed"):
            verify_core_archive(loaded, "linux", "x86_64", name, b"new-nightly")
        with self.assertRaisesRegex(ValueError, "Dolphin Sys archive changed"):
            verify_dolphin_archive(loaded, "linux", "x86_64", b"new-sys")

    def test_no_partial_rights_or_missing_platforms_can_pass(self):
        scenarios = [
            ("license_compatibility_reviewed", False, "redistribution blocked"),
            ("corresponding_source_inventory_verified", False, "redistribution blocked"),
        ]
        with TemporaryDirectory() as temp:
            file = Path(temp) / "lock.json"
            for key, bad, error in scenarios:
                data = eligible_synthetic_lock()
                data[key] = bad
                file.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, error):
                    load_approved_lock(file)
            data = eligible_synthetic_lock()
            data["targets"].pop("macos-x86_64")
            file.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "four architectures"):
                load_approved_lock(file)
            data = eligible_synthetic_lock()
            data["targets"]["linux-x86_64"]["cores"]["mednafen_pce_fast"][
                "corresponding_source_verified"
            ] = False
            file.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "incomplete source/license"):
                load_approved_lock(file)

    def test_bundle_manifest_must_match_all_native_bytes(self):
        lock = eligible_synthetic_lock()
        root = lock["targets"]["linux-x86_64"]
        records = []
        for name, row in root["cores"].items():
            records.append({
                "name": name,
                "file": row["file"],
                "sha256": row["native_sha256"],
                "size_bytes": row["native_size_bytes"],
                "archive_sha256": row["original_archive_sha256"],
                "archive_size_bytes": row["original_archive_size_bytes"],
                "source_repository_url": row["upstream_source_repository"],
            })
        manifest = {
            "build_platform": "linux",
            "build_architecture": "x86_64",
            "cores": records,
            "dolphin_system_assets": {
                "archive_sha256": root["dolphin_sys"]["original_archive_sha256"],
                "archive_size_bytes": root["dolphin_sys"]["original_archive_size_bytes"],
            },
        }
        self.assertEqual(verify_native_bundle(lock, manifest), "linux-x86_64")
        records[0]["archive_sha256"] = sha(b"wrong")
        with self.assertRaisesRegex(ValueError, "bundle core mismatch"):
            verify_native_bundle(lock, manifest)


if __name__ == "__main__":
    unittest.main()
