"""Locate verified updated or bundled Libretro cores for each console.

Normal Anything Plays installations require NO external emulator or RetroArch
core directories. External locations remain explicitly developer-only and
can never be a hidden dependency of a release installer.
"""

from pathlib import Path
import os
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
    ]
    if sys.platform == "darwin":
        # Keep camera/Libretro payloads under Contents/Resources, where macOS
        # signing seals the files as resources without rewriting dylib hashes.
        folders.insert(0, executable.parent / "Resources" / "cores")
    if os.environ.get("AP_V21_DEVELOPER_EXTERNAL") == "1":
        # Explicit diagnostic opt-in only, never a user-facing prerequisite.
        folders.extend([
            Path.home() / ".config" / "retroarch" / "cores",
            Path("/usr/lib/libretro"),
            Path("/usr/lib/x86_64-linux-gnu/libretro"),
            Path("/usr/local/lib/libretro"),
        ])
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
    # Verified user-owned core packs take precedence without mutating the
    # signed/read-only application bundle. Corruption falls back to bundle.
    from anything_plays.core_packs import managed_core_path
    updated = managed_core_path(core)
    if updated is not None:
        return updated
    extension = _library_extension()
    filenames = (f"{core}_libretro{extension}", f"libretro_{core}{extension}")
    for folder in _search_directories():
        for filename in filenames:
            candidate = folder / filename
            if candidate.is_file():
                return str(candidate)
    return None
