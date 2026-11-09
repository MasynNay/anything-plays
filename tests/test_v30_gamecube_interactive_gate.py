"""Real-source Dolphin playback verdict must never accept silent or static frames.

These are pure regression tests for the exact acceptance function used by the
native child probe. They are NOT a claim of physical GameCube compatibility.
"""
import unittest

from tools.probe_gamecube_homebrew import (
    evaluate_interactive_playback,
    evaluate_video_probe,
)


class SourceBuiltGameCubeAcceptance(unittest.TestCase):
    def verdict(self, **overrides):
        args = dict(
            error=None, exercise_controls=True, decoded_frames=90,
            unique_nonblank_frames=4, input_callback_calls=500,
            nonzero_input_samples=40, native_steps=1200,
            video_evidence=evaluate_video_probe(None, 90, 40, 3),
        )
        args.update(overrides)
        return evaluate_interactive_playback(**args)

    def test_actual_interactive_video_and_fps_pass(self):
        self.assertTrue(self.verdict()["playback_probe_passed"])

    def test_real_ci_failure_thousands_of_runs_no_frames_fails(self):
        report = self.verdict(
            decoded_frames=0, unique_nonblank_frames=0,
            native_steps=1232, input_callback_calls=157760,
            nonzero_input_samples=680,
            video_evidence=evaluate_video_probe(None, 0, 0, 25.121),
        )
        self.assertFalse(report["static_homebrew_interactive_passed"])
        self.assertFalse(report["playback_probe_passed"])

    def test_high_fps_but_static_frames_never_pass(self):
        report = self.verdict(unique_nonblank_frames=1)
        self.assertFalse(report["playback_probe_passed"])

    def test_fast_frames_without_input_never_pass(self):
        for changed in (
            {"exercise_controls": False},
            {"input_callback_calls": 0},
            {"nonzero_input_samples": 0},
            {"native_steps": 0},
        ):
            with self.subTest(changed=changed):
                self.assertFalse(self.verdict(**changed)["playback_probe_passed"])

    def test_changing_interactive_frames_below_minimum_fps_fail(self):
        report = self.verdict(
            video_evidence=evaluate_video_probe(None, 90, 40, 25),
        )
        self.assertTrue(report["static_homebrew_interactive_passed"])
        self.assertFalse(report["playback_probe_passed"])

    def test_native_error_never_passes(self):
        self.assertFalse(self.verdict(error="SIGSEGV")["playback_probe_passed"])


if __name__ == "__main__":
    unittest.main()
