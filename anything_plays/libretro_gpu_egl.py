"""Linux offscreen OpenGL Libretro frontend for embedded GameCube playback.

The EGL implementation is shared by native diagnostics and the application.
It owns an EGL pbuffer and an RGBA+depth/stencil FBO; no standalone game
window or separately installed emulator is created. On platforms without
EGL/OpenGL, construction fails clearly rather than inventing a context.

Only call from the thread that owns retro_load_game/retro_run. Native libretro
callbacks and the framebuffer must remain alive until the core unloads.
"""
from __future__ import annotations

import ctypes as C
import os
import re
import sys
import threading

EGL_NONE = 0x3038
EGL_DEFAULT_DISPLAY = None
EGL_OPENGL_API = 0x30A2
GL_FRAMEBUFFER = 0x8D40
GL_READ_FRAMEBUFFER = 0x8CA8
GL_READ_FRAMEBUFFER_BINDING = 0x8CAA
GL_COLOR_ATTACHMENT0 = 0x8CE0
GL_DEPTH_STENCIL_ATTACHMENT = 0x821A
GL_FRAMEBUFFER_COMPLETE = 0x8CD5
GL_TEXTURE_2D = 0x0DE1
GL_RENDERBUFFER = 0x8D41
GL_RGBA8 = 0x8058
GL_RGBA = 0x1908
GL_UNSIGNED_BYTE = 0x1401
GL_TEXTURE_MIN_FILTER = 0x2801
GL_TEXTURE_MAG_FILTER = 0x2800
GL_LINEAR = 0x2601
GL_DEPTH24_STENCIL8 = 0x88F0
GL_PACK_ALIGNMENT = 0x0D05
GL_PACK_ROW_LENGTH = 0x0D02
GL_PACK_SKIP_ROWS = 0x0D04
GL_PACK_SKIP_PIXELS = 0x0D06
GL_PIXEL_PACK_BUFFER = 0x88EB
GL_PIXEL_PACK_BUFFER_BINDING = 0x88ED
GL_READ_BUFFER = 0x0C02
GL_VERSION = 0x1F02
GL_RENDERER = 0x1F01
GL_VENDOR = 0x1F00
MAX_PIXELS = 4096 * 4096

GET_FBO = C.CFUNCTYPE(C.c_size_t)
GET_PROC = C.CFUNCTYPE(C.c_void_p, C.c_char_p)


class HardwareRenderCallback(C.Structure):
    """libretro.h retro_hw_render_callback layout, including natural alignment."""
    _fields_ = [
        ("context_type", C.c_int),
        ("context_reset", C.c_void_p),
        ("get_current_framebuffer", C.c_void_p),
        ("get_proc_address", C.c_void_p),
        ("depth", C.c_bool),
        ("stencil", C.c_bool),
        ("bottom_left_origin", C.c_bool),
        ("version_major", C.c_uint),
        ("version_minor", C.c_uint),
        ("cache_context", C.c_bool),
        ("context_destroy", C.c_void_p),
        ("debug_context", C.c_bool),
    ]


def bounded_dimensions(width, height, max_width=640, max_height=576):
    """Hard stop before reading driver-managed memory at unexpected dimensions."""
    w, h = int(width), int(height)
    if not (0 < w <= max_width and 0 < h <= max_height):
        raise ValueError("OpenGL frame dimensions exceed allocated framebuffer")
    if w * h > MAX_PIXELS:
        raise ValueError("OpenGL frame exceeds safe memory budget")
    return w, h


