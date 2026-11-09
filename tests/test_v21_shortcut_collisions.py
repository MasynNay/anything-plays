"""Regression tests for case-insensitive manual keyboard control mapping."""
import unittest

from anything_plays.shortcuts import button_for_key, normalize_bindings, rebind


class ShortcutCollisionTests(unittest.TestCase):
    def test_uppercase_letter_cannot_duplicate_existing_lowercase_binding(self):
        bindings = normalize_bindings("snes")
        with self.assertRaisesRegex(ValueError, "already assigned"):
            rebind("snes", bindings, "B", "Z")

    def test_saved_case_variant_collision_does_not_override_default(self):
        bindings = normalize_bindings("snes", {"B": "Z"})
        self.assertEqual(bindings["B"], "x")
        self.assertEqual(button_for_key("snes", bindings, "Z"), "A")
        self.assertEqual(button_for_key("snes", bindings, "z"), "A")

    def test_non_conflicting_uppercase_binding_is_recognized(self):
        bindings = rebind("snes", normalize_bindings("snes"), "B", "V")
        self.assertEqual(button_for_key("snes", bindings, "v"), "B")
        self.assertEqual(button_for_key("snes", bindings, "V"), "B")


if __name__ == "__main__":
    unittest.main()
