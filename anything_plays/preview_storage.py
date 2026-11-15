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
    return checked_preview_directory(
        base / ".config" / "anything-plays-32-preview" / "libretro-system",
        "anything-plays-32-preview",
    )


def checked_preview_directory(path, scope):
    """Refuse redirects inside the preview-specific storage tree.

    A settings, save or managed-core directory linked back to a stable
    installation defeats the preview's distinct path names. Inspect only
    components at and below *scope*: users can legitimately symlink their
    home or top-level APPDATA/XDG_DATA_HOME to another drive.
    """
    path = Path(path)
    parts = path.parts
    if scope not in parts:
        raise ValueError("Requested private storage is outside preview scope")
    marker = parts.index(scope)
    for level in range(marker + 1, len(parts) + 1):
        candidate = Path(*parts[:level])
        if candidate.is_symlink():
            raise ValueError("Preview storage must not link to another installation")
    return path
