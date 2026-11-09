"""Negative and validation tests for isolated approved-pack simulation."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from unittest import TestCase
from unittest.mock import patch

from tools.validate_installable_core_pack import run_integration


class InstallablePackIntegrationContracts(TestCase):
    def test_only_reviewable_runtime_fixtures_are_accepted(self):
        with self.assertRaisesRegex(ValueError, "fixture not available"):
            run_integration("dolphin", Path("should-not-exist.json"))

    def test_core_download_failure_is_not_mistaken_for_install_or_success(self):
        with TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.json"
            with patch("tools.validate_installable_core_pack.fetch_core",
                       side_effect=RuntimeError("offline source")):
                self.assertFalse(run_integration("fceumm", report, seconds=2))
            data = json.loads(report.read_text())
            self.assertFalse(data["passed"])
            self.assertFalse(data["test_pack_installed"])
            self.assertFalse(data["rollback_passed"])
            self.assertIn("offline source", data["error"])


if __name__ == "__main__":
    import unittest
    unittest.main()
