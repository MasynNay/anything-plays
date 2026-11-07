"""Supported consoles and their Libretro core and ROM file associations.

Keep these definitions independent of the UI so library filtering and core
selection share one source of truth.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class System:
    """Metadata required to browse ROMs and select an emulator core."""

    key: str
    title: str
    core: str
    extensions: tuple[str, ...]
    backend: str = "libretro"  # Embedded software-video core, or named external emulator.


SYSTEMS = {
    "gb": System("gb", "Game Boy", "mgba", (".gb",)),
    "gbc": System("gbc", "Game Boy Color", "mgba", (".gbc",)),
    "gba": System("gba", "Game Boy Advance", "mgba", (".gba",)),
    "snes": System("snes", "Super Nintendo", "snes9x", (".sfc", ".smc")),
    "nes": System("nes", "Nintendo Entertainment System", "fceumm", (".nes", ".unf", ".unif")),
    "genesis": System("genesis", "Sega Genesis / Mega Drive", "genesis_plus_gx", (".md", ".gen", ".smd", ".bin")),
    "n64": System("n64", "Nintendo 64 (RetroArch)", "mupen64plus_next", (".n64", ".z64", ".v64"), "retroarch"),
    "gamecube": System(
        "gamecube", "Nintendo GameCube", "dolphin",
        # Dolphin Libretro also supports homebrew .dol/.elf, TGC, WIA and
        # multi-disc playlists; include them in the same in-app ROM shelf.
        (".iso", ".gcm", ".rvz", ".gcz", ".ciso", ".dol", ".elf",
         ".tgc", ".wia", ".m3u"), "dolphin",
    ),
}

# Retain GBA as the default for users upgrading from the original application.
DEFAULT_SYSTEM = "gba"
