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


SYSTEMS = {
    "gb": System("gb", "Game Boy", "gambatte", (".gb",)),
    "gbc": System("gbc", "Game Boy Color", "gambatte", (".gbc",)),
    "gba": System("gba", "Game Boy Advance", "mgba", (".gba",)),
    "snes": System("snes", "Super Nintendo", "snes9x", (".sfc", ".smc")),
}

# Retain GBA as the default for users upgrading from the original application.
DEFAULT_SYSTEM = "gba"
