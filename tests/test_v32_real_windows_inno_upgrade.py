"""Real Inno CI install command and no-user-install security gates."""
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.v32_real_windows_inno_upgrade import (
    ORIGINAL, CANDIDATE, installation_arguments, run_inno_upgrade,
)


class WindowsActualInnoTests(unittest.TestCase):
    def test_expected_flags_run_installer_exes_not_unpacker(self):
        result = installation_arguments(
            Path("original-setup.exe"), Path("C:/CI Apps/Anything Plays"),
            Path("C:/CI Logs/setup.log"),
        )
        self.assertEqual(result[0], "original-setup.exe")
        self.assertIn("/VERYSILENT", result)
        self.assertIn("/CURRENTUSER", result)
        self.assertIn("/NOICONS", result)
        # pathlib uses backslashes on Windows and forward slashes on
        # Linux. The actual native installer receives the correct host path.
        normalized = [item.replace(chr(92), "/") for item in result]
        self.assertIn("/DIR=C:/CI Apps/Anything Plays", normalized)
        self.assertIn("/LOG=C:/CI Logs/setup.log", normalized)
        self.assertNotIn("unpack", " ".join(result))

    def test_real_inno_rejected_outside_windows_ci(self):
        with TemporaryDirectory() as td:
            old = Path(td) / ORIGINAL
            new = Path(td) / CANDIDATE
            old.write_bytes(b"MZ" + b"x" * 1100000)
            new.write_bytes(b"MZ" + b"y" * 1100000)
            with patch.dict(os.environ, {
                "GITHUB_ACTIONS": "false",
                "AP_V32_STABLE_CANDIDATE": "1",
            }):
                with self.assertRaisesRegex(ValueError, "private Windows CI"):
                    run_inno_upgrade(
                        old, new, Path(td) / "installed", Path(td), "a" * 40,
                    )

    def test_invalid_source_sha_fails_before_executing_any_program(self):
        with TemporaryDirectory() as td:
            old = Path(td) / ORIGINAL
            new = Path(td) / CANDIDATE
            with (
                patch.object(sys, "platform", "win32"),
                patch.dict(os.environ, {
                    "GITHUB_ACTIONS": "true",
                    "AP_V32_STABLE_CANDIDATE": "1",
                }),
            ):
                with self.assertRaisesRegex(ValueError, "source SHA"):
                    run_inno_upgrade(old, new, Path(td) / "install", td, "invalid")


if __name__ == "__main__":
    unittest.main()
