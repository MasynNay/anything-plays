"""Dolphin full-package test must fail transparently when no core is obtained."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from tools.probe_dolphin_package import run_paired_core_experiment


class DolphinPackNativeExperimentTests(TestCase):
    def test_external_core_download_failure_does_not_claim_pack_installed(self):
        with TemporaryDirectory() as temp:
            report = Path(temp) / "report.json"
            with patch("tools.probe_dolphin_package.fetch_core",
                       side_effect=RuntimeError("original source offline")):
                self.assertFalse(run_paired_core_experiment(report, seconds=2))
            result = json.loads(report.read_text())
            self.assertFalse(result["passed"])
            self.assertFalse(result["installed_native_core_and_sys"])
            self.assertFalse(result["package_approved_for_distribution"])
            self.assertIn("original source offline", result["error"])
