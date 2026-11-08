"""Physical 3.0 QA must be user-driven, offline and explicitly unapproved."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.systems import SYSTEMS
from tools import v30_physical_qa as qa


class PhysicalQAContracts(unittest.TestCase):
    def test_detects_all_supported_real_architectures_and_rejects_unsupported(self):
        self.assertEqual(qa.detected_target("Linux", "x86_64"), "linux-x64")
        self.assertEqual(qa.detected_target("Windows", "AMD64"), "windows-x64")
        self.assertEqual(qa.detected_target("Darwin", "arm64"), "macos-arm64")
        self.assertEqual(qa.detected_target("Darwin", "x86_64"), "macos-x86_64")
        with self.assertRaisesRegex(ValueError, "Unsupported physical"):
            qa.detected_target("Linux", "aarch64")

    def test_exact_real_18_console_contract_matches_app_not_synthetic_inventory(self):
        self.assertEqual(len(SYSTEMS), 18)
        self.assertEqual(len(qa.CONSOLE_CHECKS), 8)
        self.assertIn("camera_controls", qa.CONSOLE_CHECKS)
        self.assertIn("save_then_reload", qa.CONSOLE_CHECKS)
        self.assertIn("rom_change_restart", qa.CONSOLE_CHECKS)
        self.assertIn("extended_play_stable", qa.CONSOLE_CHECKS)
        with TemporaryDirectory() as td, patch.object(qa, "detected_target", return_value="linux-x64"):
            path = Path(td) / "anything_plays_3.0_preview.deb"
            contents = b"local package test bytes" * 64
            path.write_bytes(contents)
            obj = qa.create_report(path, commit="a"*40)
            self.assertEqual(set(obj["console_checks"]), set(SYSTEMS))
            self.assertEqual(len(obj["console_checks"]) * len(qa.CONSOLE_CHECKS)
                             + len(qa.HOST_CHECKS), 150)
            self.assertEqual(obj["installer_sha256"], hashlib.sha256(contents).hexdigest())
            self.assertNotIn(str(path), json.dumps(obj))
            self.assertIn("contains_rom_names_paths_or_game_files", obj)
            self.assertIs(obj["contains_rom_names_paths_or_game_files"], False)
            self.assertFalse(obj["public_release_approved"])
            self.assertFalse(obj["external_license_redistribution_reviewed"])
            self.assertFalse(obj["independent_hardware_reviewed"])
            self.assertFalse(obj["source_to_binary_correspondence_reviewed"])

    def test_rejects_mismatched_installer_platform_and_unpinned_sources(self):
        with TemporaryDirectory() as td, patch.object(qa, "detected_target", return_value="windows-x64"):
            d = Path(td)
            (d/"app.exe").write_bytes(b"EXE")
            (d/"app.dmg").write_bytes(b"DMG")
            with self.assertRaisesRegex(ValueError, "extension"):
                qa.create_report(d/"app.dmg", commit="a"*40)
            with self.assertRaisesRegex(ValueError, "does not match"):
                qa.create_report(d/"app.exe", commit="a"*40, target="linux-x64")
            with self.assertRaisesRegex(ValueError, "forty-character"):
                qa.create_report(d/"app.exe", commit="unknown")
            self.assertEqual(qa.create_report(d/"app.exe", commit="b"*40)["target"],
                             "windows-x64")

    def test_atomic_write_edit_and_immutable_actual_installer_identity(self):
        with TemporaryDirectory() as td, patch.object(qa, "detected_target", return_value="linux-x64"):
            folder = Path(td)
            source = folder/"preview.deb"
            source.write_bytes(b"legitimate local installer file" * 100)
            path = folder/"review.json"
            report = qa.create_report(source, commit="d"*40)
            qa._store(path, report)
            self.assertEqual(qa.load_report(path), report)
            with self.assertRaisesRegex(ValueError, "new for init"):
                qa._store(path, report)
            qa.record_result(report, system="n64", check="rom_change_restart", result="pass")
            qa.record_result(report, system=None, check="fresh_installer_clean_install",
                             result="fail")
            qa._store(path, report, existing=True)
            reread = qa.load_report(path)
            self.assertEqual(reread["console_checks"]["n64"]["rom_change_restart"],
                             "pass")
            self.assertEqual(reread["host_checks"]["fresh_installer_clean_install"], "fail")
            self.assertIn("NOT COMPLETE", qa.brief(reread))
            mangled = copy.deepcopy(reread)
            mangled["installer_sha256"] = "0"*64
            with self.assertRaisesRegex(ValueError, "Immutable"):
                qa._store(path, mangled, existing=True)
            self.assertEqual(qa.load_report(path), reread)

    def test_wizard_only_records_observed_answers_and_can_save_progress(self):
        with TemporaryDirectory() as td, patch.object(qa, "detected_target", return_value="macos-arm64"):
            source = Path(td)/"preview.dmg"
            source.write_bytes(b"preview"*40)
            report = qa.create_report(source, commit="a"*40)
            answers = iter(("p", "f", "q"))
            messages = []
            checkpoints = []
            qa.review_wizard(report, reader=lambda prompt: next(answers),
                             printer=messages.append,
                             on_record=lambda state: checkpoints.append(
                                 dict(state["host_checks"])))
            self.assertEqual(len(checkpoints), 2)
            self.assertEqual(checkpoints[0][qa.HOST_CHECKS[0]], "pass")
            self.assertEqual(checkpoints[1][qa.HOST_CHECKS[1]], "fail")
            self.assertEqual(report["host_checks"][qa.HOST_CHECKS[0]], "pass")
            self.assertEqual(report["host_checks"][qa.HOST_CHECKS[1]], "fail")
            self.assertEqual(report["host_checks"][qa.HOST_CHECKS[2]], "not-tested")
            self.assertEqual(sum(1 for r in report["console_checks"].values()
                                 for value in r.values() if value == "pass"), 0)
            self.assertTrue(any("installed app" in m for m in messages))

    def test_report_never_accepts_automated_legal_or_public_approval(self):
        with TemporaryDirectory() as td, patch.object(qa, "detected_target", return_value="linux-x64"):
            file = Path(td)/"preview.deb"
            file.write_bytes(b"a"*20)
            report = qa.create_report(file, commit="a"*40)
            for forbidden in (
                "independent_hardware_reviewed",
                "external_license_redistribution_reviewed",
                "source_to_binary_correspondence_reviewed",
                "production_approval", "public_release_approved",
                "contains_rom_names_paths_or_game_files",
            ):
                with self.subTest(field=forbidden):
                    bad = copy.deepcopy(report)
                    bad[forbidden] = True
                    with self.assertRaisesRegex(ValueError, "Forbidden"):
                        qa.validate_report(bad)
            bad = copy.deepcopy(report)
            bad["console_checks"].pop("gamecube")
            with self.assertRaisesRegex(ValueError, "all 18"):
                qa.validate_report(bad)
            bad = copy.deepcopy(report)
            bad["console_checks"]["gb"]["save_then_reload"] = "auto-pass"
            with self.assertRaisesRegex(ValueError, "invalid manual"):
                qa.validate_report(bad)

    def test_completed_owner_report_remains_unapproved_and_export_is_sanitized(self):
        with TemporaryDirectory() as td, patch.object(qa, "detected_target", return_value="linux-x64"):
            root = Path(td)
            installer = root/"preview.deb"
            installer.write_bytes(b"local preview installer only")
            report = qa.create_report(installer, commit="b"*40)
            for check in qa.HOST_CHECKS:
                qa.record_result(report, check=check, result="pass")
            for system in SYSTEMS:
                for check in qa.CONSOLE_CHECKS:
                    qa.record_result(report, check=check, result="pass", system=system)
            status = qa.brief(report)
            self.assertIn("150/150", status)
            self.assertIn("COMPLETE FOR INDEPENDENT REVIEW", status)
            self.assertIn("NOT APPROVED", status)
            directory = root/"evidence"
            output = qa.export_review(report, directory)
            self.assertEqual({x.name for x in directory.iterdir()}, {
                "V30_PHYSICAL_QA_OWNER_REPORTED_UNREVIEWED.json", "SHA256SUMS.txt",
            })
            digest, name = (directory/"SHA256SUMS.txt").read_text("ascii").split()
            self.assertEqual(digest, hashlib.sha256(output.read_bytes()).hexdigest())
            self.assertEqual(name, output.name)
            self.assertEqual(qa.load_report(output), report)
            self.assertNotIn(str(root), output.read_text("utf-8"))
            with self.assertRaisesRegex(ValueError, "new or empty"):
                qa.export_review(report, directory)

    def test_invalid_console_and_host_checks_are_not_skipped_or_auto_passed(self):
        with TemporaryDirectory() as td, patch.object(qa, "detected_target", return_value="linux-x64"):
            file = Path(td)/"app.deb"
            file.write_bytes(b"x")
            report = qa.create_report(file, commit="c"*40)
            with self.assertRaisesRegex(ValueError, "Unknown"):
                qa.record_result(report, check="gameplay", result="pass")
            with self.assertRaisesRegex(ValueError, "Unknown"):
                qa.record_result(report, check="video", system="gamecube", result="pass")
            with self.assertRaisesRegex(ValueError, "must be"):
                qa.record_result(report, check="camera_controls", system="ngp",
                                 result="skipped")
            self.assertEqual(qa.counts(report)["not-tested"], 150)

    def test_help_runs_without_camera_dependencies_or_game_data(self):
        from contextlib import redirect_stdout
        from io import StringIO
        out = StringIO()
        with redirect_stdout(out):
            with self.assertRaises(SystemExit) as caught:
                qa.main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        for name in ("init", "wizard", "status", "record", "export"):
            self.assertIn(name, out.getvalue())


if __name__ == "__main__":
    unittest.main()
