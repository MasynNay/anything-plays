"""Built-in camera layouts preserve calibration and console compatibility."""
import copy
import json
import unittest

from anything_plays.accessible_layouts import LAYOUTS, build_layout, layout_changes
from anything_plays.portable_profiles import parse_bundle, merge_portable_profile
from anything_plays.settings_defaults import DEFAULT
from anything_plays.system_profiles import (
    BUTTONS_BY_SYSTEM, DISABLED_MAPPING, default_for, enabled_zones,
)


class BuiltinLayoutTests(unittest.TestCase):
    def test_every_layout_round_trips_for_all_18_consoles(self):
        for system in BUTTONS_BY_SYSTEM:
            for key in LAYOUTS:
                with self.subTest(system=system, key=key):
                    original = default_for(system, DEFAULT)
                    bundle = build_layout(system, key, original)
                    profile, theme, legacy = parse_bundle(
                        json.dumps(bundle), selected_system=system)
                    self.assertFalse(legacy)
                    self.assertIsNone(theme)
                    self.assertEqual(set(profile["mapping"]),
                                     set(BUTTONS_BY_SYSTEM[system]))
                    self.assertFalse(profile["shuffle_enabled"])
                    self.assertEqual(profile, bundle["profile"])

    def test_large_layouts_have_expected_controls_and_disjoint_zones(self):
        for system in BUTTONS_BY_SYSTEM:
            for key, expected in (
                ("movement", {"Up", "Left", "Right", "Down"}),
                ("actions", {"A", "B"}),
                ("adventure", {"Up", "Left", "Right", "Down", "A", "B", "Start"}),
            ):
                profile = build_layout(system, key, default_for(system, DEFAULT))["profile"]
                active = enabled_zones(profile, system)
                self.assertEqual(set(active), expected)
                total = 0
                for index, name in enumerate(active):
                    a, b, c, d = profile["zones"][name]
                    total += (c-a)*(d-b)
                    for other in active[index+1:]:
                        e, f, g, h = profile["zones"][other]
                        self.assertFalse(max(a,e) < min(c,g) and max(b,f) < min(d,h))
                self.assertAlmostEqual(total, 1.0)

    def test_calibration_and_private_local_settings_survive_apply(self):
        original = default_for("gba", DEFAULT)
        original.update(rgb=[1, 2, 3], rgb2=[5, 6, 7], tolerance=55,
                        min_area=750, hold_frames=12, cooldown_ms=600,
                        mirror=True, color2_enabled=True, multi_fish_enabled=True,
                        camera_input_mode="Pulse (classic)", zone_image="/private/art.png")
        prior = copy.deepcopy(original)
        for key in LAYOUTS:
            bundle = build_layout("gba", key, original)
            self.assertEqual(original, prior)
            self.assertNotIn("private", json.dumps(bundle))
            applied = merge_portable_profile("gba", original, bundle["profile"])
            for field in ("rgb", "rgb2", "tolerance", "min_area", "hold_frames",
                          "cooldown_ms", "mirror", "color2_enabled", "multi_fish_enabled",
                          "camera_input_mode", "zone_image"):
                self.assertEqual(applied[field], original[field])

    def test_high_contrast_keeps_all_controls(self):
        original = default_for("gamecube", DEFAULT)
        profile = build_layout("gamecube", "contrast", original)["profile"]
        self.assertEqual(set(enabled_zones(profile, "gamecube")),
                         set(BUTTONS_BY_SYSTEM["gamecube"]))
        self.assertEqual(profile["zone_style"], "High contrast")
        self.assertEqual(profile["zone_opacity"], 100)
        self.assertGreaterEqual(profile["zone_font_size"], 50)

    def test_mirrored_layout_is_deterministic_not_a_toggle(self):
        original = default_for("snes", DEFAULT)
        first = build_layout("snes", "mirrored", original)["profile"]
        second = build_layout("snes", "mirrored", first)["profile"]
        self.assertEqual(first, second)
        for name, (x0, y0, x1, y1) in original["zones"].items():
            self.assertEqual(first["zones"][name], [1-x1, y0, 1-x0, y1])

    def test_diff_distinguishes_moved_disabled_enabled_and_remapped(self):
        before = default_for("gba", DEFAULT)
        after = copy.deepcopy(before)
        before["mapping"]["B"] = DISABLED_MAPPING
        after["mapping"]["A"] = "B"
        after["mapping"]["L"] = DISABLED_MAPPING
        after["zones"]["Right"] = [0.2, 0.2, 0.8, 0.8]
        after["shuffle_enabled"] = False
        diff = layout_changes("gba", before, after)
        self.assertEqual(diff["disabled"], ("L",))
        self.assertEqual(diff["enabled"], ("B",))
        self.assertEqual(diff["remapped"], ("A",))
        self.assertEqual(diff["moved"], ("Right",))
        self.assertTrue(diff["shuffle_changed"])

    def test_unsupported_layouts_and_consoles_are_rejected(self):
        for system, key in (("unknown", "actions"), ("gba", "unknown")):
            with self.assertRaises(ValueError):
                build_layout(system, key, {})

    def test_each_result_is_independent(self):
        original = default_for("gba", DEFAULT)
        first = build_layout("gba", "actions", original)
        first["profile"]["zones"]["A"][0] = 0.3
        second = build_layout("gba", "actions", original)
        self.assertEqual(second["profile"]["zones"]["A"], [0, 0, .5, 1])


if __name__ == "__main__":
    unittest.main()
