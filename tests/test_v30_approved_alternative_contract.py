"""Fail-closed test for future source-reviewed GPL alternative 3.0 production.

The checked-in release lock still DENIES shipping. Synthetic approval
fixtures exercise only code paths, never grant actual distribution rights.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fetch_mgba_core import core_names_for_build, V30_GPL_TRIAL_CORES
from tools.emit_v30_production_provenance import validate_source_inventory
from tools.v30_release_lock import (
    ALTERNATIVE_CORE_NAMES, ALTERNATIVE_CORE_ORDER, CORE_NAMES,
    TARGETS, load_approved_lock, native_for_target,
    ordered_core_names_for_lock, selected_core_set, verify_native_bundle,
)


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def synthetic_approved():
    """Generate artificial 44-native source records, not an approval file."""
    lock = {
        "schema_version": 1, "source_commit": "a" * 40,
        "core_set_id": "gpl-source-built-alternative",
        "legacy_noncommercial_native_binaries_excluded": True,
        "source_built_alternative_binary_rights_reviewed": True,
        "approved_for_binary_distribution": True,
        "license_compatibility_reviewed": True,
        "corresponding_source_inventory_verified": True,
        "native_core_count": 11, "system_profile_count": 18,
        "targets": {},
    }
    inventory = {
        "schema_version": 1, "source_commit": lock["source_commit"],
        "native_core_count": 11,
        "approved_for_public_binary_distribution": True,
        "corresponding_source_inventory_verified": True,
        "independent_binary_to_source_match_proven": True,
        "targets": {},
    }
    for target in TARGETS:
        ext = ".dll" if target.startswith("windows") else ".so" if target.startswith("linux") else ".dylib"
        cores, evidence = {}, {}
        for name in ALTERNATIVE_CORE_ORDER:
            digest, archive = sha(name + target), sha(name + target + "zip")
            repo = ("https://github.com/libretro/supafaust" if name == "mednafen_supafaust"
                    else "https://github.com/libretro/blastem" if name == "blastem"
                    else f"https://github.com/libretro/{name}")
            cores[name] = {
                "file": f"{name}_libretro{ext}",
                "native_sha256": digest, "native_size_bytes": 100000,
                "original_archive_sha256": archive, "original_archive_size_bytes": 110000,
                "source_commit_sha": "b" * 40, "upstream_source_repository": repo,
                "redistribution_approved": True, "corresponding_source_verified": True,
            }
            evidence[name] = {
                "source_commit_sha": "b" * 40, "native_sha256": digest,
                "original_native_archive_sha256": archive, "source_repository": repo,
                "source_archive_sha256": sha(name + target + "source"),
                "source_archive_size_bytes": 15000,
                "source_build_dependencies_reviewed": True,
                "source_to_binary_verified": True,
                "redistribution_license_reviewed": True,
            }
        sys = {
            "original_archive_sha256": sha("Sys" + target),
            "original_archive_size_bytes": 5432,
            "source_correspondence_verified": True, "redistribution_approved": True,
        }
        lock["targets"][target] = {
            "approved_for_distribution": True, "cores": cores, "dolphin_sys": sys,
        }
        inventory["targets"][target] = {
            "cores": evidence, "dolphin_sys": {**sys, "source_and_license_reviewed": True},
        }
    return lock, inventory


class ApprovedAlternativeContract(unittest.TestCase):
    def test_current_real_release_unapproved(self):
        with self.assertRaises(ValueError):
            load_approved_lock()
        record = json.loads((Path(__file__).resolve().parents[1]
                             / "config/v3.0-core-lock.json").read_text())
        self.assertFalse(record["approved_for_binary_distribution"])

    def test_exact_11_alternative_core_ids_and_source_review(self):
        lock, source = synthetic_approved()
        self.assertEqual(V30_GPL_TRIAL_CORES, ALTERNATIVE_CORE_ORDER)
        self.assertEqual(selected_core_set(lock), ALTERNATIVE_CORE_NAMES)
        self.assertTrue(validate_source_inventory(lock, source))
        self.assertEqual(len(CORE_NAMES), 11)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "ONLY_SYNTHETIC_NOT_APPROVAL.json"
            path.write_text(json.dumps(lock))
            loaded = load_approved_lock(path)
            self.assertEqual(ordered_core_names_for_lock(loaded), ALTERNATIVE_CORE_ORDER)

    def test_wrong_alt_approval_or_old_nc_library_refused(self):
        lock, source = synthetic_approved()
        for flag in ("legacy_noncommercial_native_binaries_excluded",
                     "source_built_alternative_binary_rights_reviewed"):
            with self.assertRaises(ValueError):
                selected_core_set({**lock, flag: False})
        with self.assertRaises(ValueError):
            selected_core_set({**lock, "core_set_id": "unrecognized"})
        target = "linux-x86_64"
        source["targets"][target]["cores"]["snes9x"] = source["targets"][target]["cores"].pop("mednafen_supafaust")
        with self.assertRaises(ValueError):
            validate_source_inventory(lock, source)
        lock["targets"][target]["cores"]["genesis_plus_gx"] = lock["targets"][target]["cores"].pop("blastem")
        with TemporaryDirectory() as folder:
            path = Path(folder) / "wrong.json"
            path.write_text(json.dumps(lock))
            with self.assertRaises(ValueError):
                load_approved_lock(path)

    def test_exact_native_name_and_reject_original_core(self):
        lock, _ = synthetic_approved()
        _, core = native_for_target(lock, "linux", "x86_64", "blastem")
        self.assertEqual(core["file"], "blastem_libretro.so")
        with self.assertRaises(ValueError):
            native_for_target(lock, "linux", "x86_64", "genesis_plus_gx")
        record = lock["targets"]["linux-x86_64"]
        manifest = {
            "build_platform": "linux", "build_architecture": "x86_64",
            "cores": [{
                "name": name, "file": entry["file"],
                "sha256": entry["native_sha256"], "size_bytes": entry["native_size_bytes"],
                "archive_sha256": entry["original_archive_sha256"],
                "archive_size_bytes": entry["original_archive_size_bytes"],
                "source_repository_url": entry["upstream_source_repository"],
            } for name, entry in record["cores"].items()],
            "dolphin_system_assets": {
                "archive_sha256": record["dolphin_sys"]["original_archive_sha256"],
                "archive_size_bytes": 5432,
            },
        }
        self.assertEqual(verify_native_bundle(lock, manifest), "linux-x86_64")
        manifest["cores"][0]["name"] = "snes9x"
        with self.assertRaises(ValueError):
            verify_native_bundle(lock, manifest)

    def test_fetcher_can_only_use_reviewed_production_order(self):
        lock, _ = synthetic_approved()
        with patch.dict(os.environ, {
            "AP_V30_APPROVED_RELEASE": "1", "AP_RELEASE_BUILD": "1",
            "AP_V30_TEST_CORES": "0", "AP_V30_GPL_TRIAL": "0",
        }, clear=True), patch("tools.v30_release_lock.load_approved_lock", return_value=lock):
            self.assertEqual(core_names_for_build(), ALTERNATIVE_CORE_ORDER)
        with patch.dict(os.environ, {
            "AP_V30_APPROVED_RELEASE": "1", "AP_RELEASE_BUILD": "1",
            "AP_V30_TEST_CORES": "1", "AP_V30_GPL_TRIAL": "1",
        }, clear=True):
            with self.assertRaises(ValueError):
                core_names_for_build()


if __name__ == "__main__":
    unittest.main()
