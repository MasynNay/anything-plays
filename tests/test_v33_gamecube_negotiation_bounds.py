"""Bound native GameCube HW context negotiation diagnostics.

These tests use an actual ctypes render request but no Dolphin core, ROM,
GPU, camera, controller or sound card.
"""
import ctypes as C
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from anything_plays.gamecube_gpu import (
    GameCubeHardwareSession, MAX_GPU_NEGOTIATION_RECORDS,
)
from anything_plays.libretro_gpu_egl import HardwareRenderCallback


class GameCubeNegotiationBoundsTests(unittest.TestCase):
    @staticmethod
    def make_session():
        session = object.__new__(GameCubeHardwareSession)
        session.hardware_requests = []
        session.hardware_negotiations_total = 0
        session.opengl_error = None
        session.emulator = SimpleNamespace(stop_event=threading.Event())
        session.host = Mock()
        session.host.accept_core_render.return_value = True
        return session

    def test_repeated_native_handshakes_have_fixed_memory_and_log_budget(self):
        session = self.make_session()
        request = HardwareRenderCallback()
        request.context_type = 3
        request.version_major = 3
        request.version_minor = 3
        request.context_reset = 7
        address = C.addressof(request)
        with patch("builtins.print") as logging:
            for i in range(10_000):
                request.version_minor = i % 10
                self.assertTrue(session.environment(14, address))
        self.assertEqual(session.hardware_negotiations_total, 10_000)
        self.assertEqual(len(session.hardware_requests), MAX_GPU_NEGOTIATION_RECORDS)
        self.assertEqual(
            [r["version"][1] for r in session.hardware_requests],
            [i % 10 for i in range(10_000 - MAX_GPU_NEGOTIATION_RECORDS, 10_000)],
        )
        self.assertTrue(all(r["granted"] for r in session.hardware_requests))
        self.assertEqual(logging.call_count, MAX_GPU_NEGOTIATION_RECORDS)
        self.assertEqual(session.host.accept_core_render.call_count, 10_000)

    def test_latest_rejection_is_retained_after_record_budget(self):
        session = self.make_session()
        req = HardwareRenderCallback()
        req.context_type = 3
        req.version_major = 4
        req.version_minor = 1
        req.context_reset = 77
        with patch("builtins.print") as logging:
            for _ in range(MAX_GPU_NEGOTIATION_RECORDS):
                self.assertTrue(session.environment(14, C.addressof(req)))
            session.host.accept_core_render.return_value = False
            self.assertFalse(session.environment(14, C.addressof(req)))
        self.assertEqual(len(session.hardware_requests), MAX_GPU_NEGOTIATION_RECORDS)
        self.assertEqual(session.hardware_negotiations_total,
                         MAX_GPU_NEGOTIATION_RECORDS + 1)
        self.assertFalse(session.hardware_requests[-1]["granted"])
        self.assertEqual(session.hardware_requests[-1]["version"], [4, 1])
        self.assertEqual(logging.call_count, MAX_GPU_NEGOTIATION_RECORDS)

    def test_closed_stdout_does_not_change_native_context_acceptance(self):
        session = self.make_session()
        request = HardwareRenderCallback()
        request.context_type = 3
        request.version_major = 3
        request.version_minor = 3
        request.context_reset = 8
        address = C.addressof(request)
        # A closed stdout can trigger either BrokenPipeError on a pipe
        # or ValueError on a closed TextIOWrapper. Neither must change
        # Libretro's HW negotiation result.
        for index, failure in enumerate((
            BrokenPipeError("output closed"),
            ValueError("I/O operation on closed file"),
        )):
            with self.subTest(failure=type(failure).__name__):
                session.host.accept_core_render.return_value = index == 0
                with patch("builtins.print", side_effect=failure):
                    self.assertEqual(session.environment(14, address), index == 0)
                self.assertEqual(session.hardware_requests[-1]["granted"],
                                 index == 0)
        self.assertEqual(session.hardware_negotiations_total, 2)
        self.assertEqual(session.host.accept_core_render.call_count, 2)

    def test_closed_stdout_after_log_budget_is_not_used_again(self):
        session = self.make_session()
        request = HardwareRenderCallback()
        request.context_type = 3
        request.version_major = 3
        request.version_minor = 3
        request.context_reset = 5
        with patch("builtins.print"):
            for _ in range(MAX_GPU_NEGOTIATION_RECORDS):
                self.assertTrue(session.environment(14, C.addressof(request)))
        with patch("builtins.print", side_effect=OSError("stdout lost")) as log:
            self.assertTrue(session.environment(14, C.addressof(request)))
        log.assert_not_called()
        self.assertEqual(session.hardware_negotiations_total,
                         MAX_GPU_NEGOTIATION_RECORDS + 1)
        self.assertEqual(len(session.hardware_requests), MAX_GPU_NEGOTIATION_RECORDS)

    def test_gpu_host_exception_rejects_and_stops_without_driver_text(self):
        """Driver/proc failures cannot escape native ctypes callbacks."""
        for failure in (
            OSError("PRIVATE GPU DRIVER /home/user/driver-token"),
            RuntimeError("PRIVATE WGL 33 vendor serial"),
            AttributeError("PRIVATE proc-loader identifier"),
        ):
            with self.subTest(error=type(failure).__name__):
                session = self.make_session()
                callback = HardwareRenderCallback()
                callback.context_type = 3
                callback.version_major = 3
                callback.version_minor = 3
                callback.context_reset = 123
                session.host.accept_core_render.side_effect = failure
                with patch("builtins.print") as logging:
                    self.assertFalse(
                        session.environment(14, C.addressof(callback))
                    )
                self.assertTrue(session.emulator.stop_event.is_set())
                self.assertEqual(
                    session.opengl_error, "GPU hardware context negotiation failed"
                )
                self.assertEqual(session.hardware_negotiations_total, 1)
                self.assertEqual(len(session.hardware_requests), 1)
                self.assertFalse(session.hardware_requests[0]["granted"])
                self.assertEqual(session.host.accept_core_render.call_count, 1)
                logging.assert_called_once()
                self.assertNotIn("PRIVATE", repr(session.hardware_requests))
                self.assertNotIn("PRIVATE", session.opengl_error)

    def test_native_context_rejection_without_driver_error_is_not_fatal(self):
        session = self.make_session()
        callback = HardwareRenderCallback()
        callback.context_type = 3
        callback.version_major = 3
        callback.version_minor = 3
        callback.context_reset = 123
        session.host.accept_core_render.return_value = False
        with patch("builtins.print"):
            self.assertFalse(session.environment(14, C.addressof(callback)))
        self.assertIsNone(session.opengl_error)
        self.assertFalse(session.emulator.stop_event.is_set())
        self.assertFalse(session.hardware_requests[-1]["granted"])

    def test_preserves_existing_graphics_failure_category_on_native_exception(self):
        session = self.make_session()
        session.opengl_error = "GPU readback failed (OSError)"
        session.host.accept_core_render.side_effect = OSError("PRIVATE /dev/nvidia0")
        callback = HardwareRenderCallback()
        callback.context_type = 3
        callback.version_major = 3
        callback.version_minor = 3
        callback.context_reset = 123
        with patch("builtins.print"):
            self.assertFalse(session.environment(14, C.addressof(callback)))
        self.assertEqual(session.opengl_error, "GPU readback failed (OSError)")
        self.assertTrue(session.emulator.stop_event.is_set())

    def test_no_callback_pointer_does_not_grow_handshake_history(self):
        session = self.make_session()
        session.host.accept_core_render.return_value = False
        with patch("builtins.print") as logging:
            self.assertFalse(session.environment(14, None))
        self.assertEqual(session.hardware_requests, [])
        self.assertEqual(session.hardware_negotiations_total, 0)
        logging.assert_not_called()


if __name__ == "__main__":
    unittest.main()
