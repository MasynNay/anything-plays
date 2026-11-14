"""Read-only setup diagnostics contracts, no devices or game files needed."""

import json
import unittest

from anything_plays.setup_health import build_setup_report


class SetupDiagnosticsTests(unittest.TestCase):
    def evaluate(self, **changes):
        options = dict(
            system="gba", camera_count=0, camera_selected=False,
            camera_active=False, core_found=False, controller_enabled=False,
            controller_detected=False, embedded_mode=True,
        )
        options.update(changes)
        return build_setup_report(**options)

    def test_no_camera_or_core_still_offers_keyboard(self):
        report = self.evaluate()
        self.assertIn("No camera found", report["checks"]["camera"]["status"])
        self.assertIn("keyboard", report["checks"]["camera"]["next"])
        self.assertIn("not located", report["checks"]["emulator"]["status"])
        self.assertIn("disabled", report["checks"]["controller"]["status"])

    def test_unbundled_preview_console_is_not_reported_damaged(self):
        report = self.evaluate(system="snes", preview_minimal=True)
        item = report["checks"]["emulator"]
        self.assertEqual(item["status"], "Not bundled in this 3.2 preview")
        self.assertIn("mGBA for GB, GBC and GBA", item["next"])
        self.assertNotIn("reinstall", item["next"].lower())

    def test_preview_detected_core_is_still_recognized(self):
        report = self.evaluate(
            system="snes", preview_minimal=True, core_found=True,
        )
        self.assertEqual(
            report["checks"]["emulator"]["status"], "Core file located"
        )

    def test_preview_gameboy_core_missing_is_legitimate_error(self):
        report = self.evaluate(
            system="gba", preview_minimal=True, core_found=False,
        )
        self.assertEqual(
            report["checks"]["emulator"]["status"], "Core file not located"
        )

    def test_external_preview_backend_is_not_misclassified(self):
        report = self.evaluate(
            system="gamecube", preview_minimal=True, embedded_mode=False,
        )
        self.assertEqual(
            report["checks"]["emulator"]["status"], "External emulator mode"
        )

    def test_selected_camera_explains_permissions_without_claiming_denial(self):
        report = self.evaluate(camera_count=1, camera_selected=True)
        advice = report["checks"]["camera"]["next"]
        self.assertIn("check OS privacy permissions", advice)
        self.assertNotIn("permission denied", advice.lower())

    def test_live_camera_observed_not_certified(self):
        report = self.evaluate(
            camera_count=2, camera_selected=True, camera_active=True,
        )
        self.assertIn("running", report["checks"]["camera"]["status"])
        self.assertIn("target color", report["checks"]["camera"]["next"])

    def test_controller_diagnostics_do_not_require_hardware(self):
        waiting = self.evaluate(controller_enabled=True)
        self.assertIn("Waiting", waiting["checks"]["controller"]["status"])
        detected = self.evaluate(
            controller_enabled=True, controller_detected=True,
        )
        self.assertIn("detected", detected["checks"]["controller"]["status"])
        self.assertIn("test live buttons", detected["checks"]["controller"]["next"])

    def test_external_backend_warns_in_app_mapping_may_not_work(self):
        report = self.evaluate(embedded_mode=False, core_found=True)
        self.assertIn("external", report["checks"]["input_backend"]["status"].lower())
        self.assertIn("may not reach", report["checks"]["input_backend"]["next"])
        self.assertEqual(
            report["checks"]["emulator"]["status"], "External emulator mode"
        )
        self.assertIn("not a valid readiness test",
                      report["checks"]["emulator"]["next"])

    def test_report_is_allowlisted_and_does_not_expose_private_data(self):
        report = self.evaluate(
            camera_count=100, camera_selected=True, core_found=True,
            controller_enabled=True, controller_detected=True,
        )
        self.assertEqual(set(report), {"format", "version", "console", "checks"})
        self.assertEqual(
            set(report["checks"]),
            {"camera", "emulator", "controller", "input_backend"},
        )
        encoded = json.dumps(report)
        for private in ("ROM path", "bluetooth_name", "camera_frame",
                        "user_directory", "device_serial", "/home/"):
            self.assertNotIn(private, encoded)

    def test_unknown_console_rejected(self):
        with self.assertRaisesRegex(ValueError, "supported console"):
            self.evaluate(system="../../secrets")



class FakeSetting:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value


class PrivateApp:
    """Deliberately include data no setup report may disclose."""
    def __init__(self, core_path):
        self.camera_name = FakeSetting("Private Office Webcam (device 7)")
        self.camera_options = {
            "Private Office Webcam (device 7)": 7,
        }
        self.cap = type("Capture", (), {"isOpened": lambda _self: True})()
        self.emu = type("Emulator", (), {"core_path": core_path})()
        self._gamepad = type("Reader", (), {
            "controller": object(),
            "name": "Private Bluetooth Serial 123456",
        })()
        self.gamepad_enabled = FakeSetting(True)
        self.system_key = FakeSetting("gba")

    def uses_embedded_emulator(self):
        return True


class SnapshotPrivacyTests(unittest.TestCase):
    def test_private_device_names_and_core_paths_never_enter_report(self):
        import tempfile
        from pathlib import Path
        from anything_plays.ui_setup_diagnostics import _snapshot

        with tempfile.TemporaryDirectory(prefix="private-local-core-") as d:
            core = Path(d) / "licensed-native-test.so"
            core.write_bytes(b"synthetic test only")
            app = PrivateApp(core)
            report = _snapshot(app)
        encoded = json.dumps(report)
        self.assertIn("Core file located", encoded)
        for private in (
            "Private Office Webcam", "Private Bluetooth",
            "private-local-core", "licensed-native-test.so", "device 7",
        ):
            self.assertNotIn(private, encoded)

    def test_bad_camera_driver_does_not_break_report(self):
        from anything_plays.ui_setup_diagnostics import _snapshot

        app = PrivateApp(None)
        def fail_open():
            raise OSError("private /home/alex/camera-driver")
        app.cap = type("Capture", (), {"isOpened": lambda _self: fail_open()})()
        report = _snapshot(app)
        self.assertIn(
            "not running", report["checks"]["camera"]["status"],
        )
        self.assertNotIn("/home/alex", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
