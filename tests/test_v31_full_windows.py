"""Prevent false approval or unsafe Windows native DLL use in 3.1 QA."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.assemble_v31_full_windows import (
    STABLE, PREVIEW, FULL, SOURCE_REVISION, check_inputs, hash_file,
)


class WindowsFullReleaseCandidateTests(unittest.TestCase):
    def test_stable_and_preview_installers_have_distinct_names(self):
        self.assertEqual(STABLE, "AnythingPlaysSetup-3.0.0.exe")
        self.assertEqual(PREVIEW, "AnythingPlaysSetup-3.1.0-preview1.exe")
        self.assertEqual(FULL, "AnythingPlaysSetup-3.1.0-preview2.exe")
        self.assertNotEqual(FULL, PREVIEW)

    def test_hash_and_source_commit_guard_fail_on_tampering(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            stable = root / STABLE
            preview = root / PREVIEW
            stable.write_bytes(b"stable test")
            preview.write_bytes(b"preview test")
            checks = root / "SHA256SUMS.txt"
            checks.write_text(f"{hash_file(stable)}  {STABLE}\n", "utf-8")
            receipt = root / "PREVIEW1_RECEIPT.json"
            receipt.write_text(json.dumps({
                "target": "windows-x64",
                "installer": PREVIEW,
                "sha256": hash_file(preview),
                "source_revision": SOURCE_REVISION,
            }), "utf-8")
            self.assertEqual(
                check_inputs(stable, preview, checks, receipt),
                hash_file(stable),
            )
            preview.write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                check_inputs(stable, preview, checks, receipt)

    def test_real_installer_is_inspected_in_isolated_native_process(self):
        script = (Path(__file__).resolve().parents[1] /
                  "tools/assemble_v31_full_windows.py").read_text("utf-8")
        # If the native DLL is mapped in the parent process, Windows
        # cannot delete it from TemporaryDirectory; the build will fail.
        self.assertIn("str(installed)],", script)
        self.assertIn("check_native=True)", script)
        self.assertIn("check=True, cwd=root, timeout=120", script)
        self.assertIn("verify_bundle(installed, \"windows\", check_native=False)", script)

    def test_ci_only_retains_qa_artifacts(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/v31-full-windows-qa.yml").read_text("utf-8")
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("retention-days: 7", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("gh release create", workflow)


if __name__ == "__main__":
    unittest.main()
