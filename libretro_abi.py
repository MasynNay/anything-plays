"""Native declarations for libretro.h, used unchanged across all consoles.

The core holds callback pointers: keep CFUNCTYPE objects alive until after
``retro_unload_game`` and ``retro_deinit`` have both returned.
"""

import ctypes as C

VIDEO = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AUDIO = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
AUDIO_BATCH = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
INPUT_POLL = C.CFUNCTYPE(None)
INPUT_STATE = C.CFUNCTYPE(
    C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint
)
ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)


class GameInfo(C.Structure):
    """Game path or in-memory bytes passed to retro_load_game."""

    _fields_ = [
        ("path", C.c_char_p), ("data", C.c_void_p),
        ("size", C.c_size_t), ("meta", C.c_char_p),
    ]


class CoreInfo(C.Structure):
    """Game loading options returned by retro_get_system_info."""

    _fields_ = [
        ("library_name", C.c_char_p), ("library_version", C.c_char_p),
        ("valid_extensions", C.c_char_p), ("need_fullpath", C.c_bool),
        ("block_extract", C.c_bool),
    ]


class Geometry(C.Structure):
    """Maximum and current frame sizes."""

    _fields_ = [
        ("base_width", C.c_uint), ("base_height", C.c_uint),
        ("max_width", C.c_uint), ("max_height", C.c_uint),
        ("aspect_ratio", C.c_float),
    ]


class Timing(C.Structure):
    """Core-supplied video rate and PCM sample rate."""

    _fields_ = [("fps", C.c_double), ("sample_rate", C.c_double)]


class AVInfo(C.Structure):
    """libretro_system_av_info with C-compatible field order and alignment."""

    _fields_ = [("geometry", Geometry), ("timing", Timing)]
