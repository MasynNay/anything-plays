"""Storage boundaries for unreleased 3.2 test builds.

The build identity, not an untrusted user-supplied path, determines whether
native saves, system files and downloaded core packs must be isolated from
stable installs. Nothing in this module opens devices or writes any files.
"""

from pathlib import Path

from anything_plays.build_identity import current_identity


def is_v32_preview():
    """True only for the explicitly selected source or frozen 3.2 preview."""
    return current_identity()["channel"] == "v32_preview"


def preview_system_directory(home=None):
    """A native Libretro system directory never shared with stable versions."""
    base = Path.home() if home is None else Path(home)
    return base / ".config" / "anything-plays-32-preview" / "libretro-system"
