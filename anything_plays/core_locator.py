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
    # The independently reviewed full 3.0 alternative installer records
    # genuine original native file/source identities, never aliases them to
    # the old noncommercial emulator filenames. A corrupt marker fails
    # CLOSED rather than falling through to another native implementation.
    if system in ("snes", "genesis", "mastersystem", "gamegear", "sg1000", "pce",
                  "nes", "atari2600", "atari7800", "ngp", "ngpc", "ws", "wsc"):
        from anything_plays.v30_approved_core_map import find_approved_core
        try:
            approved, path = find_approved_core(
                _search_directories(), system, _library_extension())
        except (OSError, ValueError, TypeError, KeyError):
            return None
        if approved:
            return path
    # Research-only complete offline preview, never the public stable build:
    # a marker and exact source-built GPL images must be present in the
    # installed bundle. No implicit downloads and no fallback to NC cores.
    from anything_plays.v30_gpl_trial import find_trial_core
    if system in ("snes", "genesis", "mastersystem", "gamegear", "sg1000"):
        try:
            trial, trial_path = find_trial_core(
                _search_directories(), system, _library_extension())
        except (OSError, ValueError, TypeError):
            return None
        if trial:
            return trial_path
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
                if core == "dolphin":
                    codehandler = folder / "dolphin-emu" / "Sys" / "codehandler.bin"
                    try:
                        if not codehandler.is_file() or not codehandler.stat().st_size:
                            continue
                    except OSError:
                        # Bad directory modes on root-owned package contents
                        # must never prevent the main UI from starting.
                        continue
                return str(candidate)
    return None
