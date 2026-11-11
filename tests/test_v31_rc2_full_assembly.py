"""Fail-closed RC2 full native-core assembly, using synthetic receipts.

The four real native installers are exercised separately by GitHub Actions.
These tests intentionally check the exact source, names, flags and digests
BEFORE any large native installer is executed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import assemble_v31_full_linux as linux
from tools import assemble_v31_full_windows as win
from tools import assemble_v31_full_macos as mac
from tools.v31_rc2_source import (
    checked_rc2_source_revision, require_rc2_receipt, STAGE_STATUS, FULL_STATUS
)


SHA = "a" * 40
FLAGS = {
    "AP_V31_RC2": "1",
    "AP_V31_RC": "0",
    "AP_V31_PREVIEW": "0",
    "AP_V31_NEXT_QA": "1",
    "AP_V31_FULL_TEST_CORES": "1",
    "AP_V31_QA_CHECKOUT_SHA": SHA,
    "AP_RELEASE_BUILD": "0",
    "AP_V30_APPROVED_RELEASE": "0",
    "AP_V30_STABLE_CANDIDATE": "0",
    "AP_V30_TEST_CORES": "0",
    "AP_V30_GPL_TRIAL": "0",
    "AP_V30_TIA_TRIAL": "0",
}


def source_receipt(target, installer, digest, size):
    return {
        "schema_version": 1,
        "status": STAGE_STATUS,
        "public_release_approved": False,
        "final_release_candidate": False,
        "target": target,
        "source_revision": SHA,
        "version": "3.1.0-rc2",
        "settings_namespace": "anything-plays-31-rc2",
        "installer": installer,
        "sha256": digest,
        "size_bytes": size,
        "bundled_console_profiles": ["gb", "gbc", "gba"],
        "hardware_controller_verified": False,
    }


class Rc2FullBuildTests(unittest.TestCase):
    def test_full_source_is_exact_checked_out_nonrelease_rc2(self):
        self.assertEqual(
            checked_rc2_source_revision(SHA, environ=FLAGS, checkout=SHA), SHA
        )
        for key, value in (
            ("AP_V31_RC2", "0"),
            ("AP_V31_NEXT_QA", "0"),
            ("AP_V31_FULL_TEST_CORES", "0"),
            ("AP_V31_RC", "1"),
            ("AP_V31_PREVIEW", "1"),
            ("AP_RELEASE_BUILD", "1"),
            ("AP_V30_APPROVED_RELEASE", "1"),
            ("AP_V30_STABLE_CANDIDATE", "1"),
            ("AP_V30_GPL_TRIAL", "1"),
            ("AP_V30_TIA_TRIAL", "1"),
            ("AP_V31_QA_CHECKOUT_SHA", "b" * 40),
        ):
            with self.subTest(field=key), self.assertRaises(ValueError):
                checked_rc2_source_revision(SHA, environ=dict(FLAGS, **{key: value}),
                                            checkout=SHA)
        for bad in ("", "a" * 39, "A" * 40, "b" * 40, "3.1.0"):
            with self.subTest(sha=bad), self.assertRaises(ValueError):
                checked_rc2_source_revision(bad, environ=FLAGS, checkout=SHA)
        with self.assertRaises(ValueError):
            checked_rc2_source_revision(SHA, environ=FLAGS, checkout="b" * 40)

    def test_metadata_rejects_forged_source_or_release_approval(self):
        good = source_receipt("windows-x64", win.RC2_PREVIEW, "c" * 64,
                              1048577)
        self.assertTrue(require_rc2_receipt(
            good, source=SHA, target="windows-x64",
            installer=win.RC2_PREVIEW, digest="c" * 64, size=1048577
        ))
        for key, value in (
            ("schema_version", 2), ("status", "APPROVED"),
            ("public_release_approved", True),
            ("final_release_candidate", True),
            ("source_revision", "b" * 40),
            ("version", "3.1.0-rc1"),
            ("settings_namespace", "anything-plays-31-rc1"),
            ("installer", win.RC_PREVIEW),
            ("sha256", "b" * 64),
            ("bundled_console_profiles", ["gb"]),
            ("hardware_controller_verified", True),
            ("size_bytes", 1),
        ):
            with self.subTest(field=key), self.assertRaises(ValueError):
                require_rc2_receipt(
                    dict(good, **{key: value}), source=SHA,
                    target="windows-x64", installer=win.RC2_PREVIEW,
                    digest="c" * 64, size=1048577,
                )

    def test_linux_windows_and_mac_refuse_mutated_stage_or_3_0(self):
        configs = [
            (linux, "linux-x64", linux.STABLE,
             linux.RC2_PREVIEW, linux.sha,
             lambda stable, source, sums, receipt:
                 linux.validate_inputs(stable, source, sums, receipt,
                                       rc2=True, expected_source_revision=SHA)),
            (win, "windows-x64", win.STABLE,
             win.RC2_PREVIEW, win.hash_file,
             lambda stable, source, sums, receipt:
                 win.check_inputs(stable, source, sums, receipt,
                                  rc2=True, expected_source_revision=SHA)),
        ]
        for mod, target, baseline, candidate, digest, validate in configs:
            with self.subTest(platform=target), TemporaryDirectory() as tmp:
                root = Path(tmp)
                old = root / baseline
                new = root / candidate
                sums = root / "SHA256SUMS.txt"
                receipt = root / "RC2_SOURCE_STAGE_RECEIPT.json"
                old.write_bytes(b"original native 3.0")
                new.write_bytes(b"RC2-source" * 110000)
                sums.write_text(digest(old) + "  " + old.name + "\n", "utf-8")
                meta = source_receipt(target, new.name, digest(new),
                                      new.stat().st_size)
                receipt.write_text(json.dumps(meta), "utf-8")
                with patch.dict(os.environ, FLAGS):
                    with patch("tools.v31_rc2_source.subprocess.check_output",
                               return_value=SHA + "\n"):
                        self.assertEqual(validate(old, new, sums, receipt),
                                         digest(old))
                        meta["settings_namespace"] = "anything-plays-31-rc1"
                        receipt.write_text(json.dumps(meta), "utf-8")
                        with self.assertRaises(ValueError):
                            validate(old, new, sums, receipt)
                        meta["settings_namespace"] = "anything-plays-31-rc2"
                        receipt.write_text(json.dumps(meta), "utf-8")
                        old.write_bytes(b"modified stable source")
                        with self.assertRaises(ValueError):
                            validate(old, new, sums, receipt)

    def test_both_mac_arches_require_separate_rc2_signed_app_receipt(self):
        for arch in ("arm64", "x64"):
            with self.subTest(arch=arch), TemporaryDirectory() as tmp:
                root = Path(tmp)
                old = root / ("AnythingPlays-3.0.0-macos-" + arch + ".dmg")
                new = root / ("AnythingPlays-3.1.0-rc2-macos-" + arch + ".dmg")
                sums, receipt = root / "SHA256SUMS.txt", root / "RC2_SOURCE_STAGE_RECEIPT.json"
                old.write_bytes(b"original Mac natives")
                new.write_bytes(b"RC2-macos" * 130000)
                sums.write_text(mac.digest(old) + "  " + old.name + "\n", "utf-8")
                stage = source_receipt("macos-" + arch, new.name, mac.digest(new),
                                       new.stat().st_size)
                receipt.write_text(json.dumps(stage), "utf-8")
                with patch.dict(os.environ, FLAGS):
                    with patch("tools.v31_rc2_source.subprocess.check_output",
                               return_value=SHA + "\n"):
                        self.assertEqual(
                            mac.verify_inputs(arch, old, new, sums, receipt,
                                              rc2=True, expected_source_revision=SHA),
                            mac.digest(old),
                        )
                        new.write_bytes(b"corrupted app image")
                        with self.assertRaises(ValueError):
                            mac.verify_inputs(arch, old, new, sums, receipt,
                                              rc2=True, expected_source_revision=SHA)

    def test_native_core_inventory_accepts_only_one_explicit_rc2_channel(self):
        from fetch_mgba_core import core_names_for_build
        from tools.v30_release_lock import ALTERNATIVE_TIA_CORE_ORDER
        with patch.dict(os.environ, FLAGS, clear=False):
            result = core_names_for_build()
            self.assertEqual(tuple(result), tuple(ALTERNATIVE_TIA_CORE_ORDER))
            self.assertEqual(len(result), 11)
        for changed in (
            {"AP_V31_RC": "1"},
            {"AP_V31_PREVIEW": "1"},
            {"AP_RELEASE_BUILD": "1"},
            {"AP_V30_APPROVED_RELEASE": "1"},
            {"AP_V31_NEXT_QA": "0"},
            {"AP_V31_QA_CHECKOUT_SHA": ""},
        ):
            with self.subTest(flags=changed):
                with patch.dict(os.environ, dict(FLAGS, **changed), clear=False):
                    with self.assertRaises(ValueError):
                        core_names_for_build()

    def test_windows_full_installer_is_exported_under_actual_rc2_name(self):
        self.assertEqual(
            win.full_installer_filename(rc2=True),
            "AnythingPlaysSetup-3.1.0-rc2-full.exe",
        )
        self.assertEqual(win.full_installer_filename(rc1=True), win.RC_FULL)
        self.assertEqual(win.full_installer_filename(), win.FULL)
        with self.assertRaises(ValueError):
            win.full_installer_filename(rc1=True, rc2=True)
        # This helper must actually drive the generated installer export;
        # a correctly selected filename in metadata but the wrong EXE path
        # previously produced a 14 KB report-only artifact on Windows.
        source = (Path(__file__).resolve().parents[1] /
                  "tools/assemble_v31_full_windows.py").read_text("utf-8")
        self.assertIn(
            "target = output/full_installer_filename(rc1=rc1, rc2=rc2)",
            source,
        )

    def test_full_linux_receipt_declares_authentic_platform(self):
        source = (Path(__file__).resolve().parents[1] /
                  "tools/assemble_v31_full_linux.py").read_text("utf-8")
        self.assertIn('"target": "linux-x64"', source)
        # Both installed QA and final release staging must be able to
        # authenticate the target against the exact original Linux receipt.
        self.assertIn('"installer": deb.name', source)

    def test_mac_disk_image_retries_only_transient_resource_busy(self):
        from unittest.mock import Mock
        from tools.assemble_v31_full_macos import create_disk_image
        with TemporaryDirectory() as tmp:
            path = Path(tmp)
            app, dmg = path / "AnythingPlays31RC2.app", path / "rc2.dmg"
            app.mkdir()
            fail = Mock(returncode=1, stderr="hdiutil: create failed - Resource busy",
                        stdout="")
            def success(*args, **kwargs):
                dmg.write_bytes(b"test-dmg" * 200000)
                return Mock(returncode=0, stderr="", stdout="")
            calls = [0]
            def transient_then_success(*args, **kwargs):
                calls[0] += 1
                return fail if calls[0] == 1 else success(*args, **kwargs)
            with patch("tools.assemble_v31_full_macos.subprocess.run",
                       side_effect=transient_then_success) as run:
                with patch("tools.assemble_v31_full_macos.time.sleep") as sleep:
                    create_disk_image(app, dmg, attempts=3)
                    self.assertEqual(run.call_count, 2)
                    self.assertEqual(sleep.call_count, 1)
                    self.assertGreater(dmg.stat().st_size, 1024 * 1024)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            app, dmg = root / "Example.app", root / "failed.dmg"
            app.mkdir()
            denied = Mock(returncode=1, stdout="",
                          stderr="hdiutil: create failed - Invalid argument")
            with patch("tools.assemble_v31_full_macos.subprocess.run",
                       return_value=denied) as run:
                with patch("tools.assemble_v31_full_macos.time.sleep") as sleep:
                    with self.assertRaises(RuntimeError):
                        create_disk_image(app, dmg)
                    self.assertEqual(run.call_count, 1)
                    sleep.assert_not_called()

    def test_rc2_does_not_change_historical_rc1_or_preview_names(self):
        self.assertEqual(linux.RC_PREVIEW,
                         "anything-plays-31-rc1_3.1.0~rc1_amd64.deb")
        self.assertEqual(win.RC_PREVIEW, "AnythingPlaysSetup-3.1.0-rc1.exe")
        self.assertEqual(linux.RC_FULL,
                         "anything-plays-31-rc1_3.1.0~rc1full_amd64.deb")
        self.assertEqual(win.RC_FULL, "AnythingPlaysSetup-3.1.0-rc1-full.exe")
        self.assertEqual(linux.RC2_FULL,
                         "anything-plays-31-rc2_3.1.0~rc2full_amd64.deb")
        self.assertEqual(win.RC2_FULL,
                         "AnythingPlaysSetup-3.1.0-rc2-full.exe")
        self.assertEqual(FULL_STATUS, "UNRELEASED_3_1_FULL_RC2_QA")


if __name__ == "__main__":
    unittest.main()