class EGLFrameHost:
    """Own an OpenGL 3.3+ context and a hidden hardware-rendered FBO."""

    def __init__(self, width=640, height=576):
        if sys.platform != "linux":
            raise RuntimeError("EGL experiment is Linux-only until other GPU hosts are audited")
        self.width, self.height = bounded_dimensions(width, height, 4096, 4096)
        self.owner = threading.get_ident()
        self.egl = C.CDLL("libEGL.so.1")
        self.opengl = C.CDLL("libGL.so.1")
        self._eglfunc = {}
        self._glfunc = {}
        self.display = None
        self.surface = None
        self.context = None
        self.fbo = 0
        self.color_tex = 0
        self.depth_stencil = 0
        self.core_reset = None
        self.core_destroy = None
        self._fbo_callback = GET_FBO(self._native_get_framebuffer)
        self._proc_callback = GET_PROC(self._native_get_proc_address)
        try:
            # EGL can fail after allocating a display, pbuffer or context.
            # Teardown must run for *either* context setup or FBO failure,
            # otherwise a failed GameCube boot retains native GPU handles.
            self._init_egl()
            self._init_framebuffer()
        except BaseException:
            try:
                self.close()
            except Exception:
                # Never replace the original initialization error with a
                # secondary cleanup error from a failing graphics driver.
                pass
            raise

    def _check_thread(self):
        if threading.get_ident() != self.owner:
            raise RuntimeError("OpenGL context accessed from a different thread")

    def _native_get_framebuffer(self):
        """Return only a valid GL framebuffer ID to the Libretro C callback.

        A native core can call this while a GPU context is being torn down.
        Never let a missing driver-owned attribute or invalid ID unwind
        through CFUNCTYPE (which would leave an undefined C return value).
        """
        try:
            self._check_thread()
            # The native core can retain CFUNCTYPE pointers after close().
            # Never advertise a stale FBO while its EGL/CGL/WGL context is
            # gone, or before glcontext.__enter__ has succeeded.
            if (not getattr(self, "context", None)
                    or not getattr(self, "_entered", True)):
                return 0
            framebuffer = self.fbo
            if type(framebuffer) is int and 0 < framebuffer <= 0xFFFFFFFF:
                return framebuffer
        except BaseException:
            # This method is ONLY passed to a native C callback.
            pass
        return 0

    def _native_get_proc_address(self, symbol):
        """Return a function pointer or NULL without escaping into C.

        get_proc_address is also used directly by our Python GL loader,
        where exceptions must remain actionable. Only the Libretro callback
        boundary isolates arbitrary native driver/proc-loader failures.
        """
        try:
            self._check_thread()
            # An obsolete native callback must return NULL *without even
            # calling into the driver's proc loader*. Driver entry points
            # may no longer be valid after the context was destroyed.
            if (not getattr(self, "context", None)
                    or not getattr(self, "_entered", True)):
                return None
            address = self.get_proc_address(symbol)
            if (type(address) is int and 0 < address
                    <= (1 << (8 * C.sizeof(C.c_void_p))) - 1):
                return address
        except BaseException:
            # CFUNCTYPE swallows Python exceptions and may otherwise expose
            # an indeterminate native pointer. NULL explicitly means absent.
            pass
        return None

    def _ef(self, name, restype, argtypes):
        fn = getattr(self.egl, name)
        fn.restype = restype
        fn.argtypes = argtypes
        self._eglfunc[name] = fn
        return fn

    def _gl(self, name, restype, argtypes):
        if name not in self._glfunc:
            address = self.get_proc_address(name.encode("ascii"))
            if not address:
                raise RuntimeError("Missing required OpenGL entry point: " + name)
            self._glfunc[name] = C.CFUNCTYPE(restype, *argtypes)(address)
        return self._glfunc[name]

    def _init_egl(self):
        V, I, UI = C.c_void_p, C.c_int, C.c_uint
        get_display = self._ef("eglGetDisplay", V, [V])
        initialize = self._ef("eglInitialize", UI, [V, C.POINTER(I), C.POINTER(I)])
        bind_api = self._ef("eglBindAPI", UI, [UI])
        choose = self._ef("eglChooseConfig", UI, [V, C.POINTER(I), C.POINTER(V), I, C.POINTER(I)])
        pbuffer = self._ef("eglCreatePbufferSurface", V, [V, V, C.POINTER(I)])
        create = self._ef("eglCreateContext", V, [V, V, V, C.POINTER(I)])
        self._ef("eglMakeCurrent", UI, [V, V, V, V])
        self._ef("eglDestroySurface", UI, [V, V])
        self._ef("eglDestroyContext", UI, [V, V])
        self._ef("eglTerminate", UI, [V])
        self._ef("eglGetProcAddress", V, [C.c_char_p])
        self.display = get_display(EGL_DEFAULT_DISPLAY)
        major, minor = I(), I()
        if not self.display or not initialize(self.display, C.byref(major), C.byref(minor)):
            raise RuntimeError("Could not initialize offscreen EGL display")
        if not bind_api(EGL_OPENGL_API):
            raise RuntimeError("EGL OpenGL API unavailable")
        attrs = (I * 17)(
            0x3024, 8, 0x3023, 8, 0x3022, 8, 0x3040, 8,
            0x3033, 1, 0x3021, 8, 0x3025, 24, EGL_NONE,
        )
        configuration, count = V(), I()
        if not choose(self.display, attrs, C.byref(configuration), 1, C.byref(count)) or not count.value:
            raise RuntimeError("No offscreen RGBA OpenGL-compatible EGL config")
        surfattrs = (I * 5)(0x3057, self.width, 0x3056, self.height, EGL_NONE)
        self.surface = pbuffer(self.display, configuration, surfattrs)
        ctxattrs = (I * 7)(0x3098, 3, 0x30FB, 3, 0x30FD, 1, EGL_NONE)
        self.context = create(self.display, configuration, None, ctxattrs)
        if not self.surface or not self.context:
            raise RuntimeError("Could not create offscreen OpenGL core context")
        if not self._eglfunc["eglMakeCurrent"](self.display, self.surface, self.surface, self.context):
            raise RuntimeError("Could not make offscreen OpenGL context current")
        get_string = self._gl("glGetString", C.c_char_p, [UI])
        version = get_string(GL_VERSION)
        if not version:
            raise RuntimeError("Created EGL context does not expose OpenGL")
        self.opengl_version = version.decode("utf-8", errors="replace")
        self.opengl_vendor = (get_string(GL_VENDOR) or b"").decode("utf-8", errors="replace")
        self.opengl_renderer = (get_string(GL_RENDERER) or b"").decode("utf-8", errors="replace")
        self.last_gl_error = 0

    def get_proc_address(self, symbol):
        if not symbol:
            return None
        proc = self._eglfunc.get("eglGetProcAddress")
        if proc:
            addr = proc(symbol)
            if addr:
                return int(addr)
        try:
            return C.cast(getattr(self.opengl, symbol.decode("ascii")), C.c_void_p).value
        except (AttributeError, UnicodeError):
            return None

    def _init_framebuffer(self):
        I, UI, V = C.c_int, C.c_uint, C.c_void_p
        self._check_thread()
        fbo, tex, depth = UI(), UI(), UI()
        self._gl("glGenFramebuffers", None, [I, C.POINTER(UI)])(1, C.byref(fbo))
        # Take ownership immediately after each successful allocation.
        # If a later GL call fails, __init__ invokes close(), which must
        # know every resource that has already been created. Delaying all
        # three assignments until FRAMEBUFFER_COMPLETE leaked partial FBOs.
        self.fbo = fbo.value
        self._gl("glBindFramebuffer", None, [UI, UI])(GL_FRAMEBUFFER, fbo)
        self._gl("glGenTextures", None, [I, C.POINTER(UI)])(1, C.byref(tex))
        self.color_tex = tex.value
        self._gl("glBindTexture", None, [UI, UI])(GL_TEXTURE_2D, tex)
        self._gl("glTexParameteri", None, [UI, UI, I])(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        self._gl("glTexParameteri", None, [UI, UI, I])(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        self._gl("glTexImage2D", None, [UI, I, I, I, I, I, UI, UI, V])(
            GL_TEXTURE_2D, 0, GL_RGBA8, self.width, self.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None
        )
        self._gl("glFramebufferTexture2D", None, [UI, UI, UI, UI, I])(
            GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, tex, 0
        )
        self._gl("glGenRenderbuffers", None, [I, C.POINTER(UI)])(1, C.byref(depth))
        self.depth_stencil = depth.value
        self._gl("glBindRenderbuffer", None, [UI, UI])(GL_RENDERBUFFER, depth)
        self._gl("glRenderbufferStorage", None, [UI, UI, I, I])(
            GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, self.width, self.height
        )
        self._gl("glFramebufferRenderbuffer", None, [UI, UI, UI, UI])(
            GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, depth
        )
        status = self._gl("glCheckFramebufferStatus", UI, [UI])(GL_FRAMEBUFFER)
        if status != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("Offscreen GameCube framebuffer incomplete: " + hex(status))
        # The three handles have already been recorded, including in the
        # failed/incomplete FBO paths, so teardown always has ownership.

    def accept_core_render(self, address):
        self._check_thread()
        if not address:
            return False
        req = C.cast(address, C.POINTER(HardwareRenderCallback)).contents
        if req.context_type != 3 or (req.version_major, req.version_minor) > (4, 5):
            return False
        # An EGL 3.3 minimum-version request does NOT prove that a driver
        # delivered OpenGL 4.5. Never hand a Dolphin core a GL context
        # lower than the version it explicitly requested: calling newer
        # entry points on older native GPU drivers can crash the process.
        # GL_VERSION permits vendor/build suffixes such as "3.3 Mesa 24".
        version = re.match(r"^\s*(\d+)\.(\d+)", getattr(self, "opengl_version", ""))
        if version is None:
            return False
        supported = (int(version.group(1)), int(version.group(2)))
        if (req.version_major, req.version_minor) > supported:
            return False
        if not req.context_reset:
            return False
        req.get_current_framebuffer = C.cast(self._fbo_callback, C.c_void_p).value
        req.get_proc_address = C.cast(self._proc_callback, C.c_void_p).value
        self.core_reset = req.context_reset
        self.core_destroy = req.context_destroy
        return True

    def reset_core(self):
        self._check_thread()
        if not self.core_reset:
            raise RuntimeError("Dolphin did not negotiate a supported hardware context")
        C.CFUNCTYPE(None)(self.core_reset)()

    def destroy_core(self):
        self._check_thread()
        if self.core_destroy:
            cb, self.core_destroy = self.core_destroy, None
            C.CFUNCTYPE(None)(cb)()

    def read_frame(self, width, height, flip_vertical=True):
        """Read a completed FBO into independently owned RGB numpy storage."""
        self._check_thread()
        w, h = bounded_dimensions(width, height, self.width, self.height)
        import numpy as np

        # Dolphin may have left a GL error from earlier rendering. Drain a
        # bounded set BEFORE our readback so an unrelated old error does not
        # turn a valid game frame into a fatal new readback failure.
        get_error = self._gl("glGetError", C.c_uint, [])
        for _ in range(8):
            if not get_error():
                break
        else:
            self.last_gl_error = 1
            raise RuntimeError("GPU readback OpenGL error")

        # Native Dolphin can leave a pixel pack buffer or a nondefault
        # row length/skip offset bound when its video callback fires.
        # glReadPixels treats a pointer as a PBO offset in that case, and
        # row/skip state can write beyond our exact w*h*4 client buffer.
        # Isolate ALL pack layout needed for this tightly packed RGBA copy;
        # restore native GL state even after a failed transfer.
        get_int = self._gl("glGetIntegerv", None, [C.c_uint, C.c_void_p])
        old_read = C.c_int()
        get_int(GL_READ_FRAMEBUFFER_BINDING, C.byref(old_read))
        old_pbo = C.c_int()
        get_int(GL_PIXEL_PACK_BUFFER_BINDING, C.byref(old_pbo))
        pack_state = (
            (GL_PACK_ALIGNMENT, C.c_int(4), 1),
            (GL_PACK_ROW_LENGTH, C.c_int(0), 0),
            (GL_PACK_SKIP_ROWS, C.c_int(0), 0),
            (GL_PACK_SKIP_PIXELS, C.c_int(0), 0),
        )
        for pname, previous, _desired in pack_state:
            get_int(pname, C.byref(previous))

        bind_read = self._gl(
            "glBindFramebuffer", None, [C.c_uint, C.c_uint]
        )
        bind_pack = self._gl(
            "glBindBuffer", None, [C.c_uint, C.c_uint]
        )
        pixel_store = self._gl(
            "glPixelStorei", None, [C.c_uint, C.c_int]
        )
        read_buffer = self._gl("glReadBuffer", None, [C.c_uint])
        read_pixels = self._gl(
            "glReadPixels", None,
            [C.c_int, C.c_int, C.c_int, C.c_int,
             C.c_uint, C.c_uint, C.c_void_p],
        )
        # Allocate native transfer storage before mutating GL state.
        image = (C.c_ubyte * (w * h * 4))()
        # Read-buffer selection belongs to the FBO, not the global pack
        # state. Query it only AFTER binding our FBO; restore it before
        # returning to the previously active native read framebuffer.
        old_read_buffer = C.c_int(GL_COLOR_ATTACHMENT0)
        read_buffer_known = False
        try:
            bind_read(GL_READ_FRAMEBUFFER, self.fbo)
            get_int(GL_READ_BUFFER, C.byref(old_read_buffer))
            read_buffer_known = True
            if old_read_buffer.value != GL_COLOR_ATTACHMENT0:
                read_buffer(GL_COLOR_ATTACHMENT0)
            if old_pbo.value:
                bind_pack(GL_PIXEL_PACK_BUFFER, 0)
            for pname, previous, desired in pack_state:
                if previous.value != desired:
                    pixel_store(pname, desired)
            read_pixels(0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, image)
        finally:
            try:
                for pname, previous, desired in pack_state:
                    if previous.value != desired:
                        pixel_store(pname, previous.value)
            finally:
                try:
                    if old_pbo.value:
                        bind_pack(GL_PIXEL_PACK_BUFFER, old_pbo.value)
                finally:
                    try:
                        if (read_buffer_known
                                and old_read_buffer.value != GL_COLOR_ATTACHMENT0):
                            read_buffer(old_read_buffer.value)
                    finally:
                        bind_read(GL_READ_FRAMEBUFFER, old_read.value)
        self.last_gl_error = get_error()
        if self.last_gl_error:
            # glReadPixels can fail without raising a Python exception. The
            # destination buffer remains zero-filled, which otherwise looks
            # like a valid (but permanently black) video frame. Fail closed
            # with a fixed error category; do not include GPU vendor strings.
            raise RuntimeError("GPU readback OpenGL error")
        arr = np.frombuffer(image, dtype=np.uint8).reshape(h, w, 4)[:, :, :3]
        return arr[::-1].copy() if flip_vertical else arr.copy()

    def close(self):
        """Release even partially initialized EGL resources, once.

        EGL initialization may fail after a display or surface exists but
        before an OpenGL context becomes current. The failed driver must not
        mask the originating exception or leave a surface/display behind.
        """
        self._check_thread()
        display, surface, context = self.display, self.surface, self.context
        self.display = self.surface = self.context = None

        def best_effort_egl(name, *args):
            fn = self._eglfunc.get(name)
            if fn is not None:
                try:
                    fn(*args)
                except Exception:
                    # A destroyed context may reject cleanup operations.
                    # Continue releasing the other independently owned
                    # native handles; never publish vendor exception text.
                    pass

        try:
            if display and context:
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
                        except Exception:
                            # Do not abandon the EGL context on a GL driver
                            # failure while removing an optional FBO.
                            pass
                best_effort_egl("eglMakeCurrent", display, None, None, None)
                best_effort_egl("eglDestroyContext", display, context)
            # A pbuffer may exist even when eglCreateContext failed.
            if display and surface:
                best_effort_egl("eglDestroySurface", display, surface)
            if display:
                best_effort_egl("eglTerminate", display)
        finally:
            self.fbo = self.color_tex = self.depth_stencil = 0
            self.core_reset = self.core_destroy = None

    def __enter__(self):
        return self

    def __exit__(self, _t, _v, _tb):
        self.close()
