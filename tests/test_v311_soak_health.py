"""Regression checks: a broken Tk session must never be a green QA report."""
import unittest

from anything_plays.soak_health import completion_failures


class SoakWatchdogTests(unittest.TestCase):
    def test_completed_session_with_samples_and_no_callback_error_passes(self):
        self.assertEqual(completion_failures(180, 180.08, [{"rss_mb": 100}], []), [])
        self.assertEqual(completion_failures(180, 179.3, [{"rss_mb": 100}], []), [])

    def test_unexpected_early_gui_close_is_detected(self):
        errors = completion_failures(180, 30.0, [{"rss_mb": 100}], [])
        self.assertEqual(len(errors), 1)
        self.assertIn("GUI exited early", errors[0])
        self.assertIn("30.00s", errors[0])

    def test_tk_callback_exception_always_fails_even_after_full_duration(self):
        errors = completion_failures(
            180, 180.1, [{"rss_mb": 100}],
            ["Tk callback raised RuntimeError: disconnected"],
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("RuntimeError", errors[0])

    def test_no_samples_fails_even_after_full_elapsed_time(self):
        errors = completion_failures(180, 180.5, [], [])
        self.assertIn("UI soak produced no resource samples", errors)

    def test_combined_failure_reasons_are_preserved_without_mutation(self):
        original = ["Tk callback raised ValueError: stale frame"]
        errors = completion_failures(180, 12.0, [], original)
        self.assertEqual(len(errors), 3)
        self.assertEqual(original, ["Tk callback raised ValueError: stale frame"])
        self.assertIn("GUI exited early", errors[-1])


if __name__ == "__main__":
    unittest.main()
