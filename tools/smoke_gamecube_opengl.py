"""Independent live offscreen OpenGL smoke: no Dolphin/game or app window."""
import json
from pathlib import Path

from tools.libretro_gpu_egl import EGLFrameHost, GL_FRAMEBUFFER

with EGLFrameHost(640, 576) as ctx:
    assert ctx.fbo > 0
    assert ctx.get_proc_address(b"glClearColor")
    assert ctx.get_proc_address(b"glReadPixels")
    ctx._gl("glBindFramebuffer", None, [__import__("ctypes").c_uint, __import__("ctypes").c_uint])(
        GL_FRAMEBUFFER, ctx.fbo
    )
    import ctypes as C
    ctx._gl("glClearColor", None, [C.c_float] * 4)(0.25, 0.5, 0.75, 1.0)
    ctx._gl("glClear", None, [C.c_uint])(0x4000)
    frame = ctx.read_frame(640, 576)
    assert frame.shape == (576, 640, 3), frame.shape
    rgb = [int(frame[0, 0, i]) for i in range(3)]
    assert abs(rgb[0] - 64) <= 2, rgb
    assert abs(rgb[1] - 128) <= 2, rgb
    assert abs(rgb[2] - 191) <= 2, rgb
    report = {"passed": True, "fbo": ctx.fbo, "shape": list(frame.shape), "rgb": rgb}
    print(json.dumps(report, indent=2), flush=True)
