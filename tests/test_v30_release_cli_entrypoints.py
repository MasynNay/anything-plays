"""Release workflows must execute their Python tooling without import errors."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReleaseWorkflowEntrypointTests(unittest.TestCase):
    def test_all_release_tool_modules_have_working_cli(self):
        for module in (
            "tools.collect_v30_production_assets",
            "tools.stage_v30_release_assets",
            "tools.create_v30_candidate_lock",
        ):
            with self.subTest(module=module):
                result = subprocess.run(
                    [sys.executable, "-m", module, "--help"],
                    cwd=ROOT, capture_output=True, text=True, timeout=15,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.lower())

    def test_actions_call_importable_modules_not_directly_executed_scripts(self):
        for workflow, modules in (
            (".github/workflows/v30-publish-approved.yml", (
                "tools.collect_v30_production_assets",
                "tools.stage_v30_release_assets",
            )),
            (".github/workflows/v30-freeze-inputs.yml", (
                "tools.create_v30_candidate_lock",
            )),
        ):
            source = (ROOT / workflow).read_text("utf-8")
            for module in modules:
                with self.subTest(workflow=workflow, module=module):
                    self.assertIn("python -m " + module, source)
                    self.assertNotIn("python " + module.replace(".", "/") + ".py", source)


if __name__ == "__main__":
    unittest.main()
