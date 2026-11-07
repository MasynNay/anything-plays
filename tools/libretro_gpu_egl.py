"""Legacy import compatibility for the GameCube EGL diagnostic tools.

The real implementation lives under anything_plays/ so PyInstaller includes
it in the desktop application. This facade must stay lightweight.
"""
import sys
from anything_plays.libretro_gpu_egl import (
    EGLFrameHost, HardwareRenderCallback, bounded_dimensions,
)
