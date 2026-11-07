"""Windows WGL and macOS CGL headless OpenGL framebuffer hosts for Dolphin.

No external executable, RetroArch, standalone Dolphin install, GLFW, or
second game window is needed. The tiny MIT-licensed glcontext extension
owns a thread-local native context. The existing proven EGL host supplies
the shared FBO, GL ABI, pixel readback and Libretro hardware callback logic.

This is a 3.0 *experimental* platform backend: CI must establish a real
Dolphin game and audio on every OS before it can be public release-ready.
"""
from __future__ import annotations

import ctypes as C
import re
import sys
import threading

from anything_plays.libretro_gpu_egl import (
    EGLFrameHost, GET_FBO, GET_PROC, bounded_dimensions,
    GL_VERSION, GL_VENDOR, GL_RENDERER,
)


class PortableGLFrameHost(EGLFrameHost):
    """Make a hidden WGL/CGL context without constructing a GUI window."""

    def __init__(self, width=640, height=576, *, backend=None):
        if sys.platform not in ("win32", "darwin"):
            raise RuntimeError(
                "Portable GameCube GPU host requires Windows WGL or macOS CGL"
            )
        self.width, self.height = bounded_dimensions(width, height, 4096, 4096)
        self.owner = threading.get_ident()
        self._glfunc = {}
        self._eglfunc = {}
        self.fbo = self.color_tex = self.depth_stencil = 0
        self.core_reset = self.core_destroy = None
        self.last_gl_error = 0
        self.context = None
        self._entered = False
        self._fbo_callback = GET_FBO(lambda: self.fbo)
        self._proc_callback = GET_PROC(self.get_proc_address)
        if backend is None:
            try:
                import glcontext
            except ImportError as exc:
                raise RuntimeError(
                    "GameCube GPU context dependency not installed with Anything Plays"
                ) from exc
            backend = glcontext.default_backend()
        opts = {"mode": "standalone"}
        if sys.platform == "win32":
            opts["glversion"] = 330
        try:
            self.context = backend(**opts)
            self.context.__enter__()
            self._entered = True
            get_string = self._gl("glGetString", C.c_char_p, [C.c_uint])
            raw = get_string(GL_VERSION)
            if not raw:
                raise RuntimeError("Headless GPU context has no OpenGL version")
            self.opengl_version = raw.decode("utf-8", errors="replace")
            self.opengl_vendor = (get_string(GL_VENDOR) or b"").decode(
                "utf-8", errors="replace"
            )
            self.opengl_renderer = (get_string(GL_RENDERER) or b"").decode(
                "utf-8", errors="replace"
            )
            self._init_framebuffer()
        except BaseException:
            self.close()
            raise

    def get_proc_address(self, symbol):
        if not symbol or self.context is None:
            return None
        try:
            return int(self.context.load(symbol.decode("ascii")))
        except (AttributeError, UnicodeError, TypeError, ValueError, RuntimeError):
            return None

    def accept_core_render(self, address):
        self._check_thread()
        if not address:
            return False
        from anything_plays.libretro_gpu_egl import HardwareRenderCallback
        req = C.cast(address, C.POINTER(HardwareRenderCallback)).contents
        # macOS CGL supports up to GL 4.1. Never pretend to satisfy a
        # native core asking for a newer context than what was created.
        # Drivers append arbitrary vendor/build suffixes to GL_VERSION:
        # "4.1 Metal - 90.0", "4.1 INTEL-17", "4.5 (Core Profile)".
        # Treat that trailing text as metadata, not part of the minor number.
        version = re.match(r"^\s*(\d+)\.(\d+)", self.opengl_version or "")
        if version is None:
            return False
        supported = int(version.group(1)), int(version.group(2))
        if (req.version_major, req.version_minor) > supported:
            return False
        return super().accept_core_render(address)

    def close(self):
        self._check_thread()
        context = self.context
        if context is None:
            return
        try:
            if self._entered:
                for attr, symbol in (
                    ("fbo", "glDeleteFramebuffers"),
                    ("color_tex", "glDeleteTextures"),
                    ("depth_stencil", "glDeleteRenderbuffers"),
                ):
                    identifier = getattr(self, attr, 0)
                    if identifier:
                        try:
                            self._gl(symbol, None, [
                                C.c_int, C.POINTER(C.c_uint)
                            ])(1, C.byref(C.c_uint(identifier)))
                        except (RuntimeError, ValueError):
                            # No GL calls after the native context is lost.
                            pass
        finally:
            try:
                if self._entered:
                    context.__exit__(None, None, None)
            finally:
                self.context = None
                self._entered = False
                self.fbo = self.color_tex = self.depth_stencil = 0
                self.core_reset = self.core_destroy = None


def choose_gamecube_gpu_host():
    """Use the known EGL backend on Linux and windowless WGL/CGL elsewhere."""
    if sys.platform == "linux":
        return EGLFrameHost
    if sys.platform in ("win32", "darwin"):
        return PortableGLFrameHost
    raise RuntimeError("GameCube GPU rendering unavailable on this platform")
