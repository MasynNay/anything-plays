"""3.3 EGL startup cleanup: no GPU, core, camera, ROM or display required."""
import threading
import unittest
from unittest.mock import Mock, patch

from anything_plays.libretro_gpu_egl import EGLFrameHost


class EGLPartialInitCleanupTests(unittest.TestCase):
    @staticmethod
    def make_hooks(events, *, fail_context_delete=False):
        def log(name):
            def call(*args):
                events.append((name, args))
                if name == "eglDestroyContext" and fail_context_delete:
                    raise OSError("PRIVATE GL driver /home/owner/card")
                return 1
            return call
        return {name: log(name) for name in (
            "eglMakeCurrent", "eglDestroyContext",
            "eglDestroySurface", "eglTerminate",
        )}

    def construct_failure(self, *, surface, context, in_framebuffer=False,
                          fail_context_delete=False, with_fbo=False):
        events = []
        instances = []
        hooks = self.make_hooks(events, fail_context_delete=fail_context_delete)

        def egl_init(host):
            instances.append(host)
            host.display = 10
            host.surface = 20 if surface else None
            host.context = 30 if context else None
            # The framebuffer stage can only be reached after a successful
            # eglMakeCurrent. Earlier synthetic failures are unentered.
            host._entered = bool(context and in_framebuffer)
            host._eglfunc.update(hooks)
            if not in_framebuffer:
                raise RuntimeError("original EGL setup failure")

        def fbo_init(host):
            if with_fbo:
                host.fbo, host.color_tex, host.depth_stencil = 7, 8, 9
                def mock_gl(symbol, _result, _args):
                    def call(*args):
                        events.append((symbol, args))
                        if symbol == "glDeleteTextures":
                            raise RuntimeError("private GPU delete failed")
                    return call
                host._gl = mock_gl
            raise RuntimeError("original FBO setup failure")

        with (
            patch("anything_plays.libretro_gpu_egl.sys.platform", "linux"),
            patch("anything_plays.libretro_gpu_egl.C.CDLL",
                  return_value=Mock()),
            patch.object(EGLFrameHost, "_init_egl", egl_init),
            patch.object(EGLFrameHost, "_init_framebuffer", fbo_init),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "original FBO setup failure" if in_framebuffer
                else "original EGL setup failure",
            ):
                EGLFrameHost()
        host = instances[0]
        self.assertIsNone(host.display)
        self.assertIsNone(host.surface)
        self.assertIsNone(host.context)
        self.assertFalse(host._entered)
        self.assertEqual((host.fbo, host.color_tex, host.depth_stencil),
                         (0, 0, 0))
        self.assertIsNone(host.core_reset)
        self.assertIsNone(host.core_destroy)
        before = len(events)
        host.close()
        self.assertEqual(len(events), before, "cleanup must be idempotent")
        return [name for name, args in events]

    def test_display_only_failure_terminates_display(self):
        self.assertEqual(
            self.construct_failure(surface=False, context=False),
            ["eglTerminate"],
        )

    def test_surface_without_context_is_destroyed(self):
        self.assertEqual(
            self.construct_failure(surface=True, context=False),
            ["eglDestroySurface", "eglTerminate"],
        )

    def test_current_context_failure_unbinds_and_destroys_all_handles(self):
        self.assertEqual(
            self.construct_failure(surface=True, context=True),
            ["eglMakeCurrent", "eglDestroyContext",
             "eglDestroySurface", "eglTerminate"],
        )

    def test_secondary_egl_driver_error_does_not_hide_original_failure(self):
        self.assertEqual(
            self.construct_failure(
                surface=True, context=True, fail_context_delete=True),
            ["eglMakeCurrent", "eglDestroyContext",
             "eglDestroySurface", "eglTerminate"],
        )

    def test_unentered_egl_context_skips_gl_calls_but_releases_egl(self):
        host = EGLFrameHost.__new__(EGLFrameHost)
        host.owner = threading.get_ident()
        host.display, host.surface, host.context = 10, 20, 30
        host._entered = False  # eglMakeCurrent failed after context creation.
        # Deliberately model corrupt/stale IDs: none can trigger GL calls
        # without an entered context.
        host.fbo, host.color_tex, host.depth_stencil = 7, 8, 9
        host.core_reset, host.core_destroy = 123, 456
        events = []
        host._eglfunc = self.make_hooks(events)
        host._gl = Mock()
        host.close()
        host._gl.assert_not_called()
        self.assertEqual(
            [name for name, _args in events],
            ["eglMakeCurrent", "eglDestroyContext",
             "eglDestroySurface", "eglTerminate"],
        )
        self.assertIsNone(host.context)
        self.assertFalse(host._entered)
        self.assertEqual((host.fbo, host.color_tex, host.depth_stencil),
                         (0, 0, 0))
        self.assertIsNone(host.core_reset)
        self.assertIsNone(host.core_destroy)
        before = len(events)
        host.close()
        self.assertEqual(len(events), before)

    def test_framebuffer_init_failure_still_destroys_all_resources(self):
        self.assertEqual(
            self.construct_failure(
                surface=True, context=True,
                in_framebuffer=True, with_fbo=True,
            ),
            ["glDeleteFramebuffers", "glDeleteTextures",
             "glDeleteRenderbuffers", "eglMakeCurrent",
             "eglDestroyContext", "eglDestroySurface", "eglTerminate"],
        )


if __name__ == "__main__":
    unittest.main()
