"""Controller onboarding state tests, with no real HID or SDL requirements."""

import unittest

from anything_plays.controller_onboarding import setup_guidance


class ControllerOnboardingTests(unittest.TestCase):
    def guidance(self, **overrides):
        state = {
            "enabled": False, "connected": False, "focused": False,
            "pressed_count": 0, "embedded": True,
        }
        state.update(overrides)
        return setup_guidance(**state)

    def test_off_is_safe_and_never_promises_connected(self):
        step, help_text = self.guidance(connected=True, pressed_count=1)
        self.assertIn("Enable", step)
        self.assertNotIn("connected.", help_text)
        self.assertIn("camera controls", help_text)

    def test_scanned_but_disconnected_has_recovery_path(self):
        step, help_text = self.guidance(enabled=True, focused=True)
        self.assertIn("Waiting", step)
        self.assertIn("Rescan", help_text)
        self.assertIn("keyboard", help_text)

    def test_focus_loss_is_explicit(self):
        step, help_text = self.guidance(
            enabled=True, connected=True, pressed_count=1,
        )
        self.assertIn("Focus", step)
        self.assertIn("released", help_text)

    def test_external_backend_is_not_claimed_supported(self):
        step, help_text = self.guidance(
            enabled=True, connected=True, focused=True,
            pressed_count=4, embedded=False,
        )
        self.assertIn("backend", step)
        self.assertIn("does not accept", help_text)

    def test_connected_with_no_input_is_not_misreported_as_tested(self):
        step, help_text = self.guidance(
            enabled=True, connected=True, focused=True,
        )
        self.assertIn("Test a button", step)
        self.assertIn("Press", help_text)

    def test_live_activity_changes_status_only_for_embedded_backend(self):
        step, help_text = self.guidance(
            enabled=True, connected=True, focused=True,
            pressed_count=2,
        )
        self.assertIn("Input detected", step)
        self.assertIn("Button mapping", help_text)


if __name__ == "__main__":
    unittest.main()
