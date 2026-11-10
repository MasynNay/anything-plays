"""Test-only full offline GPL trio: source-built SNES, Sega, PCE Fast.

The nightly PCE input had an UNKNOWN original source revision. These fixtures
never claim a nightly source match, licensing clearance or public availability.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.v30_gpl_trial import (
    EXPECTED_SOURCE_COMMITS, MARKER, STATUS, PCE_SOURCE_COMMIT,
    PCE_SOURCE_REPO, validate_trial_core_directory,
)
from tools.stage_v30_gpl_trial_inputs import stage_inputs, TARGET_EXT

TARGET = ("windows-x64" if sys.platform == "win32"
          else "macos-arm64" if sys.platform == "darwin" else "linux-x64")
EXT = TARGET_EXT[TARGET]


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def sample(root):
    native = {}
    alternatives = {}
    root = Path(root)
    root.mkdir(exist_ok=True, parents=True)
    for system, name in (("snes", "mednafen_supafaust"),
                         ("sega", "blastem"),
                         ("pce", "mednafen_pce_fast")):
        name_ext = f"{name}_libretro{EXT}"
        payload = (f"synthetic test-only {name} core").encode() * 100
        (root / name_ext).write_bytes(payload)
        native[name] = sha(payload)
        if system != "pce":
            alternatives[name] = {
                "source_commit": EXPECTED_SOURCE_COMMITS[name],
                "source_repository": {
                    "mednafen_supafaust": "https://github.com/libretro/supafaust",
                    "blastem": "https://github.com/libretro/blastem",
                }[name],
                "native_sha256": native[name],
                "native_filename": name_ext,
            }
    dep = {}
    if EXT == ".dll":
        raw = b"MZ" + b"source-authored-unit-fixture" * 600
        (root / "libwinpthread-1.dll").write_bytes(raw)
        dep = {"libwinpthread-1.dll": sha(raw)}
    pce = {
        "source_repository": PCE_SOURCE_REPO,
        "source_commit": PCE_SOURCE_COMMIT,
        "native_filename": f"mednafen_pce_fast_libretro{EXT}",
        "native_sha256": native["mednafen_pce_fast"],
        "source_archive_sha256": "1" * 64,
        "native_archive_sha256": "2" * 64,
        "notice_sha256": "3" * 64,
        "original_source_build_run_id": 42444367068,
        "old_unknown_source_nightly_substituted": True,
    }
    manifest = {
        "schema_version": 1, "status": STATUS,
        "all_console_profiles": 18, "native_core_count": 11,
        "runtime_dependencies": dep,
        "alternatives": alternatives, "source_built_pce": pce,
        "public_binary_distribution_approved": False,
        "combined_gpl_license_reviewed": False,
        "physical_qa_approved": False,
        "production_core_substitution_approved": False,
    }
    (root / MARKER).write_text(json.dumps(manifest), "utf-8")
    return manifest


class PinnedPCEInCompleteAlternativeTrial(unittest.TestCase):
    def test_exact_pce_identity_recognized_without_nightly_relabeling(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            row = sample(root)
            self.assertEqual(validate_trial_core_directory(root, EXT)["source_built_pce"], row["source_built_pce"])
            self.assertIs(row["public_binary_distribution_approved"], False)
            self.assertIs(row["combined_gpl_license_reviewed"], False)
            self.assertEqual(row["source_built_pce"]["old_unknown_source_nightly_substituted"], True)

    def test_reject_wrong_source_sha_or_missing_native(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            row = sample(root)
            row["source_built_pce"]["source_commit"] = "0" * 40
            (root / MARKER).write_text(json.dumps(row), "utf-8")
            with self.assertRaises(ValueError):
                validate_trial_core_directory(root, EXT)
            row = sample(root)
            (root / f"mednafen_pce_fast_libretro{EXT}").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                validate_trial_core_directory(root, EXT)

    def test_requires_actual_original_verified_pce_artifact_not_nightly_source_guess(self):
        with patch.dict(os.environ, {
            "AP_V30_GPL_TRIAL": "1", "AP_V30_TEST_CORES": "1",
            "AP_V30_PINNED_PCE": "1", "AP_RELEASE_BUILD": "0",
            "AP_V30_APPROVED_RELEASE": "0",
        }):
            with TemporaryDirectory() as temp:
                root = Path(temp)
                with self.assertRaisesRegex(ValueError, "original authentic artifact"):
                    stage_inputs(root / "old", root / "snes", root / "sega",
                                 root / "output", root / "proof.json", TARGET)
                self.assertFalse((root / "output").exists())

    def test_genuine_pce_native_and_source_ci_mandatory_on_four_os(self):
        root = Path(__file__).resolve().parents[1]
        s = (root / "docs/history/workflows/v30-gpl-offline-installer-trial.yml").read_text("utf-8")
        self.assertIn("AP_V30_PINNED_PCE: '1'", s)
        self.assertIn("PINNED_PCE_RUN_ID: '42444367068'", s)
        self.assertIn("--pce-artifact original-source-built-pce.zip", s)
        self.assertIn("ACTUAL_INSTALLED_PINNED_PCE_NATIVE_AV_UNAPPROVED.json", s)
        self.assertIn("ACTUAL_INSTALLED_7_CYCLE_SWITCH_UNAPPROVED.json", s)
        for name in ("windows-x64", "linux-x64", "macos-arm64", "macos-x64"):
            self.assertIn("target: " + name, s)
        self.assertNotIn("gh release create", s)
        self.assertNotIn("dist/**", s)


if __name__ == "__main__":
    unittest.main()
