"""3.2 regression: incomplete calibration never becomes an exit-time save."""

import ast
from pathlib import Path
import unittest

from anything_plays.ui_profiles import ProfilesMixin


class FakeShutdown:
    def __init__(self, guide_open):
        self._calibration_window = object() if guide_open else None
        self.saved = ["unsaved sample"]
        self.original = ["original sample"]
        self.events = []

    def close_camera_calibration(self, *, restore):
        self.events.append(("cancel_calibration", restore))
        self.saved = self.original[:]
        self._calibration_window = None

    def persist_system_profile(self):
        self.events.append(("persist", tuple(self.saved)))


class ShutdownCalibrationTests(unittest.TestCase):
    def test_guide_cancel_precedes_persistence(self):
        app = FakeShutdown(guide_open=True)
        ProfilesMixin.persist_on_exit(app)
        self.assertEqual(
            app.events,
            [("cancel_calibration", True), ("persist", ("original sample",))],
        )

    def test_finished_guide_keeps_committed_changes(self):
        app = FakeShutdown(guide_open=False)
        ProfilesMixin.persist_on_exit(app)
        self.assertEqual(
            app.events, [("persist", ("unsaved sample",))],
        )

    def test_app_close_calls_safe_persist_not_old_persist(self):
        source = (
            Path(__file__).resolve().parents[1] / "app.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        app = next(
            cls for cls in tree.body
            if isinstance(cls, ast.ClassDef) and cls.name == "App"
        )
        close = next(
            func for func in app.body
            if isinstance(func, ast.FunctionDef) and func.name == "close"
        )
        called = {
            node.func.attr for node in ast.walk(close)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertIn("persist_on_exit", called)
        self.assertNotIn("persist_system_profile", called)


if __name__ == "__main__":
    unittest.main()
