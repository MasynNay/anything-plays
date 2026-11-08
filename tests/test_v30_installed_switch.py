"""Fail-closed provenance checks for actual offline 3.0 GPL trial switcher.

These are synthetic, intentionally non-executable unit fixtures; real four-OS
native playback is required separately in the associated Actions workflow.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from anything_plays.v30_gpl_trial import EXPECTED_SOURCE_COMMITS, MARKER, STATUS
from fetch_mgba_core import V30_GPL_TRIAL_CORES
from tools import probe_v30_installed_switch as probe


TARGET = ("windows-x64" if sys.platform == "win32"
          else ("macos-arm64" if platform.machine().lower() in ("arm64", "aarch64")
                else "macos-x64") if sys.platform == "darwin" else "linux-x64")
SUFFIX = probe.SUFFIX[TARGET]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def synthetic_install(root):
    """Create fake source-hash fixtures without any real emulator code."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    rows, hashes = [], {}
    for name in V30_GPL_TRIAL_CORES:
        data = (f"test fixture native bytes {name}").encode() * 10
        filename = f"{name}_libretro{SUFFIX}"
        (root / filename).write_bytes(data)
        rows.append({"name": name, "file": filename,
                     "sha256": sha(data), "size_bytes": len(data)})
        hashes[name] = sha(data)
    (root / "CORE_PROVENANCE.json").write_text(
        json.dumps({"cores": rows}), "utf-8")
    dolphin = root / "dolphin-emu" / "Sys"
    dolphin.mkdir(parents=True, exist_ok=True)
    (dolphin / "codehandler.bin").write_bytes(b"original sys test data")
    entries = {}
    for name, source_commit in EXPECTED_SOURCE_COMMITS.items():
        entries[name] = {
            "native_filename": f"{name}_libretro{SUFFIX}",
            "native_sha256": hashes[name],
            "source_commit": source_commit,
            "source_repository": {
                "mednafen_supafaust": "https://github.com/libretro/supafaust",
                "blastem": "https://github.com/libretro/blastem",
            }[name],
        }
    runtimes = {}
    if TARGET == "windows-x64":
        data = b"MZ" + b"synthetic Windows DLL, never executed" * 1000
        (root / "libwinpthread-1.dll").write_bytes(data)
        runtimes["libwinpthread-1.dll"] = sha(data)
    marker = {
        "schema_version": 1, "status": STATUS, "target": TARGET,
        "all_console_profiles": 18, "native_core_count": 11,
        "alternatives": entries, "runtime_dependencies": runtimes,
        "public_binary_distribution_approved": False,
        "combined_gpl_license_reviewed": False,
        "production_core_substitution_approved": False,
        "physical_qa_approved": False,
    }
    (root / MARKER).write_text(json.dumps(marker), "utf-8")
    return marker


class InstalledCoreSwitchContracts(unittest.TestCase):
    def test_true_18_profile_and_11_native_offline_fixture(self):
        with TemporaryDirectory() as temp:
            root = Path(temp) / "app" / "cores"
            synthetic_install(root)
            found = probe.verify_installed_payload(root, TARGET)
            self.assertEqual(len(found["core_hashes"]), 11)
            self.assertEqual(found["source"]["all_console_profiles"], 18)
            self.assertEqual(found["snes"].name, f"mednafen_supafaust_libretro{SUFFIX}")
            self.assertEqual(found["sega"].name, f"blastem_libretro{SUFFIX}")
            self.assertEqual(len(probe.CYCLES), 7)
            self.assertEqual(set(probe.FLAGS), {
                "combined_gpl_license_reviewed", "public_binary_distribution_approved",
                "physical_audio_camera_save_qa_approved", "release_approved",
            })

    def test_refuses_corrupt_source_or_noncommercial_native_substitution(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            marker = synthetic_install(root)
            corrupt = root / f"blastem_libretro{SUFFIX}"
            corrupt.write_bytes(b"tampered!")
            with self.assertRaises(ValueError):
                probe.verify_installed_payload(root, TARGET)
            synthetic_install(root)
            marker["alternatives"]["blastem"]["source_commit"] = "0" * 40
            (root / MARKER).write_text(json.dumps(marker), "utf-8")
            with self.assertRaises(ValueError):
                probe.verify_installed_payload(root, TARGET)
            synthetic_install(root)
            (root / f"snes9x_libretro{SUFFIX}").write_bytes(b"noncommercial original core")
            with self.assertRaises(ValueError):
                probe.verify_installed_payload(root, TARGET)

    def test_refuses_missing_other_system_and_missing_dolphin_sys(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            synthetic_install(root)
            (root / f"fceumm_libretro{SUFFIX}").unlink()
            with self.assertRaises(ValueError):
                probe.verify_installed_payload(root, TARGET)
            synthetic_install(root)
            (root / "dolphin-emu" / "Sys" / "codehandler.bin").unlink()
            with self.assertRaises(ValueError):
                probe.verify_installed_payload(root, TARGET)

    def test_incorrect_actual_architecture_refused(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            synthetic_install(root)
            other = "linux-x64" if TARGET != "linux-x64" else "windows-x64"
            with self.assertRaises(ValueError):
                probe.verify_installed_payload(root, other)

    def test_workflow_keeps_all_approval_flags_false_and_never_uploads_app(self):
        work = Path(__file__).resolve().parents[1]
        workflow = (work / ".github/workflows/v30-gpl-offline-installer-trial.yml").read_text("utf-8")
        self.assertIn("probe_v30_installed_switch.py", workflow)
        self.assertIn("ACTUAL_INSTALLED_7_CYCLE_SWITCH_UNAPPROVED.json", workflow)
        self.assertIn("AP_RELEASE_BUILD: '0'", workflow)
        self.assertIn("AP_V30_APPROVED_RELEASE: '0'", workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertIn("test-evidence/*.json", workflow)
        self.assertNotIn("dist/**", workflow)
        for target in ("windows-x64", "linux-x64", "macos-arm64", "macos-x64"):
            self.assertIn("target: " + target, workflow)


if __name__ == "__main__":
    unittest.main()
