"""Regression checks: a broken Tk session must never be a green QA report."""
import unittest

from anything_plays.soak_health import (
    completion_failures, stream_target_is_valid,
)


class SoakWatchdogTests(unittest.TestCase):
    def test_stream_stress_accepts_all_three_rates_but_fixed_soak_only_24(self):
        # A long stress test switches between settings and must not fail
        # merely because its last rate was not the default.
        for fps in (15, 24, 30):
            self.assertTrue(stream_target_is_valid(fps, stress_stream=True))
        self.assertTrue(stream_target_is_valid(24))
        self.assertFalse(stream_target_is_valid(15))
        self.assertFalse(stream_target_is_valid(30))
        for invalid in (None, True, 0, 60, "24", "24 FPS", [], {}):
            with self.subTest(value_type=type(invalid).__name__):
                self.assertFalse(stream_target_is_valid(invalid))
                self.assertFalse(stream_target_is_valid(
                    invalid, stress_stream=True
                ))

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
