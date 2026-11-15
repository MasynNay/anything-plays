"""Private GUI failure diagnostics must disclose no user paths or errors."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.v32_gui_failure_summary import summarize


class FrozenGuiFailureSummaryTests(unittest.TestCase):
    def test_known_source_location_and_type_without_raw_traceback(self):
        with TemporaryDirectory() as td:
            file = Path(td) / "private-report.json"
            trace = (
                "Traceback (most recent call last):\n"
                '  File "/Users/secret/repo/anything_plays/preview_setup_smoke.py", '
                'line 123, in _exercise_installed_control_archive\n'
                '  File "/Users/secret/private/irrelevant.py", line 1, in main\n'
                "RuntimeError: /Users/secret/roms/user-game.iso\n"
            )
            file.write_text(json.dumps({"passed": False, "error": trace}),
                            "utf-8")
            safe = summarize(file)
            self.assertEqual(safe["status"], "failed")
            self.assertEqual(safe["exception_class"], "RuntimeError")
            self.assertEqual(safe["source_file"], "preview_setup_smoke.py")
            self.assertEqual(safe["source_line"], 123)
            self.assertNotIn("Users/secret", json.dumps(safe))
            self.assertNotIn("roms", json.dumps(safe))

    def test_missing_invalid_or_unrecognized_report_only_returns_codes(self):
        with TemporaryDirectory() as td:
            file = Path(td) / "report.json"
            self.assertEqual(summarize(file)["status"],
                             "report_missing_or_invalid")
            file.write_text(json.dumps({"passed": False, "error":
                             "PrivateError: /secret/rom"}), "utf-8")
            report = summarize(file)
            self.assertEqual(report["exception_class"], "unavailable")
            self.assertEqual(report["source_file"], "unavailable")
            file.write_bytes(b"x" * (64 * 1024 + 1))
            self.assertEqual(summarize(file)["status"],
                             "report_missing_or_invalid")

    def test_macos_failure_path_prints_safe_summary_not_raw_native_logs(self):
        source = (
            Path(__file__).resolve().parents[1]
            / ".github/workflows/v32-private-preview-installers.yml"
        ).read_text("utf-8")
        self.assertIn("from tools.v32_gui_failure_summary import summarize", source)
        self.assertNotIn("print(task.stderr[-4000:])", source)
        self.assertNotIn("print(task.stdout[-1000:])", source)


if __name__ == "__main__":
    unittest.main()
