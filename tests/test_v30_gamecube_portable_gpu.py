"""Portable GameCube OpenGL contracts without a display or commercial game."""
import ctypes as C
import threading
from unittest import TestCase
from unittest.mock import Mock, patch
from anything_plays.libretro_gpu_portable import (
    PortableGLFrameHost, choose_gamecube_gpu_host,
)
from anything_plays.libretro_gpu_egl import (
    EGLFrameHost, HardwareRenderCallback,
)


class PortableGameCubeHostTests(TestCase):
    def test_shared_framebuffer_reader_rejects_silent_gl_error(self):
        # EGL, WGL and CGL all share this readback method. The GL driver may
        # set an error flag instead of raising an exception from ctypes.
        host = EGLFrameHost.__new__(EGLFrameHost)
        host.owner = threading.get_ident()
        host.width = host.height = 4
        host.fbo = 7
        calls = []
        readback_errors = [0, 0x0506]

        def gl(name, _result, _arguments):
            def call(*args):
                calls.append(name)
                if name == "glGetError":
                    return readback_errors.pop(0)
                return None
            return call

        host._gl = gl
        with self.assertRaisesRegex(RuntimeError, "GPU readback OpenGL error"):
            host.read_frame(4, 4)
        self.assertEqual(host.last_gl_error, 0x0506)
        self.assertIn("glReadPixels", calls)
        self.assertIn("glBindFramebuffer", calls)
        self.assertEqual(calls[-1], "glGetError")

    def test_old_gl_error_does_not_invalidate_successful_readback(self):
        # An unrelated stale error from an earlier Dolphin render should be
        # drained, while a new error from glReadPixels remains fatal.
        host = EGLFrameHost.__new__(EGLFrameHost)
        host.owner = threading.get_ident()
        host.width = host.height = 2
        host.fbo = 11
        errors = [0x0502, 0, 0]
        calls = []

        def gl(name, _result, _arguments):
            def call(*args):
                calls.append(name)
                if name == "glGetError":
                    return errors.pop(0)
                return None
            return call

        host._gl = gl
        frame = host.read_frame(2, 2)
        self.assertEqual(frame.shape, (2, 2, 3))
        self.assertEqual(host.last_gl_error, 0)
        self.assertIn("glReadPixels", calls)
        self.assertEqual(errors, [])

    def test_shared_framebuffer_reader_accepts_successful_gl_readback(self):
        host = EGLFrameHost.__new__(EGLFrameHost)
        host.owner = threading.get_ident()
        host.width = 4
        host.height = 3
        host.fbo = 2

        def gl(name, _result, _arguments):
            def call(*args):
                if name == "glGetError":
                    return 0
                if name == "glReadPixels":
                    # ctypes still receives an independently owned RGBA
                    # buffer; fill a native pixel without touching any GPU.
                    destination = args[-1]
                    destination[0:4] = [15, 33, 47, 255]
            return call

        host._gl = gl
        frame = host.read_frame(4, 3, flip_vertical=False)
        self.assertEqual(frame.shape, (3, 4, 3))
        self.assertEqual(frame.dtype.name, "uint8")
        self.assertEqual(frame[0, 0].tolist(), [15, 33, 47])
        self.assertEqual(host.last_gl_error, 0)

    def test_selects_proven_egl_for_linux(self):
        with patch("anything_plays.libretro_gpu_portable.sys.platform", "linux"):
            self.assertIs(choose_gamecube_gpu_host(), EGLFrameHost)

    def test_selects_portable_for_windows_and_macos(self):
        for system in ("win32", "darwin"):
            with patch("anything_plays.libretro_gpu_portable.sys.platform",
                       system):
                self.assertIs(choose_gamecube_gpu_host(), PortableGLFrameHost)

    def test_unsupported_platform_fails_closed(self):
        with patch("anything_plays.libretro_gpu_portable.sys.platform", "other"):
            with self.assertRaises(RuntimeError):
                choose_gamecube_gpu_host()

    def test_macos_open_gl_41_rejects_45_dolphin_request(self):
        host = PortableGLFrameHost.__new__(PortableGLFrameHost)
        host.owner = threading.get_ident()
        host.opengl_version = "4.1 INTEL-17"
        req = HardwareRenderCallback()
        req.context_type = 3
        req.version_major = 4
        req.version_minor = 5
        req.context_reset = 123
        self.assertFalse(host.accept_core_render(C.addressof(req)))

    def test_macos_native_gl_41_version_accepts_actual_dolphin_gl33(self):
        from anything_plays.libretro_gpu_egl import GET_FBO, GET_PROC
        host = PortableGLFrameHost.__new__(PortableGLFrameHost)
        host.owner = threading.get_ident()
        host.opengl_version = "4.1 Metal - 90.0"
        host.fbo = 32
        host._fbo_callback = GET_FBO(lambda: host.fbo)
        host._proc_callback = GET_PROC(lambda name: 123)
        req = HardwareRenderCallback()
        req.context_type = 3
        req.version_major = 3
        req.version_minor = 3
        req.context_reset = 123
        self.assertTrue(host.accept_core_render(C.addressof(req)))
        self.assertEqual(host.core_reset, 123)
        self.assertTrue(req.get_current_framebuffer)

    def test_windows_missing_gpu_driver_reports_actionable_error(self):
        with patch("anything_plays.libretro_gpu_portable.sys.platform",
                   "win32"):
            def absent_driver(**kwargs):
                raise Exception("wglCreateContextAttribsARB not found")
            with self.assertRaisesRegex(RuntimeError, "graphics driver") as caught:
                PortableGLFrameHost(backend=absent_driver)
            self.assertIn("OpenGL 3.3", str(caught.exception))
            self.assertIn("restart Anything Plays", str(caught.exception))

    def test_no_context_procs_return_none_without_native_crash(self):
        host = PortableGLFrameHost.__new__(PortableGLFrameHost)
        host.context = None
        self.assertIsNone(host.get_proc_address(b"glGetString"))
        host.context = Mock()
        host.context.load.return_value = 123
        self.assertEqual(host.get_proc_address(b"glClear"), 123)
        host.context.load.side_effect = ValueError("missing")
        self.assertIsNone(host.get_proc_address(b"missing"))
