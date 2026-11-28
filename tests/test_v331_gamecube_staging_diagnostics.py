"""3.3.1 GameCube staging-memory counters are bounded, observable, and private.

No GPU, physical ROM, camera, sound device, Tk instance or real native core.
The fake OpenGL driver writes tiny RGBA buffers through the real read_frame().
"""
import ctypes as C
import gc
import weakref
from contextlib import contextmanager
import json
import threading
import unittest
from unittest.mock import Mock, patch

from anything_plays.gamecube_gpu import GameCubeHardwareSession
from anything_plays.gamecube_native_timing import GameCubeNativeTiming
from anything_plays.gamecube_preview import (
    PreviewCadenceTracker, ReadbackTimingHistogram,
)
from anything_plays.libretro_gpu_egl import EGLFrameHost
from anything_plays.libretro_gpu_portable import PortableGLFrameHost
from anything_plays.ui_setup_diagnostics import (
    _safe_gamecube_performance_report,
    _gamecube_performance_summary_lines,
)


def host_with_fake_gl(cls=EGLFrameHost):
    host = cls.__new__(cls)
    host.owner = threading.get_ident()
    host.width, host.height = 8, 8
    host.fbo = 4
    host.last_gl_error = 0
    host._readback_staging = None
    host.readback_staging_allocations = 0
    host.readback_staging_reuses = 0
    host.readback_staging_peak_bytes = 0
    transfers = []

    def gl(name, _return_type, _arg_types):
        def call(*args):
            if name == "glGetError":
                return 0
            if name == "glReadPixels":
                transfers.append(args[-1])
                args[-1][0:4] = [7, 18, 42, 255]
        return call

    host._gl = gl
    return host, transfers


def fake_session(host):
    session = GameCubeHardwareSession.__new__(GameCubeHardwareSession)
    session.host = host
    session.native_run_timing = GameCubeNativeTiming()
    session.gpu_readback_seconds = 0.0
    session.gpu_readback_max_seconds = 0.0
    session.gpu_readback_calls = 0
    session.gpu_readback_timing_samples = 0
    session.preview_clock_failures = 0
    session.hardware_frames = 0
    session.preview_readback_skips = 0
    session._readback_histogram = ReadbackTimingHistogram()
    session._preview_cadence = PreviewCadenceTracker()
    session.audio = Mock()
    session.audio.delivery_snapshot.return_value = {
        "audio_output_callback_calls": 0,
        "audio_output_requested_frames": 0,
        "audio_output_underrun_frames": 0,
        "audio_queue_dropped_frames": 0,
        "audio_output_device_underflow_callbacks": 0,
    }
    return session


