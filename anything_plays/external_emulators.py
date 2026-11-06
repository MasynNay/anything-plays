"""Safely launch separately installed 3D emulators without shell injection.

Anything Plays owns game discovery and launch. RetroArch or Dolphin owns
hardware graphics, analog controllers and save states. Webcam tracking does
not currently control external emulator processes.
"""
from pathlib import Path
import shutil
import subprocess
import sys

from anything_plays.core_locator import find_core
from anything_plays.systems import SYSTEMS


class ExternalLaunchError(RuntimeError):
    pass


def find_external_emulator(system, override=None):
    if system not in ("n64", "gamecube"):
        raise ValueError("Unsupported external backend")
    if override:
        executable = Path(override).expanduser()
        if not executable.is_file():
            raise ExternalLaunchError(f"Configured emulator executable not found: {executable}")
        return executable
    if system == "n64":
        names = ("RetroArch.exe", "retroarch.exe", "retroarch") if sys.platform == "win32" else ("retroarch", "RetroArch")
        candidates = (
            Path("/Applications/RetroArch.app/Contents/MacOS/RetroArch"),
            Path("C:/Program Files/RetroArch/retroarch.exe"),
            Path("C:/Program Files (x86)/RetroArch/retroarch.exe"),
        )
    else:
        names = ("Dolphin.exe", "dolphin-emu", "dolphin-emu-qt2", "Dolphin")
        candidates = (
            Path("/Applications/Dolphin.app/Contents/MacOS/Dolphin"),
            Path("C:/Program Files/Dolphin/Dolphin.exe"),
            Path("C:/Program Files (x86)/Dolphin/Dolphin.exe"),
        )
    for name in names:
        location = shutil.which(name)
        if location:
            return Path(location)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    label = "RetroArch with Mupen64Plus-Next" if system == "n64" else "Dolphin"
    raise ExternalLaunchError(
        f"{label} is not installed or configured. Install the official emulator "
        "and select its executable in Anything Plays settings."
    )


def command_for(system, game, *, executable=None, n64_core=None, fullscreen=False, borderless=False, network_config=None, dolphin_user=None):
    """Return a safe argument vector, never a shell string."""
    if system not in ("n64", "gamecube"):
        raise ValueError("Only external systems can use this launcher")
    rom = Path(game).expanduser().resolve()
    if not rom.is_file() or rom.suffix.lower() not in SYSTEMS[system].extensions:
        raise ExternalLaunchError("Choose an existing, compatible game file")
    exe = find_external_emulator(system, executable)
    if system == "gamecube":
        args = [str(exe), "--batch"]
        if dolphin_user is not None:
            user_dir = Path(dolphin_user).expanduser()
            if not user_dir.is_dir():
                raise ExternalLaunchError("GameCube controller user directory is missing")
            args.append("--user=" + str(user_dir))
        # Dolphin's command-line overrides affect only this launch, not saved
        # emulator preferences. Honor fullscreen and borderless selections.
        if fullscreen or borderless:
            args.append("--config=Dolphin.Display.Fullscreen=True")
        if borderless:
            args.append("--config=Graphics.Settings.BorderlessFullscreen=True")
        return [*args, "--exec=" + str(rom)]
    core = n64_core or find_core("n64")
    if core is None or not Path(core).expanduser().is_file():
        raise ExternalLaunchError(
            "Install the Mupen64Plus-Next core in RetroArch, or select "
            "a native N64 graphics core in Anything Plays. "
            "N64 cannot run in the embedded software-only video frontend."
        )
    args = [str(exe), "-L", str(Path(core).expanduser().resolve()), str(rom)]
    if network_config is not None:
        config = Path(network_config).expanduser()
        if not config.is_file():
            raise ExternalLaunchError("Missing temporary RetroArch network gamepad config")
        args[1:1] = ["--appendconfig", str(config)]
    if fullscreen:
        args.insert(1, "--fullscreen")
    return args


def launch(system, game, *, executable=None, n64_core=None, fullscreen=False, borderless=False, network_config=None, dolphin_user=None):
    command = command_for(system, game, executable=executable,
                          n64_core=n64_core, fullscreen=fullscreen, borderless=borderless, network_config=network_config, dolphin_user=dolphin_user)
    try:
        return subprocess.Popen(command, shell=False)
    except OSError as exc:
        raise ExternalLaunchError(f"Could not start external emulator: {exc}") from exc
