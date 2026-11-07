"""Experimental single-window GameCube software-rendering Libretro backend.

Dolphin's Libretro core includes a Software Renderer that emits ordinary
CPU-owned RGBA video frames through retro_video_refresh_t. Unlike Dolphin's
default Hardware renderer, this mode does not require SET_HW_RENDER, so it can
use Anything Plays' existing game canvas and camera overlays.

**This is an integration path, not a supported-gameplay claim.**
Frame rates, console memory-card behavior, and hardware compatibility need
real-game testing before this mode can ship as complete. The binary and its
Dolphin Sys resources must be bundled at build time, never downloaded by users.

Upstream implementation:
libretro/dolphin Source/Core/DolphinLibretro/Video.cpp, Main.cpp, Video.h
"""

import ctypes as C
from pathlib import Path

from anything_plays.core_locator import _library_extension, _search_directories


# Select the core's actual CPU/software renderer, not its Null backend.
# Keeping settings minimal avoids overriding game-specific configurations.
SOFTWARE_OPTIONS = {
    b"dolphin_renderer": b"Software",
    b"dolphin_efb_scale": b"1",
}

# From DolphinLibretro/Input.cpp's GameCube RetroPad port map:
# A=8, B=0, X=9, Y=1, Start=3, Z=R(11), L=L2(12), R=R2(13).
# Analogue stick directions are generated from camera zones; C uses the
# standard right stick. D-pad events accompany the main stick for games
# that use either, while actual speed remains a fixed digital step.
GAMECUBE_BUTTON_IDS = {
    "B": 0, "Y": 1, "Start": 3, "A": 8, "X": 9,
    "Z": 11, "L": 12, "R": 13,
}
GAMECUBE_DPAD = {"Up": 4, "Down": 5, "Left": 6, "Right": 7}
GAMECUBE_AXES = {
    "Left": (0, 0, -28000), "Right": (0, 0, 28000),
    "Up": (0, 1, -28000), "Down": (0, 1, 28000),
    "C Left": (1, 0, -28000), "C Right": (1, 0, 28000),
    "C Up": (1, 1, -28000), "C Down": (1, 1, 28000),
}
GAMECUBE_INPUT = {
    **{name: ("digital", identity) for name, identity
       in {**GAMECUBE_BUTTON_IDS, **GAMECUBE_DPAD}.items()},
    **{name: ("stick", *axes) for name, axes in GAMECUBE_AXES.items()},
}


def gamecube_state(buttons):
    """Return both RetroPad digital buttons and analogue stick coordinates.

    The state is computed once per emulation frame and is never routed through
    global OS keyboard events or an external Dolphin process.
    """
    active = frozenset(buttons)
    result = {}
    for name in active:
        identifier = GAMECUBE_BUTTON_IDS.get(name)
        if identifier is not None:
            result[(1, 0, identifier)] = 1
        dpad = GAMECUBE_DPAD.get(name)
        if dpad is not None:
            result[(1, 0, dpad)] = 1

    for name, (index, axis, amount) in GAMECUBE_AXES.items():
        if name in active:
            identity = (5, index, axis)
            result[identity] = max(-32768, min(32767,
                result.get(identity, 0) + amount
            ))
    return {key: value for key, value in result.items() if value}


class RetroVariable(C.Structure):
    """Libretro retro_variable ABI: char *key, char *value."""

    _fields_ = [("key", C.c_char_p), ("value", C.c_char_p)]


def find_dolphin_core():
    """Locate a packaged Dolphin Libretro library, not the Dolphin app."""
    filename = "dolphin_libretro" + _library_extension()
    for directory in _search_directories():
        candidate = Path(directory) / filename
        if candidate.is_file():
            return str(candidate)
    return None


def packaged_dolphin_system_directory(core_path):
    """Return a validated read-only system root containing dolphin-emu/Sys.

    Dolphin requires the Sys data alongside its core; the frontend exposes
    the parent through RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY. This prevents
    a seemingly complete installer from silently depending on global Dolphin
    installation directories or asking the end user to install a ZIP.
    """
    if core_path is None:
        raise FileNotFoundError("Bundled Dolphin core is missing")
    root = Path(core_path).resolve().parent
    sys_folder = root / "dolphin-emu" / "Sys"
    if not sys_folder.is_dir():
        raise FileNotFoundError(
            "Bundled Dolphin system data is missing: dolphin-emu/Sys"
        )
    if not any(sys_folder.iterdir()):
        raise ValueError("Bundled Dolphin system data is empty")
    return root


class DolphinSoftwareOptions:
    """Supply Libretro core options for software frames without GPU contexts."""

    def __init__(self):
        # Keep Python byte strings referenced until the native core unloads.
        self.values = dict(SOFTWARE_OPTIONS)
        # DolphinLibretro/Common/Options.cpp calls CheckForUpdatedVariables
        # during its very first retro_init(). Without this first true, its
        # startup core-option cache is never populated, including requested
        # CPU mode, graphics renderer, and internal resolution.
        self._initial_options_pending = True

    def environment(self, command, data):
        """Return None when another part of the frontend should handle a call."""
        if command == 15 and data:  # RETRO_ENVIRONMENT_GET_VARIABLE
            request = C.cast(data, C.POINTER(RetroVariable))
            choice = self.values.get(request.contents.key)
            if choice is None:
                return False
            request.contents.value = choice
            return True
        if command == 16:  # SET_VARIABLES (core may supply option definitions)
            return True
        if command == 17 and data:  # GET_VARIABLE_UPDATE
            # Report the first startup configuration exactly once, then keep
            # the immutable native-session options stable until teardown.
            C.cast(data, C.POINTER(C.c_bool))[0] = self._initial_options_pending
            self._initial_options_pending = False
            return True
        if command == 52 and data:  # GET_CORE_OPTIONS_VERSION
            # Ask upstream Dolphin for the backward-compatible v0 options.
            C.cast(data, C.POINTER(C.c_uint))[0] = 0
            return True
        if command == 14:  # SET_HW_RENDER
            # Never claim a GPU context that Tk cannot actually provide.
            return False
        if command == 0x10000 | 44:  # Experimental shared GPU context request
            return False
        return None
