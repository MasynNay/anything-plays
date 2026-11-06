"""Locate a native Libretro core for the user's OS and selected console.

Prefer bundled cores and explicitly installed RetroArch locations. Do not
silently download a replacement at runtime: installed applications should work
offline and never execute an unreviewed native binary from the network.
"""

from pathlib import Path
import sys

from anything_plays.systems import SYSTEMS


def _library_extension():
    if sys.platform == "win32":
        return ".dll"
    if sys.platform == "darwin":
        return ".dylib"
    return ".so"


def _search_directories():
    source = Path(__file__).resolve().parent
    executable = Path(sys.executable).resolve().parent
    frozen = Path(getattr(sys, "_MEIPASS", source))
    folders = [
        source.parent / "cores",  # source checkout lives one level above the package
        source / "cores",
        executable / "cores",
        frozen / "cores",
        Path.home() / ".config" / "retroarch" / "cores",
        Path("/usr/lib/libretro"),
        Path("/usr/lib/x86_64-linux-gnu/libretro"),
        Path("/usr/local/lib/libretro"),
    ]
    if sys.platform == "darwin":
        folders.extend([
            Path.home() / "Library/Application Support/RetroArch/cores",
            Path("/Applications/RetroArch.app/Contents/Resources/cores"),
        ])
    return folders


def find_core(system="gba"):
    """Return the first matching native core path, or ``None`` if unavailable.

    ``KeyError`` for an unrecognized console is intentional: callers must not
    accidentally boot a ROM with the wrong system's emulator.
    """
    core = SYSTEMS[system].core
    extension = _library_extension()
    filenames = (f"{core}_libretro{extension}", f"libretro_{core}{extension}")
    for folder in _search_directories():
        for filename in filenames:
            candidate = folder / filename
            if candidate.is_file():
                return str(candidate)
    return None
