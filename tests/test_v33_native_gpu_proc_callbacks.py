"""Native GameCube GL callbacks must return defined zero/NULL on failures.

Calls below use the actual CFUNCTYPE types but no GPU, ROM, core or camera.
The callback bridge is shared by Linux EGL and Windows/macOS glcontext.
"""
import ctypes as C
import threading
import unittest
from unittest.mock import Mock, patch

from anything_plays.libretro_gpu_egl import (
    EGLFrameHost, GET_FBO, GET_PROC, HardwareRenderCallback,
)
from anything_plays.libretro_gpu_portable import PortableGLFrameHost


class NativeGPUCallbackSafetyTests(unittest.TestCase):
    @staticmethod
    def host(klass):
        instance = klass.__new__(klass)
        instance.owner = threading.get_ident()
        instance.fbo = 37
        instance.context = object()
        if klass is PortableGLFrameHost:
            instance._entered = True
        instance.get_proc_address = Mock(return_value=0x123456)
        instance._fbo_callback = GET_FBO(instance._native_get_framebuffer)
        instance._proc_callback = GET_PROC(instance._native_get_proc_address)
        return instance

    def test_native_c_callbacks_return_valid_ids_for_both_platform_hosts(self):
        for klass in (EGLFrameHost, PortableGLFrameHost):
            with self.subTest(host=klass.__name__):
                host = self.host(klass)
                self.assertEqual(host._fbo_callback(), 37)
                self.assertEqual(host._proc_callback(b"glBindFramebuffer"),
                                 0x123456)
                host.get_proc_address.assert_called_once_with(
                    b"glBindFramebuffer"
                )

    def test_driver_exception_returns_null_without_native_callback_error(self):
        for klass in (EGLFrameHost, PortableGLFrameHost):
            for failure in (
                OSError("GPU SECRET-ID /Users/owner/private.iso"),
                RuntimeError("GL function loader PRIVATE /dev/dri/renderD128"),
                ValueError("driver corrupt pointer"),
            ):
                with self.subTest(host=klass.__name__,
                                  failure=type(failure).__name__):
                    host = self.host(klass)
                    host.get_proc_address.side_effect = failure
                    with patch("sys.stderr") as stderr:
                        self.assertIsNone(host._proc_callback(b"glClear"))
                    self.assertFalse(stderr.write.called)
                    self.assertEqual(host._fbo_callback(), 37)

    def test_invalid_native_pointers_are_never_returned(self):
        for invalid in (None, 0, -1, True, 1.5, "private",
                        (1 << (8 * C.sizeof(C.c_void_p))), object()):
            with self.subTest(value=repr(invalid)):
                host = self.host(EGLFrameHost)
                host.get_proc_address.return_value = invalid
                self.assertIsNone(host._proc_callback(b"glClear"))

    def test_context_teardown_or_wrong_thread_returns_null_and_zero(self):
        for klass in (EGLFrameHost, PortableGLFrameHost):
            host = self.host(klass)
            host.fbo = 0
            self.assertEqual(host._fbo_callback(), 0)
            host.owner += 1
            self.assertEqual(host._fbo_callback(), 0)
            self.assertIsNone(host._proc_callback(b"glClear"))
            host.get_proc_address.assert_not_called()

    def test_corrupt_framebuffer_id_cannot_escape_native_callback(self):
        for invalid in (None, -1, True, "private", 2**32, object()):
            with self.subTest(value=repr(invalid)):
                host = self.host(EGLFrameHost)
                host.fbo = invalid
                self.assertEqual(host._fbo_callback(), 0)

    def test_destroyed_context_cannot_publish_stale_fbo_or_proc_address(self):
        for klass in (EGLFrameHost, PortableGLFrameHost):
            with self.subTest(host=klass.__name__):
                host = self.host(klass)
                self.assertEqual(host._fbo_callback(), 37)
                self.assertEqual(host._proc_callback(b"glClear"), 0x123456)
                host.get_proc_address.reset_mock()
                host.context = None
                # Deliberately leave a stale nonzero FBO to prove the
                # callback refuses it independently of native ID cleanup.
                self.assertEqual(host.fbo, 37)
                self.assertEqual(host._fbo_callback(), 0)
                self.assertIsNone(host._proc_callback(b"glClear"))
                host.get_proc_address.assert_not_called()

    def test_egl_context_handle_without_make_current_cannot_negotiate(self):
        host = self.host(EGLFrameHost)
        host._entered = False
        host.opengl_version = "4.5 Mesa"
        host.core_reset = host.core_destroy = None
        self.assertEqual(host._fbo_callback(), 0)
        self.assertIsNone(host._proc_callback(b"glClear"))
        host.get_proc_address.assert_not_called()

        request = HardwareRenderCallback()
        request.context_type = 3
        request.version_major = 3
        request.version_minor = 3
        request.context_reset = 123
        self.assertFalse(host.accept_core_render(C.addressof(request)))
        self.assertFalse(request.get_current_framebuffer)
        self.assertFalse(request.get_proc_address)
        self.assertIsNone(host.core_reset)

    def test_unentered_portable_context_cannot_publish_callback_pointers(self):
        host = self.host(PortableGLFrameHost)
        host._entered = False
        self.assertEqual(host._fbo_callback(), 0)
        self.assertIsNone(host._proc_callback(b"glClear"))
        host.get_proc_address.assert_not_called()

    def test_actual_close_revokes_callbacks_on_both_gpu_backends(self):
        class NativeCtx:
            def __init__(self):
                self.exits = 0

            def __exit__(self, *_args):
                self.exits += 1

        for klass in (EGLFrameHost, PortableGLFrameHost):
            with self.subTest(host=klass.__name__):
                host = self.host(klass)
                host.color_tex = 0
                host.depth_stencil = 0
                host.fbo = 0  # Avoid real GL deletion in no-GPU regression.
                if klass is EGLFrameHost:
                    host.display = 10
                    host.surface = 11
                    host._eglfunc = {
                        symbol: lambda *args: None
                        for symbol in (
                            "eglMakeCurrent", "eglDestroyContext",
                            "eglDestroySurface", "eglTerminate"
                        )
                    }
                else:
                    context = NativeCtx()
                    host.context = context
                host.close()
                self.assertIsNone(host.context)
                self.assertFalse(host._entered)
                self.assertEqual(host._fbo_callback(), 0)
                self.assertIsNone(host._proc_callback(b"glClear"))
                host.get_proc_address.assert_not_called()
                if klass is PortableGLFrameHost:
                    self.assertEqual(context.exits, 1)
                host.close()  # Repeated teardown must remain idempotent.


    def test_native_negotiation_rejects_closed_and_unentered_contexts(self):
        def request():
            callback = HardwareRenderCallback()
            callback.context_type = 3
            callback.version_major = 3
            callback.version_minor = 3
            callback.context_reset = 1234
            callback.context_destroy = 5678
            return callback

        for klass in (EGLFrameHost, PortableGLFrameHost):
            with self.subTest(host=klass.__name__):
                host = self.host(klass)
                host.opengl_version = "4.1 (Core Profile)"
                host.core_reset = host.core_destroy = None
                initial = request()
                self.assertTrue(host.accept_core_render(C.addressof(initial)))
                self.assertTrue(initial.get_current_framebuffer)
                self.assertTrue(initial.get_proc_address)

                # A new native callback request must not reuse the earlier
                # accepted result once the driver-owned context disappears.
                host.context = None
                closed = request()
                self.assertFalse(host.accept_core_render(C.addressof(closed)))
                self.assertFalse(closed.get_current_framebuffer)
                self.assertFalse(closed.get_proc_address)
                if klass is PortableGLFrameHost:
                    host.context = object()
                    host._entered = False
                    unentered = request()
                    self.assertFalse(host.accept_core_render(C.addressof(unentered)))
                    self.assertFalse(unentered.get_current_framebuffer)
                    self.assertFalse(unentered.get_proc_address)

    def test_gl_python_loader_keeps_its_normal_error_visibility(self):
        # Exception isolation must happen at the native callback only.
        # Python startup/driver debugging still gets the actual exception.
        host = self.host(PortableGLFrameHost)
        host.get_proc_address.side_effect = OSError("native GPU load failed")
        with self.assertRaisesRegex(OSError, "native GPU load failed"):
            host.get_proc_address(b"glClear")
        self.assertIsNone(host._proc_callback(b"glClear"))


if __name__ == "__main__":
    unittest.main()
