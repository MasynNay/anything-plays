"""Partial OpenGL framebuffer allocation is released for EGL and WGL/CGL.

Simulates actual GL ID outputs and interrupted setup: no GPU, ROM or display.
Both GPU hosts share EGLFrameHost._init_framebuffer, but release resources
through platform-specific close methods.
"""
import ctypes as C
import threading
import unittest

from anything_plays.libretro_gpu_egl import (
    EGLFrameHost, GL_FRAMEBUFFER_COMPLETE,
)
from anything_plays.libretro_gpu_portable import PortableGLFrameHost


class FakeGLContext:
    def __init__(self):
        self.exits = 0

    def __exit__(self, *_args):
        self.exits += 1


class FramebufferAllocationCleanupTests(unittest.TestCase):
    def mock_host(self, kind, *, failure, incomplete=False):
        host = kind.__new__(kind)
        host.owner = threading.get_ident()
        host.width, host.height = 16, 8
        host.fbo = host.color_tex = host.depth_stencil = 0
        host.core_reset = host.core_destroy = None
        deleted = []
        events = []
        if kind is PortableGLFrameHost:
            context = FakeGLContext()
            host.context = context
            host._entered = True
        else:
            context = None
            host.context = 42
            host.surface = 41
            host.display = 40
            host._eglfunc = {
                name: (lambda *args, _name=name: events.append(_name))
                for name in ("eglMakeCurrent", "eglDestroyContext",
                             "eglDestroySurface", "eglTerminate")
            }

        identifiers = {
            "glGenFramebuffers": 101,
            "glGenTextures": 102,
            "glGenRenderbuffers": 103,
        }
        deletes = {
            "glDeleteFramebuffers": "glGenFramebuffers",
            "glDeleteTextures": "glGenTextures",
            "glDeleteRenderbuffers": "glGenRenderbuffers",
        }

        def gl(name, _restype, _argtypes):
            def call(*args):
                events.append(name)
                if name in identifiers:
                    # Native glGenX writes its GLuint through this pointer.
                    C.cast(args[1], C.POINTER(C.c_uint))[0] = identifiers[name]
                if name in deletes:
                    value = C.cast(args[1], C.POINTER(C.c_uint))[0]
                    deleted.append((deletes[name], value))
                if name == failure:
                    raise RuntimeError("PRIMARY framebuffer driver failure")
                if name == "glCheckFramebufferStatus":
                    return 0x8CD6 if incomplete else GL_FRAMEBUFFER_COMPLETE
                return None
            return call
        host._gl = gl
        return host, events, deleted, context

    def test_cleanup_after_mid_setup_failures_for_both_backends(self):
        # Every phase runs after some objects already exist. The current
        # assigned handles must be sufficient for each host's close().
        steps = (
            ("glBindFramebuffer", ("glGenFramebuffers",)),
            ("glTexImage2D", ("glGenFramebuffers", "glGenTextures")),
            ("glRenderbufferStorage", (
                "glGenFramebuffers", "glGenTextures",
                "glGenRenderbuffers",
            )),
            ("glCheckFramebufferStatus", (
                "glGenFramebuffers", "glGenTextures",
                "glGenRenderbuffers",
            )),
        )
        for backend in (EGLFrameHost, PortableGLFrameHost):
            for failed, allocated in steps:
                with self.subTest(backend=backend.__name__, at=failed):
                    host, events, deleted, context = self.mock_host(
                        backend, failure=failed
                    )
                    with self.assertRaisesRegex(
                        RuntimeError, "PRIMARY framebuffer driver failure"
                    ):
                        host._init_framebuffer()
                    host.close()
                    self.assertEqual(
                        deleted,
                        [(name, {"glGenFramebuffers": 101,
                                 "glGenTextures": 102,
                                 "glGenRenderbuffers": 103}[name])
                         for name in allocated],
                    )
                    self.assertEqual(
                        (host.fbo, host.color_tex, host.depth_stencil),
                        (0, 0, 0),
                    )
                    before = len(events)
                    host.close()
                    self.assertEqual(len(events), before)
                    if context is not None:
                        self.assertEqual(context.exits, 1)
                    else:
                        self.assertIn("eglTerminate", events)

    def test_incomplete_framebuffer_releases_all_created_objects(self):
        for backend in (EGLFrameHost, PortableGLFrameHost):
            with self.subTest(backend=backend.__name__):
                host, events, deleted, context = self.mock_host(
                    backend, failure=None, incomplete=True
                )
                with self.assertRaisesRegex(RuntimeError, "incomplete"):
                    host._init_framebuffer()
                host.close()
                self.assertEqual(
                    deleted,
                    [("glGenFramebuffers", 101), ("glGenTextures", 102),
                     ("glGenRenderbuffers", 103)],
                )

    def test_successful_framebuffer_owns_all_three_ids_until_close(self):
        for backend in (EGLFrameHost, PortableGLFrameHost):
            with self.subTest(backend=backend.__name__):
                host, events, deleted, context = self.mock_host(
                    backend, failure=None
                )
                host._init_framebuffer()
                self.assertEqual(
                    (host.fbo, host.color_tex, host.depth_stencil),
                    (101, 102, 103),
                )
                self.assertEqual(deleted, [])
                host.close()
                self.assertEqual(
                    deleted,
                    [("glGenFramebuffers", 101), ("glGenTextures", 102),
                     ("glGenRenderbuffers", 103)],
                )


if __name__ == "__main__":
    unittest.main()
