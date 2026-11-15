"""Camera calibration guidance is grounded in actual observed matches."""

import unittest

from anything_plays.calibration_metrics import (
    calibration_advice, calibration_summary,
)


class CalibrationAdviceTests(unittest.TestCase):
    def report(self, centers, zones):
        return calibration_summary(list(zip(centers, zones)))

    def test_before_color_sampling(self):
        report = self.report([(1, 1)] * 12, ["A"] * 12)
        self.assertIn("Sample", calibration_advice(report, sampled=False))

    def test_insufficient_frames(self):
        report = self.report([(1, 1)] * 4, ["A"] * 4)
        self.assertIn("8 live frames", calibration_advice(report, sampled=True))

    def test_no_target_recommends_resampling(self):
        report = self.report([None] * 20, [None] * 20)
        self.assertIn("No matching target", calibration_advice(report, sampled=True))
        self.assertIn("new", calibration_advice(report, sampled=True))

    def test_sporadic_color_matching_gets_contrast_tips(self):
        report = self.report(
            [(1, 1)] * 2 + [None] * 18, ["A"] * 2 + [None] * 18
        )
        self.assertIn("fewer than 40%", calibration_advice(report, sampled=True))
        self.assertNotIn("accuracy", calibration_advice(report, sampled=True))

    def test_detected_outside_all_zones_gets_movement_tip(self):
        report = self.report([(4, 4)] * 10, [None] * 10)
        self.assertIn("has not entered a control zone",
                      calibration_advice(report, sampled=True))

    def test_one_zone_asks_for_another(self):
        report = self.report([(4, 4)] * 10, ["A"] * 10)
        self.assertIn("another labeled zone",
                      calibration_advice(report, sampled=True))

    def test_multiple_zones_prompts_human_review_not_certification(self):
        report = self.report([(4, 4)] * 10, ["A"] * 5 + ["B"] * 5)
        msg = calibration_advice(report, sampled=True)
        self.assertIn("Review", msg)
        self.assertNotIn("accurate", msg.lower())
        self.assertNotIn("guarantee", msg.lower())


if __name__ == "__main__":
    unittest.main()
