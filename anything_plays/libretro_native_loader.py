"""Explicitly release native N64 Libretro libraries after retro_deinit.

ctypes.CDLL retains a loaded module for the lifetime of the process unless
the host explicitly releases it. ParaLLEl-N64 retains global state between
ROMs, so a fresh retro_init on the *same mapped module* produces a blank
second game. Only N64 opts into this unload; validated 2D/GC paths remain
unchanged. Never release a module while game or callbacks are active.
"""
import _ctypes
import os


CORE_CALLS = (
    "set_environment", "set_video", "set_audio", "set_audio_batch",
    "set_poll", "set_state", "set_controller_device", "init", "deinit",
    "load", "unload", "run", "system_info", "av_info", "memory_data",
    "memory_size",
)


def release_inactive_core_library(native):
    """Drop every bound C function and unload its native module exactly once."""
    if native.loaded or native.initialized:
        raise RuntimeError("Cannot release active native core")
    if native.callbacks:
        raise RuntimeError("Cannot unload module while callbacks are registered")
    module = native.library
    if module is None:
        return
    handle = module._handle
    for name in CORE_CALLS:
        if hasattr(native, name):
            setattr(native, name, None)
    native.library = None
    if os.name == "nt":
        _ctypes.FreeLibrary(handle)
    else:
        _ctypes.dlclose(handle)
