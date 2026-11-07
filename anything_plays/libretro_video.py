"""Convert the Libretro C video callback's pixel formats to RGB frames.

Cores may provide padded scanlines, so pitch is respected rather than assuming
that a video buffer is tightly packed. The returned array owns its storage;
the core is free to reuse its buffer as soon as the callback returns.
"""

import ctypes as C

import numpy as np

RGB1555 = 0
XRGB8888 = 1
RGB565 = 2
# This is a private frontend-only marker, NOT a Libretro pixel-format value.
# Dolphin's software SWTexture is explicitly struct Pixel {r,g,b,a} and
# retro_video_refresh receives those bytes directly without a libretro
# SET_PIXEL_FORMAT request. Decoding it as XRGB8888 swaps red and blue.
SOFTWARE_RGBA8888 = 3
SUPPORTED_FORMATS = (RGB1555, XRGB8888, RGB565)
MAX_FRAME_BYTES = 64 * 1024 * 1024  # Bound a malformed core's frame allocation.
RETRO_HW_FRAME_BUFFER_VALID = C.c_void_p(-1).value


def decode_frame(buffer, width, height, pitch, pixel_format):
    """Return an owned uint8 ``(height, width, 3)`` RGB array.

    An empty frame is signaled by ``None``. Invalid pitch/format combinations
    raise ``ValueError`` so tests and callers can detect malformed buffers.
    """
    # Never dereference the reserved Libretro hardware framebuffer sentinel.
    # Software-only rendering may still receive it if a native core ignores
    # graphics negotiation, and ctypes.string_at(-1) crashes the process.
    if isinstance(buffer, C.c_void_p):
        buffer = buffer.value
    if not buffer or buffer == RETRO_HW_FRAME_BUFFER_VALID:
        return None
    if width <= 0 or height <= 0:
        return None
    if pixel_format not in (*SUPPORTED_FORMATS, SOFTWARE_RGBA8888):
        raise ValueError(f"Unsupported Libretro pixel format: {pixel_format}")
    bytes_per_pixel = (
        4 if pixel_format in (XRGB8888, SOFTWARE_RGBA8888) else 2
    )
    if pitch < width * bytes_per_pixel:
        raise ValueError("Video pitch is shorter than the image row")
    if width > 4096 or height > 4096 or pitch > 65536:
        raise ValueError("Unexpected Libretro video dimensions")
    if pitch * height > MAX_FRAME_BYTES:
        raise ValueError("Libretro video frame exceeds safe memory budget")

    raw = C.string_at(buffer, pitch * height)
    if pixel_format == SOFTWARE_RGBA8888:
        pixels = np.ndarray(
            (height, width, 4), dtype=np.uint8,
            buffer=raw, strides=(pitch, 4, 1),
        )
        # Owned storage is mandatory: Dolphin reuses its native texture.
        return pixels[:, :, :3].copy()
    if pixel_format == XRGB8888:
        pixels = np.ndarray(
            (height, width), dtype="<u4", buffer=raw, strides=(pitch, 4)
        )
        channels = ((pixels >> 16) & 255, (pixels >> 8) & 255, pixels & 255)
    else:
        pixels = np.ndarray(
            (height, width), dtype="<u2", buffer=raw, strides=(pitch, 2)
        )
        if pixel_format == RGB565:
            channels = (
                ((pixels >> 11) & 31) * 255 // 31,
                ((pixels >> 5) & 63) * 255 // 63,
                (pixels & 31) * 255 // 31,
            )
        else:
            channels = (
                ((pixels >> 10) & 31) * 255 // 31,
                ((pixels >> 5) & 31) * 255 // 31,
                (pixels & 31) * 255 // 31,
            )
    return np.stack(channels, axis=-1).astype(np.uint8)
