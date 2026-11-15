"""Crash-safe zone PNG cache with isolated storage for 3.2 previews.

Downloading a zone illustration is an explicit user action. Public and
older 3.1 identities retain their previous cache path; unreleased 3.2 never
reads or writes it. Files are staged as complete PNGs before replacement.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from anything_plays.build_identity import current_identity
from anything_plays.preview_storage import checked_preview_directory
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM


def zone_art_cache_path(preferences_path, *, identity=None, home=None, system=None):
    """Locate console-scoped artwork without opening any files or devices.

    Keep the original private 3.2 filename when a previous caller supplies
    no console; all new preview UI downloads include the current console.
    """
    identity = current_identity() if identity is None else identity
    if identity["channel"] != "v32_preview":
        home = Path.home() if home is None else Path(home)
        return home / ".config" / "anything-plays" / "zone-art.png"

    prefs = Path(preferences_path)
    if (prefs.name != "preferences.json"
            or prefs.parent.name != identity["settings_namespace"]):
        raise ValueError("3.2 artwork requires private preview preferences")
    if system is not None and system not in BUTTONS_BY_SYSTEM:
        raise ValueError("Unknown console in preview artwork cache.")
    filename = f"zone-art-{system}.png" if system else "zone-art.png"
    return checked_preview_directory(
        prefs.with_name(filename), identity["settings_namespace"]
    )


def _check_cache_target(target, *, preview):
    if not preview:
        return
    # Reject even dangling symlinks. A hardlink could alias a stable cache.
    if target.is_symlink():
        raise ValueError("Preview zone artwork cannot be symlinked")
    if target.exists():
        if not target.is_file() or target.stat().st_nlink != 1:
            raise ValueError("Preview artwork must be an independent regular file")


def save_cached_zone_art(
    image, preferences_path, *, identity=None, home=None, system=None,
):
    """Atomically publish an already-decoded, resized PNG image.

    The caller enforces the 5 MiB source download limit and thumbnail size.
    An I/O error cannot replace the previous complete PNG with partial data.
    """
    identity = current_identity() if identity is None else identity
    preview = identity["channel"] == "v32_preview"
    target = zone_art_cache_path(
        preferences_path, identity=identity, home=home, system=system
    )
    _check_cache_target(target, preview=preview)
    target.parent.mkdir(parents=True, exist_ok=True)
    if preview:
        checked_preview_directory(target, identity["settings_namespace"])
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b", prefix=".zone-art-", suffix=".tmp",
            dir=target.parent, delete=False,
        ) as stream:
            temporary = Path(stream.name)
            image.save(stream, format="PNG")
            stream.flush()
            os.fsync(stream.fileno())
        if preview:
            checked_preview_directory(target, identity["settings_namespace"])
        _check_cache_target(target, preview=preview)
        os.replace(temporary, target)
        return target
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