class ReadbackAllocationDiagnosticsTests(unittest.TestCase):
    def test_constant_resolution_reuses_one_allocation_in_long_session(self):
        host, transfers = host_with_fake_gl()
        for _ in range(1000):
            host.read_frame(8, 8)
        self.assertEqual(host.readback_staging_allocations, 1)
        self.assertEqual(host.readback_staging_reuses, 999)
        self.assertEqual(host.readback_staging_peak_bytes, 8 * 8 * 4)
        self.assertEqual(len({id(array) for array in transfers}), 1)

    def test_downshift_and_return_to_existing_capacity_avoid_allocations(self):
        host, transfers = host_with_fake_gl()
        host.read_frame(4, 4)
        first = transfers[-1]
        host.read_frame(8, 8)
        large = transfers[-1]
        host.read_frame(3, 2)
        host.read_frame(8, 8)
        self.assertIsNot(first, large)
        self.assertIs(transfers[-1], large)
        self.assertEqual(host.readback_staging_allocations, 2)
        self.assertEqual(host.readback_staging_reuses, 2)
        self.assertEqual(host.readback_staging_peak_bytes, 256)

    def test_invalid_readback_size_never_increments_counters(self):
        host, transfers = host_with_fake_gl()
        with self.assertRaises(ValueError):
            host.read_frame(9, 8)
        self.assertEqual(host.readback_staging_allocations, 0)
        self.assertEqual(host.readback_staging_reuses, 0)
        self.assertEqual(host.readback_staging_peak_bytes, 0)
        self.assertEqual(transfers, [])

    def test_portable_gl_uses_shared_allocation_counters(self):
        host, transfers = host_with_fake_gl(PortableGLFrameHost)
        host.read_frame(8, 8)
        host.read_frame(8, 8)
        self.assertIs(transfers[0], transfers[1])
        self.assertEqual(host.readback_staging_allocations, 1)
        self.assertEqual(host.readback_staging_reuses, 1)

    def test_real_first_party_host_counters_reach_safe_setup_summary(self):
        host, _ = host_with_fake_gl()
        host.read_frame(8, 8)
        for _ in range(4):
            host.read_frame(4, 4)
        session = fake_session(host)
        report = session.performance_snapshot()
        m = report["metrics"]
        self.assertEqual(m["gpu_readback_staging_allocations"], 1)
        self.assertEqual(m["gpu_readback_staging_reuses"], 4)
        self.assertEqual(m["gpu_readback_staging_peak_bytes"], 256)
        safe = _safe_gamecube_performance_report(report)
        self.assertIsNotNone(safe)
        self.assertEqual(safe["metrics"]["gpu_readback_staging_reuses"], 4)
        lines = _gamecube_performance_summary_lines(safe)
        matching = [line for line in lines if "GPU transfer memory" in line]
        self.assertEqual(len(matching), 1)
        self.assertIn("1 allocations", matching[0])
        self.assertIn("4 reuses", matching[0])
        self.assertIn("256 bytes", matching[0])
        self.assertIn("not native GPU FPS", matching[0])
        self.assertNotIn("/Users/", json.dumps(safe))
        self.assertNotIn("PRIVATE", json.dumps(safe))

    def test_third_party_host_never_injects_paths_or_image_data(self):
        fake_host = Mock()
        fake_host.readback_staging_allocations = 123
        fake_host.readback_staging_reuses = 999
        fake_host.readback_staging_peak_bytes = 1
        fake_host.device_serial = "/Users/person/PRIVATE/driver"
        report = fake_session(fake_host).performance_snapshot()
        self.assertNotIn("gpu_readback_staging_allocations", report["metrics"])
        self.assertNotIn("/Users", json.dumps(report))
        safe = _safe_gamecube_performance_report(report)
        self.assertIsNotNone(safe)
        self.assertFalse(any("GPU transfer memory" in x
                             for x in _gamecube_performance_summary_lines(safe)))

    def test_malformed_first_party_readback_counters_are_omitted(self):
        host, _ = host_with_fake_gl()
        host.readback_staging_reuses = "PRIVATE /home/owner/usb"
        report = fake_session(host).performance_snapshot()
        self.assertNotIn("gpu_readback_staging_allocations", report["metrics"])
        self.assertNotIn("PRIVATE", json.dumps(report))
        host.readback_staging_reuses = True
        report = fake_session(host).performance_snapshot()
        self.assertNotIn("gpu_readback_staging_reuses", report["metrics"])
        host.readback_staging_reuses = 10**100
        report = fake_session(host).performance_snapshot()
        self.assertNotIn("gpu_readback_staging_peak_bytes", report["metrics"])

    def test_safe_report_rejects_impossible_capacity_and_private_values(self):
        report = fake_session(Mock()).performance_snapshot()
        report["metrics"]["gpu_readback_staging_allocations"] = 1
        report["metrics"]["gpu_readback_staging_reuses"] = 7
        report["metrics"]["gpu_readback_staging_peak_bytes"] = 4096 * 4096 * 4 + 1
        self.assertIsNone(_safe_gamecube_performance_report(report))
        report["metrics"]["gpu_readback_staging_peak_bytes"] = 512
        self.assertIsNotNone(_safe_gamecube_performance_report(report))
        report["metrics"]["gpu_readback_staging_reuses"] = "PRIVATE device path"
        self.assertIsNone(_safe_gamecube_performance_report(report))

    def test_safe_report_discards_unrecognized_images_and_private_fields(self):
        report = fake_session(Mock()).performance_snapshot()
        report["metrics"]["gpu_readback_staging_allocations"] = 0
        report["metrics"]["gpu_readback_staging_reuses"] = 0
        report["metrics"]["gpu_readback_staging_peak_bytes"] = 0
        report["metrics"]["raw_pixels"] = [18, 42, "PRIVATE /Users/test"]
        report["metrics"]["usb_serial"] = "PRIVATE serial"
        safe = _safe_gamecube_performance_report(report)
        self.assertIsNotNone(safe)
        self.assertEqual(safe["metrics"]["gpu_readback_staging_peak_bytes"], 0)
        self.assertNotIn("raw_pixels", safe["metrics"])
        self.assertNotIn("PRIVATE", json.dumps(safe))

    def test_old_report_without_new_keys_remains_valid_and_readable(self):
        report = fake_session(Mock()).performance_snapshot()
        safe = _safe_gamecube_performance_report(report)
        self.assertIsNotNone(safe)
        self.assertFalse(any("GPU transfer memory" in x
                             for x in _gamecube_performance_summary_lines(safe)))


    def test_final_report_retains_counters_without_retaining_gl_host(self):
        host, _ = host_with_fake_gl()
        host.readback_staging_allocations = 2
        host.readback_staging_reuses = 800
        host.readback_staging_peak_bytes = 256
        ref = weakref.ref(host)
        holder = [host]
        session = fake_session(None)
        session.opengl_error = None

        @contextmanager
        def context(**kwargs):
            yield holder.pop()

        session._host_factory = context
        del host
        with patch("anything_plays.gamecube_gpu.CoreSession.run"):
            session.run()
        gc.collect()
        self.assertIsNone(session.host)
        self.assertIsNone(ref())
        safe = _safe_gamecube_performance_report(session.performance_snapshot())
        self.assertIsNotNone(safe)
        self.assertEqual(safe["metrics"]["gpu_readback_staging_allocations"], 2)
        self.assertEqual(safe["metrics"]["gpu_readback_staging_reuses"], 800)
        self.assertEqual(safe["metrics"]["gpu_readback_staging_peak_bytes"], 256)

    def test_failed_native_run_preserves_available_evidence_and_original_error(self):
        host, _ = host_with_fake_gl(PortableGLFrameHost)
        host.readback_staging_allocations = 1
        host.readback_staging_reuses = 25
        host.readback_staging_peak_bytes = 128
        session = fake_session(None)
        session.opengl_error = None

        @contextmanager
        def context(**kwargs):
            yield host

        session._host_factory = context
        with patch("anything_plays.gamecube_gpu.CoreSession.run",
                   side_effect=RuntimeError("original native error")):
            with self.assertRaisesRegex(RuntimeError, "original native error"):
                session.run()
        self.assertIsNone(session.host)
        self.assertEqual(session.performance_snapshot()["metrics"][
            "gpu_readback_staging_reuses"], 25)

    def test_new_failed_context_does_not_reuse_previous_session_evidence(self):
        session = fake_session(None)
        session._final_staging_snapshot = (1, 80, 256)
        session._host_factory = Mock(side_effect=RuntimeError("context failed"))
        with self.assertRaisesRegex(RuntimeError, "context failed"):
            session.run()
        self.assertNotIn("gpu_readback_staging_allocations",
                         session.performance_snapshot()["metrics"])

    def test_untrusted_cached_staging_values_never_enter_report(self):
        session = fake_session(None)
        for bad in ((1, "PRIVATE /home/user", 256), (True, 0, 256),
                    (1, 2, 4096 * 4096 * 4 + 1), {"unsafe": "PRIVATE"}):
            session._final_staging_snapshot = bad
            report = session.performance_snapshot()
            self.assertNotIn("gpu_readback_staging_allocations", report["metrics"])
            self.assertNotIn("PRIVATE", json.dumps(report))

    def test_scheduler_clock_recovery_count_survives_sanitization(self):
        session = fake_session(None)
        report = session.performance_snapshot()
        report["metrics"]["scheduler_clock_recovery_events"] = 7
        safe = _safe_gamecube_performance_report(report)
        self.assertIsNotNone(safe)
        self.assertEqual(safe["metrics"]["scheduler_clock_recovery_events"], 7)
        for bad in (-1, True, "PRIVATE", 2**63):
            report["metrics"]["scheduler_clock_recovery_events"] = bad
            self.assertIsNone(_safe_gamecube_performance_report(report))


if __name__ == "__main__":
    unittest.main()
