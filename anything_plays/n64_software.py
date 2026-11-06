"""Opt-in, *software-rendered* embedded Nintendo 64 test frontend.

ParaLLEl N64's Angrylion graphics plugin draws CPU-owned pixel frames rather
than requiring an OpenGL/Vulkan render callback. This lets the existing
Anything Plays Libretro video path attempt in-panel N64 rendering.

This is EXPERIMENTAL: real hardware ROM, audio, saves, latency and architecture
compatibility are not verified. The normal RetroArch GPU launcher stays
available, and the N64 core is never run with hardware rendering requested.
"""
import ctypes as C
from pathlib import Path

from anything_plays.core_locator import _library_extension, _search_directories


SOFTWARE_OPTIONS = {
    b"parallel-n64-gfxplugin": b"angrylion",
    b"parallel-n64-rspplugin": b"hle",
    b"parallel-n64-angrylion-multithread": b"all threads",
    b"parallel-n64-upscaling": b"1x",
    b"parallel-n64-disable_expmem": b"enabled",
    b"parallel-n64-cpucore": b"Dynamic Recompiler (Ari64)",
}


class RetroVariable(C.Structure):
    _fields_ = [("key", C.c_char_p), ("value", C.c_char_p)]


def find_parallel_n64_core():
    """Locate a packaged ParaLLEl N64 binary, never download at runtime."""
    filename = "parallel_n64_libretro" + _library_extension()
    for directory in _search_directories():
        candidate = Path(directory) / filename
        if candidate.is_file():
            return str(candidate)
    return None


class SoftwareN64Options:
    """Answer Libretro core-option queries without advertising GPU contexts."""

    def __init__(self):
        # Retain references for the lifetime of native callback pointers.
        self.values = dict(SOFTWARE_OPTIONS)

    def environment(self, command, data):
        if command == 15 and data:  # RETRO_ENVIRONMENT_GET_VARIABLE
            item = C.cast(data, C.POINTER(RetroVariable))
            key = item.contents.key
            result = self.values.get(key)
            if result is None:
                return False
            item.contents.value = result
            return True
        if command == 16:  # RETRO_ENVIRONMENT_SET_VARIABLES
            return True
        if command == 17 and data:  # RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE
            C.cast(data, C.POINTER(C.c_bool))[0] = False
            return True
        if command == 52 and data:  # RETRO_ENVIRONMENT_GET_CORE_OPTIONS_VERSION
            # Request legacy v0 GET_VARIABLE support, not v2 option metadata.
            C.cast(data, C.POINTER(C.c_uint))[0] = 0
            return True
        if command == 14:  # RETRO_ENVIRONMENT_SET_HW_RENDER
            # A hardware-render core cannot draw into the Tk software canvas.
            return False
        return None
