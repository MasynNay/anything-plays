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
    "genesis": System("genesis", "Sega Genesis / Mega Drive", "genesis_plus_gx", (".md", ".gen", ".smd", ".mdx", ".bin")),
    # Shares the already-bundled Genesis Plus GX library. No Sega CD firmware.
    "mastersystem": System("mastersystem", "Sega Master System", "genesis_plus_gx", (".sms", ".bms")),
    "gamegear": System("gamegear", "Sega Game Gear", "genesis_plus_gx", (".gg",)),
    "sg1000": System("sg1000", "Sega SG-1000", "genesis_plus_gx", (".sg",)),
    "atari2600": System("atari2600", "Atari 2600", "stella2014", (".a26", ".bin")),
    "atari7800": System("atari7800", "Atari 7800", "prosystem", (".a78",)),
    # PCE HuCards only; CD games need a separately licensed BIOS.
    "pce": System("pce", "TurboGrafx-16 / PC Engine (HuCard)", "mednafen_pce_fast", (".pce",)),
    "ngp": System("ngp", "Neo Geo Pocket", "mednafen_ngp", (".ngp", ".npc")),
    "ngpc": System("ngpc", "Neo Geo Pocket Color", "mednafen_ngp", (".ngc", ".ngpc")),
    "ws": System("ws", "WonderSwan", "mednafen_wswan", (".ws",)),
    "wsc": System("wsc", "WonderSwan Color", "mednafen_wswan", (".wsc",)),
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
