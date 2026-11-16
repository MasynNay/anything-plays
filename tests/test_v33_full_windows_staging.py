"""Pure safety tests for private full-native 3.3 Windows package staging.

Actual Inno installation, core checksums and the full native repack run on
Windows CI. These unit tests do not install software or execute any ROM.
"""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.stage_v33_full_windows import BASELINE, FULL, SOURCE, source_gate


SHA = "b" * 40


class FullNativeV33WindowsSourceTests(unittest.TestCase):
    def fixture(self, folder):
        folder = Path(folder)
        stable = folder / BASELINE
        candidate = folder / SOURCE
        stable.write_bytes(b"published-v32-windows" * 70000)
        candidate.write_bytes(b"candidate-v33-mgba" * 80000)
        checksums = folder / "SHA256SUMS.txt"
        checksums.write_text(
            hashlib.sha256(stable.read_bytes()).hexdigest()
            + "  " + BASELINE + "\n", encoding="utf-8",
        )
        expected = {
            "format": "anything-plays-v33-owner-qa",
            "target": "windows-x64", "source_sha": SHA,
            "channel": "v33_candidate", "version": "3.3.0-qa",
            "settings_namespace": "anything-plays-33-candidate",
            "installer_filename": SOURCE,
            "installer_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            "bundled_core_names": ["mgba_libretro.dll"],
            "bundled_core_count": 1,
            "public_release_approved": False,
            "hardware_input_tested": False,
            "physical_camera_tested": False,
            "gamecube_bundled": False,
            "full_18_console_gameplay_tested": False,
            "installer_fully_tested_on_real_host": False,
        }
        receipt = folder / "V33_CANDIDATE_QA_RECEIPT.json"
        receipt.write_text(json.dumps(expected), encoding="utf-8")
        return stable, candidate, checksums, receipt, expected

    def test_exact_public_source_and_candidate_gates(self):
        with TemporaryDirectory() as temp:
            s, c, sums, receipt, record = self.fixture(temp)
            self.assertEqual(source_gate(s, c, sums, receipt, SHA), (s, c))
            self.assertEqual(BASELINE, "AnythingPlaysSetup-3.2.0.exe")
            self.assertEqual(FULL, "AnythingPlaysSetup-3.3.0-fullqa1.exe")

    def test_rejects_mismatched_hashes_or_unsupported_core_set(self):
        with TemporaryDirectory() as temp:
            stable, candidate, sums, receipt, record = self.fixture(temp)
            stable.write_bytes(b"tampered v32" * 100000)
            with self.assertRaisesRegex(ValueError, "SHA256"):
                source_gate(stable, candidate, sums, receipt, SHA)
            sums.write_text(
                hashlib.sha256(stable.read_bytes()).hexdigest()
                + "  " + BASELINE + "\n", encoding="utf-8",
            )
            for key, value in (
                ("source_sha", "c" * 40),
                ("channel", "v32_preview"),
                ("settings_namespace", "anything-plays-31"),
                ("bundled_core_names", ["dolphin_libretro.dll"]),
                ("bundled_core_count", 11),
                ("gamecube_bundled", True),
                ("physical_camera_tested", True),
                ("public_release_approved", True),
                ("untrusted_key", "/Users/private/ROM-file"),
            ):
                with self.subTest(key=key):
                    broken = {**record, key: value}
                    receipt.write_text(json.dumps(broken), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "scope"):
                        source_gate(stable, candidate, sums, receipt, SHA)

    def test_invalid_sha_and_filename_rejected(self):
        with TemporaryDirectory() as temp:
            stable, candidate, sums, receipt, record = self.fixture(temp)
            for sha in (None, "bad", SHA[:-1], SHA.upper()):
                with self.subTest(sha=sha), self.assertRaises(ValueError):
                    source_gate(stable, candidate, sums, receipt, sha)
            wrong = Path(temp) / "AnythingPlaysSetup-3.2.0.exe"
            candidate.rename(Path(temp) / "untrusted-v33.exe")
            with self.assertRaises(ValueError):
                source_gate(stable, Path(temp) / "untrusted-v33.exe",
                            sums, receipt, SHA)


if __name__ == "__main__":
    unittest.main()
