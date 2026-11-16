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
        item = report["checks"]["emulator"]
        self.assertEqual(item["status"], "Preview mGBA emulator file missing")
        self.assertIn("GB, GBC and GBA", item["next"])
        self.assertIn("Stable 3.1.1 is installed separately", item["next"])
        self.assertNotIn("Not bundled", item["status"])
        self.assertNotIn("reinstall Anything Plays 3.0", item["next"])

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
    def test_live_core_rescan_updates_without_restarting_emulator(self):
        import tempfile
        from pathlib import Path
        from anything_plays.ui_setup_diagnostics import _snapshot

        with tempfile.TemporaryDirectory(prefix="private-core-refresh-") as home:
            newly_installed = Path(home) / "newly-added-core.so"
            app = PrivateApp(None)
            app.emu.find_system_core = lambda: (
                newly_installed if newly_installed.is_file() else None
            )
            before = _snapshot(app)
            self.assertEqual(
                before["checks"]["emulator"]["status"],
                "Core file not located",
            )
            newly_installed.write_bytes(b"synthetic test only")
            after = _snapshot(app)
            self.assertEqual(
                after["checks"]["emulator"]["status"], "Core file located",
            )
            self.assertIsNone(app.emu.core_path, "Read-only checks must not mutate core")
            self.assertNotIn(str(newly_installed), json.dumps(after))
            newly_installed.unlink()
            removed = _snapshot(app)
            self.assertEqual(
                removed["checks"]["emulator"]["status"],
                "Core file not located",
            )

    def test_stale_cached_core_from_another_console_is_not_reported_ready(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from anything_plays.ui_setup_diagnostics import _snapshot

        with tempfile.TemporaryDirectory(prefix="private-core-stale-") as home:
            previous_core = Path(home) / "old-gameboy-core.so"
            previous_core.write_bytes(b"synthetic test only")
            app = PrivateApp(previous_core)
            app.system_key = FakeSetting("snes")
            app.emu.find_system_core = lambda: None
            with patch(
                "anything_plays.ui_setup_diagnostics.current_identity",
                return_value={"channel": "v32_preview"},
            ):
                report = _snapshot(app)
            self.assertEqual(
                report["checks"]["emulator"]["status"],
                "Not bundled in this 3.2 preview",
            )
            self.assertNotIn(str(previous_core), json.dumps(report))
            self.assertEqual(app.emu.core_path, previous_core)

    def test_core_discovery_error_is_redacted_and_does_not_open_devices(self):
        from anything_plays.ui_setup_diagnostics import _snapshot
        app = PrivateApp(None)
        def failed_lookup():
            raise OSError("Private home path /home/user/my-core.so")
        app.emu.find_system_core = failed_lookup
        report = _snapshot(app)
        self.assertEqual(
            report["checks"]["emulator"]["status"],
            "Core file not located",
        )
        self.assertNotIn("/home/user", json.dumps(report))

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

    def test_stream_mode_aggregate_report_is_private_and_distinguishes_static_frames(self):
        from anything_plays.ui_stream import StreamCadenceTracker, StreamMixin
        from anything_plays.ui_setup_diagnostics import (
            _snapshot, _stream_cadence_summary_lines,
        )

        class StreamHarness(PrivateApp, StreamMixin):
            pass

        app = StreamHarness("/home/private/secret-emulator.so")
        app._stream_output_window = object()
        app._stream_cadence = StreamCadenceTracker()
        app._stream_cadence.record_tick(
            1.0, "24 FPS", published=True, render_seconds=0.012
        )
        app._stream_cadence.record_tick(
            1.04, "24 FPS", published=False, render_seconds=0.055
        )
        report = _snapshot(app)
        self.assertIn("stream_cadence", report)
        lines = _stream_cadence_summary_lines(report["stream_cadence"])
        self.assertEqual(len(lines), 5)
        self.assertIn("Source resize cache: not measured", lines[4])
        self.assertIn("Requested Stream Mode refresh: 24 FPS", lines[0])
        self.assertIn("observed Tk tick 25.0 FPS", lines[0])
        self.assertIn("waiting for two changed images", lines[1])
        self.assertIn("1 unchanged ticks", lines[1])
        self.assertIn("Stream composition: P95 50–67 ms", lines[3])
        self.assertIn("1 over-budget of 2 measured ticks", lines[3])
        self.assertEqual(
            report["stream_cadence"]["metrics"]["stream_render_samples"], 2
        )
        # A real active Stream Mode supplies only aggregate hit/miss counts.
        from PIL import Image
        from anything_plays.ui_stream import StreamPanelResizeCache
        cache = StreamPanelResizeCache()
        pixels = Image.new("RGB", (32, 24), "#112233")
        cache.contained("CAMERA", pixels, (0, 0, 160, 120))
        cache.contained("CAMERA", pixels, (0, 0, 160, 120))
        app._stream_resize_cache = cache
        report = _snapshot(app)
        metrics = report["stream_cadence"]["metrics"]
        self.assertEqual(metrics["stream_resize_cache_hits"], 1)
        self.assertEqual(metrics["stream_resize_cache_misses"], 1)
        self.assertIn(
            "1 reused · 1 resized",
            _stream_cadence_summary_lines(report["stream_cadence"])[4],
        )
        self.assertNotIn("112233", json.dumps(report))
        self.assertNotIn("/home/private", json.dumps(report))
        # Old reports remain legible without the new timing fields.
        old = {"metrics": {
            key: value for key, value in report["stream_cadence"]["metrics"].items()
            if not key.startswith("stream_render_")
        }}
        self.assertIn(
            "P95 not sampled", _stream_cadence_summary_lines(old)[3]
        )
        app._stream_output_window = None
        self.assertNotIn("stream_cadence", _snapshot(app))

    def test_input_timing_display_has_three_stage_ranges_or_no_samples(self):
        from anything_plays.libretro_input import InputBuffer
        from anything_plays.ui_setup_diagnostics import _input_timing_summary_lines

        inputs = InputBuffer()
        inputs.enable_latency_probe(clock=iter((10.013, 10.040)).__next__)
        empty = _input_timing_summary_lines(inputs.latency_snapshot())
        self.assertEqual(len(empty), 1)
        self.assertIn("No software input samples", empty[0])
        self.assertNotIn("None ms", empty[0])

        inputs.set_camera_buttons(["A"], sample_started_at=10.0)
        inputs.before_frame(armed=True)
        lines = _input_timing_summary_lines(inputs.latency_snapshot())
        self.assertEqual(len(lines), 3)
        self.assertIn("Tracking", lines[0])
        self.assertIn("input buffer", lines[0])
        self.assertIn("native frame", lines[1])
        self.assertIn("Combined software", lines[2])
        self.assertIn("P50 33-50 ms", lines[2])
        self.assertIn("P95 33-50 ms", lines[2])

    def test_opt_in_timing_report_contains_only_bounded_aggregate_buckets(self):
        from anything_plays.libretro_input import InputBuffer
        from anything_plays.ui_setup_diagnostics import _snapshot

        app = PrivateApp("/home/alex/secret/core.so")
        inputs = InputBuffer()
        app.emu.inputs = inputs
        self.assertNotIn("input_latency", _snapshot(app))
        inputs.enable_latency_probe(clock=iter((10.013, 10.040)).__next__)
        inputs.set_camera_buttons(["A"], ["B"], sample_started_at=10.0)
        inputs.before_frame(armed=True)
        report = _snapshot(app)
        timing = report["input_latency"]
        self.assertTrue(timing["enabled"])
        self.assertEqual(timing["samples"], 1)
        self.assertEqual(
            timing["stages"]["tracking_to_native"]["p95_bucket_ms"],
            "33-50",
        )
        encoded = json.dumps(report)
        for private in (
            "/home/alex", "secret", "Office Webcam",
            "Bluetooth Serial", "camera_frame", "ROM",
        ):
            self.assertNotIn(private, encoded)
        # A public aggregate count named discarded_pending is expected;
        # only the internal raw pending timestamp must be absent.
        self.assertNotIn("_pending", timing)
        self.assertEqual(timing["discarded_pending"], 0)
        self.assertNotIn("10.013", encoded)
        self.assertNotIn("10.040", encoded)
        inputs.disable_latency_probe()
        stopped = _snapshot(app)["input_latency"]
        self.assertFalse(stopped["enabled"])
        self.assertEqual(stopped["samples"], 1)

    def test_embedded_gamecube_shows_safe_live_performance_only(self):
        from anything_plays.gba_emulator import Emulator
        from anything_plays.gamecube_gpu import GameCubeHardwareSession
        from anything_plays.gamecube_native_timing import GameCubeNativeTiming
        from anything_plays.ui_setup_diagnostics import (
            _gamecube_performance_summary_lines, _snapshot,
        )

        session = object.__new__(GameCubeHardwareSession)
        session.native_run_timing = GameCubeNativeTiming()
        session.native_run_timing.record_native_run(.05)
        session.gpu_readback_seconds = .002
        session.gpu_readback_max_seconds = .002
        session.gpu_readback_calls = 1
        session.hardware_frames = 1
        session.preview_readback_skips = 0
        from unittest.mock import Mock
        session.audio = Mock(delivery_snapshot=Mock(return_value={
            "audio_output_callback_calls": 10,
            "audio_output_requested_frames": 1000,
            "audio_output_underrun_frames": 80,
            "audio_output_device_underflow_callbacks": 2,
            "audio_queue_dropped_frames": 0,
        }))
        session.rom = "/home/private/secret-disc.iso"
        session.host = Mock(serial_number="private-GPU-1234")

        app = PrivateApp("/home/private/secret-core.so")
        app.system_key = FakeSetting("gamecube")
        emu = object.__new__(Emulator)
        emu.system = "gamecube"
        emu.core_path = None
        emu.find_system_core = lambda: None
        emu._gamecube_session = session
        emu._gamecube_last_performance = None
        app.emu = emu
        report = _snapshot(app)
        performance = report["gamecube_performance"]
        lines = _gamecube_performance_summary_lines(performance)
        self.assertEqual(len(lines), 5)
        self.assertIn("Native frames: 1", lines[0])
        self.assertIn("P95 33–50 ms", lines[0])
        # Previously saved 3.2/early 3.3 snapshots remain readable.
        code = performance["metrics"].pop("native_run_p95_bucket_code")
        legacy = _gamecube_performance_summary_lines(performance)
        self.assertIn("P95 not sampled", legacy[0])
        performance["metrics"]["native_run_p95_bucket_code"] = code
        # Older session reports may not carry the new readback clock fields.
        timed = performance["metrics"].pop("gpu_readback_timing_samples")
        faults = performance["metrics"].pop("gamecube_preview_clock_failures")
        previous = _gamecube_performance_summary_lines(performance)
        self.assertNotIn("invalid clock reads", previous[1])
        performance["metrics"]["gpu_readback_timing_samples"] = timed
        performance["metrics"]["gamecube_preview_clock_failures"] = faults
        self.assertIn("GPU readback", lines[1])
        self.assertIn("timed 0 of 1 captures", lines[1])
        self.assertIn("0 invalid clock reads", lines[1])
        self.assertIn("Preview captures", lines[2])
        self.assertIn("waiting for two published preview images", lines[2])
        self.assertNotIn("observed 0.0 FPS", lines[2])
        self.assertIn("Late deadlines", lines[3])
        self.assertIn("Audio", lines[4])
        text = json.dumps(report)
        for private in ("secret-disc.iso", "secret-core.so", "private-GPU",
                        "/home/", "serial_number", "rom_path"):
            self.assertNotIn(private, text)
        performance["metrics"].update({
            "gamecube_preview_target_fps": 30,
            "gamecube_preview_observed_capture_fps": 28.57,
            "gamecube_preview_cadence_intervals": 2,
            "gamecube_preview_max_interval_ms": 35.0,
        })
        measured = _gamecube_performance_summary_lines(performance)
        self.assertIn("target 30 FPS", measured[2])
        self.assertIn("observed 28.57 FPS", measured[2])
        emu._gamecube_session = None
        emu._gamecube_last_performance = performance
        self.assertEqual(_snapshot(app)["gamecube_performance"], performance)
        app.system_key = FakeSetting("gba")
        self.assertNotIn("gamecube_performance", _snapshot(app))

    def test_refresh_error_message_never_echoes_private_driver_details(self):
        from anything_plays.ui_setup_diagnostics import (
            _safe_refresh_failure_message,
        )
        import tkinter as tk

        for failure in (
            ValueError("ROM /home/owner/private/game.iso could not be opened"),
            tk.TclError("Private Webcam USB serial 45345 not found"),
            OSError("Driver /Users/person/Library/secret-device.dat"),
        ):
            with self.subTest(error=type(failure).__name__):
                message = _safe_refresh_failure_message(failure)
                self.assertIn("Unable to check current setup", message)
                for private in ("/home/", "/Users/", "USB serial",
                                "game.iso", "secret-device", "45345"):
                    self.assertNotIn(private, message)
                self.assertLess(len(message), 140)

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
