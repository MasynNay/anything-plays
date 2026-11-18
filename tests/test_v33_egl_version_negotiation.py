"""3.3 Linux EGL may not grant a newer OpenGL context than it owns.

These real ctypes handshake tests never initialize GPU hardware or run ROMs.
"""
import ctypes as C
import threading
import unittest

from anything_plays.libretro_gpu_egl import (
    EGLFrameHost, GET_FBO, GET_PROC, HardwareRenderCallback,
)


class EGLContextVersionNegotiationTests(unittest.TestCase):
    @staticmethod
    def make_host(version):
        host = EGLFrameHost.__new__(EGLFrameHost)
        host.owner = threading.get_ident()
        host.opengl_version = version
        host.fbo = 79
        host.core_reset = None
        host.core_destroy = None
        host._fbo_callback = GET_FBO(lambda: host.fbo)
        host._proc_callback = GET_PROC(lambda name: 0x1234)
        return host

    @staticmethod
    def request(major, minor):
        callback = HardwareRenderCallback()
        callback.context_type = 3
        callback.version_major = major
        callback.version_minor = minor
        callback.context_reset = 1234
        callback.context_destroy = 5678
        return callback

    def test_egl_33_driver_must_reject_41_or_45_native_dolphin_request(self):
        host = self.make_host("3.3 (Core Profile) Mesa 24.1")
        for requested in ((4, 1), (4, 5)):
            with self.subTest(requested=requested):
                callback = self.request(*requested)
                self.assertFalse(
                    host.accept_core_render(C.addressof(callback))
                )
                self.assertFalse(callback.get_current_framebuffer)
                self.assertFalse(callback.get_proc_address)
                self.assertIsNone(host.core_reset)
                self.assertIsNone(host.core_destroy)

    def test_driver_with_exact_gl33_accepts_supported_dolphin_request(self):
        host = self.make_host("3.3 Mesa 24.3.4")
        callback = self.request(3, 3)
        self.assertTrue(host.accept_core_render(C.addressof(callback)))
        self.assertEqual(host.core_reset, 1234)
        self.assertEqual(host.core_destroy, 5678)
        self.assertTrue(callback.get_current_framebuffer)
        self.assertTrue(callback.get_proc_address)

    def test_egl_41_driver_accepts_33_but_rejects_45(self):
        host = self.make_host("4.1 INTEL-17")
        accepted = self.request(3, 3)
        self.assertTrue(host.accept_core_render(C.addressof(accepted)))
        rejected = self.request(4, 5)
        self.assertFalse(host.accept_core_render(C.addressof(rejected)))
        self.assertFalse(rejected.get_current_framebuffer)
        self.assertFalse(rejected.get_proc_address)

    def test_egl_45_driver_accepts_45_core_request(self):
        host = self.make_host("4.5 (Core Profile) Mesa 24.3")
        callback = self.request(4, 5)
        self.assertTrue(host.accept_core_render(C.addressof(callback)))
        self.assertTrue(callback.get_current_framebuffer)
        self.assertTrue(callback.get_proc_address)

    def test_existing_45_core_request_ceiling_remains_enforced(self):
        host = self.make_host("4.6 Mesa 25")
        rejected = self.request(4, 6)
        self.assertFalse(host.accept_core_render(C.addressof(rejected)))
        self.assertFalse(rejected.get_current_framebuffer)
        accepted = self.request(4, 5)
        self.assertTrue(host.accept_core_render(C.addressof(accepted)))

    def test_missing_malformed_or_es_version_never_approves_context(self):
        for invalid in ("", "private-driver", "OpenGL ES 3.2", "3.x Mesa"):
            with self.subTest(gl_version=invalid):
                host = self.make_host(invalid)
                callback = self.request(3, 3)
                self.assertFalse(host.accept_core_render(C.addressof(callback)))
                self.assertIsNone(host.core_reset)
                self.assertFalse(callback.get_current_framebuffer)


if __name__ == "__main__":
    unittest.main()
