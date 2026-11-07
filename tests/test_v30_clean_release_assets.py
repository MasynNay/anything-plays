"""The main 3.0 release list must stay five predictable files."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.stage_v30_release_assets import (
    expected_installers, stage_application_assets
)


class CleanReleaseAssetContract(unittest.TestCase):
    def test_main_release_contains_four_platform_downloads_and_checksums(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "input", root / "public"
            source.mkdir()
            for name in expected_installers("3.0.0"):
                (source / name).write_bytes(("test:" + name).encode())
            (source / "debug-diagnostics.json").write_text("{}")
            (source / "AnythingPlays3-Core-fceumm-linux-x64.zip").write_bytes(b"not an app")
            result = stage_application_assets(
                source, output, version="3.0.0"
            )
            self.assertEqual(len(result), 5)
            self.assertEqual(set(result), {
                *expected_installers("3.0.0"), "SHA256SUMS.txt"
            })
            self.assertFalse(any("Core" in name for name in result))
            for line in (output / "SHA256SUMS.txt").read_text().splitlines():
                digest, name = line.split("  ", 1)
                self.assertEqual(
                    digest, hashlib.sha256((output / name).read_bytes()).hexdigest()
                )
            self.assertFalse((output / "debug-diagnostics.json").exists())

    def test_missing_or_legacy_installers_are_not_staged(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "input", root / "output"
            source.mkdir()
            names = expected_installers("3.0.0")
            for name in names[:-1]:
                (source / name).write_bytes(b"synthetic")
            with self.assertRaisesRegex(FileNotFoundError, "Missing valid"):
                stage_application_assets(source, output, version="3.0.0")
            self.assertFalse(output.exists())
            (source / names[-1]).write_bytes(b"synthetic")
            (source / "AnythingPlaysSetup-2.0.0.exe").write_bytes(b"stable")
            with self.assertRaisesRegex(ValueError, "Unexpected installer"):
                stage_application_assets(source, output, version="3.0.0")
            self.assertFalse(output.exists())

    def test_reject_preview_as_stable_and_preexisting_staging(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "input", root / "output"
            source.mkdir()
            with self.assertRaisesRegex(ValueError, "Only stable"):
                stage_application_assets(source, output, version="3.0.0-alpha.1")
            output.mkdir()
            (output / "previous-release.txt").write_text("preserved")
            for name in expected_installers("3.0.0"):
                (source / name).write_bytes(b"synthetic")
            with self.assertRaisesRegex(ValueError, "new or empty"):
                stage_application_assets(source, output, version="3.0.0")
            self.assertEqual((output / "previous-release.txt").read_text(),
                             "preserved")


if __name__ == "__main__":
    unittest.main()
