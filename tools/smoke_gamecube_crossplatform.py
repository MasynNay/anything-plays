"""Validate hidden GameCube GPU framebuffer on the real emulator worker thread.

No game/window or Dolphin binary required: this tests context and FBO access.
Separate native GameCube tests verify actual ROM execution and audio.
"""
from __future__ import annotations
import argparse
import ctypes as C
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from anything_plays.libretro_gpu_portable import choose_gamecube_gpu_host
from anything_plays.libretro_gpu_egl import GL_FRAMEBUFFER

GL_COLOR_BUFFER_BIT = 0x4000


def inspect_gpu():
    host = choose_gamecube_gpu_host()
    with host(width=640, height=576) as gpu:
        gpu._gl("glBindFramebuffer", None, [C.c_uint, C.c_uint])(
            GL_FRAMEBUFFER, gpu.fbo)
        gpu._gl("glClearColor", None, [C.c_float] * 4)(
            0.2, 0.5, 0.8, 1.0)
        gpu._gl("glClear", None, [C.c_uint])(GL_COLOR_BUFFER_BIT)
        rgb = gpu.read_frame(640, 576)
        sample = [int(v) for v in rgb[100, 100]]
        valid = (list(rgb.shape) == [576, 640, 3] and
                 all(abs(a - b) <= 4
                     for a, b in zip(sample, (51, 128, 204))) and
                 gpu.last_gl_error == 0)
        return {
            "host": host.__name__, "renderer": gpu.opengl_renderer,
            "version": gpu.opengl_version, "sample_rgb": sample,
            "frame_shape": list(rgb.shape),
            "uses_emulator_worker_thread": True, "passed": valid,
        }


def validate(report):
    report = Path(report).resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    result = {"passed": False, "platform": sys.platform}
    def worker():
        try:
            result.update(inspect_gpu())
        except BaseException as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
    thread = threading.Thread(target=worker, daemon=True,
                              name="gamecube-gpu-worker")
    started = time.monotonic()
    thread.start()
    thread.join(timeout=30)
    if thread.is_alive():
        result["passed"] = False
        result["timed_out"] = True
    result["seconds"] = round(time.monotonic()-started, 3)
    report.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(validate(args.report))
