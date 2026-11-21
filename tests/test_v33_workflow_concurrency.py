"""3.3 CI queue discipline: latest PR head should replace stale QA jobs.

Source-only; never executes GitHub workflows or touches the public release.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class V33WorkflowConcurrencyTests(unittest.TestCase):
    def test_3_3_build_and_long_soak_cancel_stale_pr_queues(self):
        for filename, group in (
            ("v33-private-candidate-installers.yml", "v33-candidate-build-"),
            ("v33-extended-stream-mode-soak.yml", "v33-extended-tk-stream-"),
        ):
            with self.subTest(workflow=filename):
                source = (ROOT / ".github" / "workflows" / filename).read_text(
                    encoding="utf-8"
                )
                lines = [line.strip() for line in source.splitlines()]
                expected = (
                    "group: " + group
                    + "${{ github.event.pull_request.number || github.ref }}"
                )
                self.assertIn(expected, lines)
                self.assertIn("cancel-in-progress: true", lines)
                # A changing SHA in the concurrency key defeats cancellation.
                self.assertFalse(any(
                    "head.sha" in line or "github.sha" in line
                    for line in lines if line.startswith("group: ")
                ))
                # Still test the exact reviewed PR source after scheduling.
                self.assertIn(
                    "github.event.pull_request.head.sha || github.sha", source
                )
                self.assertIn("persist-credentials: false", source)

    def test_private_installer_gate_keeps_all_four_platforms_and_no_release(self):
        source = (ROOT / ".github" / "workflows"
                  / "v33-private-candidate-installers.yml").read_text(
                      encoding="utf-8"
                  )
        for marker in ("target: linux-x64", "target: windows-x64",
                       "target: macos-arm64", "target: macos-x64",
                       "AP_RELEASE_BUILD: \"0\"",
                       "v33_full_native_link",
                       "test_v33_workflow_concurrency.py"):
            self.assertIn(marker, source)
        self.assertNotIn("gh release create", source)
        self.assertNotIn("git push", source)


if __name__ == "__main__":
    unittest.main()
