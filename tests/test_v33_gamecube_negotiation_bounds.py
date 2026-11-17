"""Bound native GameCube HW context negotiation diagnostics.

These tests use an actual ctypes render request but no Dolphin core, ROM,
GPU, camera, controller or sound card.
"""
import ctypes as C
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

    def test_no_callback_pointer_does_not_grow_handshake_history(self):
        session = self.make_session()
        with patch("builtins.print") as logging:
            self.assertFalse(session.environment(14, None))
        self.assertEqual(session.hardware_requests, [])
        self.assertEqual(session.hardware_negotiations_total, 0)
        logging.assert_not_called()


if __name__ == "__main__":
    unittest.main()
