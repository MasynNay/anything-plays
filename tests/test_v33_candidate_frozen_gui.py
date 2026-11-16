"""Synthetic contract for the installed 3.3 frozen Tk acceptance verifier.

No camera, ROM, SDL device, OS installer or desktop is started by these tests.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.v33_candidate_frozen_gui import (
    PRIVATE_DIR, REQUIRED_FALSE, REQUIRED_TRUE, STABLE_CANARIES,
    seed, verify,
)


def valid_report():
    return {
        **{name: True for name in REQUIRED_TRUE},
        **{name: False for name in REQUIRED_FALSE},
        "v33_settings_namespace": "anything-plays-33-candidate",
        "initialized_system": "gba",
        "console_profile_count": 18,
        "error": None,
    }


class FrozenV33CandidateAcceptanceTests(unittest.TestCase):
    def fixture(self, base):
        home = base / "home"
        home.mkdir()
        seed(home)
        (home / PRIVATE_DIR).mkdir()
        report = base / "frozen.json"
        report.write_text(json.dumps(valid_report()), encoding="utf-8")
        return home, report

    def test_real_frozen_report_shape_and_stable_canaries(self):
        with TemporaryDirectory() as directory:
            home, report = self.fixture(Path(directory))
            stable_before = {
                name: hashlib.sha256((home / name).read_bytes()).digest()
                for name in STABLE_CANARIES
            }
            outcome = verify(report, home)
            self.assertTrue(outcome["frozen_candidate_gui_started"])
            self.assertTrue(outcome["synthetic_stream_window_verified"])
            self.assertTrue(outcome["historical_settings_unchanged"])
            self.assertFalse(outcome["public_release_approved"])
            self.assertFalse(outcome["hardware_camera_tested"])
            for name, original_hash in stable_before.items():
                self.assertEqual(
                    hashlib.sha256((home / name).read_bytes()).digest(),
                    original_hash,
                )

    def test_seed_refuses_any_existing_candidate_or_prior_settings(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()
            seed(home)
            with self.assertRaisesRegex(ValueError, "already exists"):
                seed(home)
            (home / PRIVATE_DIR).mkdir()
            with self.assertRaisesRegex(ValueError, "already exists"):
                seed(home)

    def test_wrong_identity_skipped_tk_or_unverified_hardware_fails(self):
        with TemporaryDirectory() as directory:
            home, report = self.fixture(Path(directory))
            for field, corrupt in (
                ("passed", False),
                ("actual_tk_mainloop_ran", False),
                ("frozen_binary", False),
                ("v33_frozen_isolation_verified", False),
                ("v33_input_disarmed_at_startup", False),
                ("stream_output_window_opened", False),
                ("stream_camera_reference_rendered", False),
                ("stream_closed_cleanly", False),
                ("physical_qa_approved", True),
                ("camera_hardware_tested", True),
                ("public_distribution_approved", True),
                ("v33_settings_namespace", "anything-plays-31"),
                ("initialized_system", "gamecube"),
                ("console_profile_count", 2),
                ("error", "native camera /Users/private/serial-99"),
            ):
                with self.subTest(field=field):
                    report.write_text(
                        json.dumps({**valid_report(), field: corrupt}),
                        encoding="utf-8",
                    )
                    with self.assertRaises(ValueError):
                        verify(report, home)

    def test_host_qa_executes_installed_frozen_app_on_each_platform(self):
        workflow = (Path(__file__).resolve().parents[1]
                    / ".github/workflows/v33-private-candidate-installers.yml")
        source = workflow.read_text(encoding="utf-8")
        for expected in (
            "Launch real frozen Linux Tk candidate",
            "Install real Windows Inno candidate",
            "Mount genuine macOS QA DMG",
            "dpkg-deb -x",
            "tools.assemble_v31_full_windows import unpack",
            "hdiutil attach -readonly",
            'ENTRY="$BUNDLE/Contents/MacOS/AnythingPlays"',
            "$env:AP_V33_GUI_SMOKE_CHECK = '1'",
            "AP_V33_GUI_SMOKE_CHECK=1",
            "release/V33_FROZEN_GUI_RECEIPT.json",
            "AP_V33_CANDIDATE: \"1\"",
            "AP_RELEASE_BUILD: \"0\"",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, source)
        self.assertGreaterEqual(source.count("--ap-v30-ui-smoke"), 3)
        self.assertEqual(
            source.count("python -m tools.v33_candidate_frozen_gui verify"),
            3,
        )

    def test_historical_changes_or_links_fail_closed(self):
        with TemporaryDirectory() as directory:
            base = Path(directory)
            home, report = self.fixture(base)
            for name, original in STABLE_CANARIES.items():
                with self.subTest(name=name):
                    location = home / name
                    location.write_bytes(b"candidate modified public data")
                    with self.assertRaisesRegex(ValueError, "historical"):
                        verify(report, home)
                    location.write_bytes(original)
            report_link = base / "linked-report.json"
            try:
                report_link.symlink_to(report)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unsupported")
            with self.assertRaisesRegex(ValueError, "linked"):
                verify(report_link, home)
            private = home / PRIVATE_DIR
            private.rmdir()
            private.symlink_to(home / ".config" / "anything-plays-31",
                               target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "private"):
                verify(report, home)


if __name__ == "__main__":
    unittest.main()
