"""Supported systems and per-system library/core configuration."""
from dataclasses import dataclass

@dataclass(frozen=True)
class System:
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
DEFAULT_SYSTEM = "gba"
