"""Combined 3.2 contract checks for all 18 console profiles.

These tests work without a webcam, controller, ROM, graphical display or
additional platform-specific native dependencies.
"""

import json
import unittest

from anything_plays.portable_profiles import make_bundle, parse_bundle
from anything_plays.settings_defaults import DEFAULT
from anything_plays.setup_health import build_setup_report
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM, default_for


class V32IntegrationTests(unittest.TestCase):
    def test_every_console_exports_and_imports_a_private_safe_profile(self):
        self.assertEqual(len(BUTTONS_BY_SYSTEM), 18)
        for system in BUTTONS_BY_SYSTEM:
            with self.subTest(system=system):
                profile = default_for(system, DEFAULT)
                profile["zone_image"] = "/private/local/photo.png"
                profile["rom_directory"] = "C:\\private\\game-files"
                document = make_bundle(
                    system, profile, theme="Dark",
                    allowed_themes=("Dark",),
                )
                clean, theme, legacy = parse_bundle(
                    json.dumps(document),
                    selected_system=system, allowed_themes=("Dark",),
                )
                self.assertFalse(legacy)
                self.assertEqual(theme, "Dark")
                self.assertEqual(clean["mapping"], profile["mapping"])
                self.assertEqual(clean["zones"], profile["zones"])
                serialized = json.dumps(document)
                self.assertNotIn("/private/", serialized)
                self.assertNotIn("rom_directory", serialized)
                self.assertNotIn("zone_image", serialized)

    def test_every_console_can_run_redacted_initial_checks(self):
        for system in BUTTONS_BY_SYSTEM:
            with self.subTest(system=system):
                report = build_setup_report(
                    system=system,
                    camera_count=0, camera_selected=False, camera_active=False,
                    core_found=False, controller_enabled=False,
                    controller_detected=False, embedded_mode=True,
                )
                self.assertEqual(report["console"], system)
                self.assertIn("No camera", report["checks"]["camera"]["status"])

    def test_new_user_entry_points_exist_on_composed_app(self):
        from app import App
        for name in (
            "open_calibration_wizard", "close_camera_calibration",
            "calibration_note_frame", "calibration_camera_changed",
            "open_controller_setup_guide", "open_setup_diagnostics",
            "save_profile", "load_profile", "undo_profile_import",
            "stop_controls", "close",
        ):
            with self.subTest(method=name):
                self.assertTrue(callable(getattr(App, name, None)))

    def test_profile_import_does_not_activate_camera_or_controller(self):
        import ast
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[1] /
            "anything_plays" / "portable_profiles.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        invoked = {
            node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertFalse(
            invoked & {"VideoCapture", "start_camera", "start_game",
                       "toggle_gamepad", "set_camera_buttons", "press"}
        )


if __name__ == "__main__":
    unittest.main()
