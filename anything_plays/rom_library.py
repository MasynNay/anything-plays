"""Find user-owned ROM files and their optional local cover art.

Browsing is deliberately bounded: the file chooser can point at a large drive,
so scanning must never follow directory symlinks or walk it indefinitely.
"""

import os
from pathlib import Path

MAX_DIRECTORIES = 2_500
MAX_GAMES = 2_000
COVER_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def scan_rom_directory(folder, extensions, cancelled=None):
    """Return a bounded, alphabetized list of matching ROMs below *folder*.

    The optional callback permits the UI to cancel a large scan immediately
    when someone changes or clears a mistakenly selected directory. No files
    are opened, modified, or followed through symlinks.
    """
    if not folder:
        return []

    directory = Path(folder)
    try:
        # followlinks=False only protects os.walk's *descendants*: a selected
        # symlinked root is still followed. Never scan outside the chosen
        # actual ROM directory, including during removable-drive churn.
        if directory.is_symlink() or not directory.is_dir():
            return []
    except OSError:
        return []

    supported = {suffix.lower() for suffix in extensions}
    games = []
    try:
        for index, (root, folders, files) in enumerate(
            os.walk(directory, followlinks=False), start=1
        ):
            if (cancelled is not None and cancelled()):
                return []
            if index > MAX_DIRECTORIES or len(games) >= MAX_GAMES:
                break
            folders[:] = sorted(
                folder for folder in folders
                if not folder.startswith(".")
                and not (Path(root) / folder).is_symlink()
            )
            for name in files:
                if cancelled is not None and cancelled():
                    return []
                path = Path(root) / name
                if path.suffix.lower() not in supported:
                    continue
                try:
                    # os.walk(followlinks=False) still lists symlinked files.
                    # Do not present external private files as game ROMs.
                    if path.is_symlink() or not path.is_file():
                        continue
                except OSError:
                    # A single inaccessible/corrupt directory entry should
                    # not hide the other valid games in the same library.
                    continue
                games.append(path)
                if len(games) >= MAX_GAMES:
                    break
    except OSError:
        # A removable or network volume can disappear mid-scan.
        pass
    return sorted(games, key=lambda path: (path.stem.casefold(), str(path).casefold()))


def find_cover_art(rom):
    """Look for artwork beside a ROM, preferring its filename over generic art."""
    rom = Path(rom)
    for stem in (rom.stem, "cover", "folder"):
        for extension in COVER_EXTENSIONS:
            candidate = rom.parent / (stem + extension)
            try:
                # Artwork loaders open the returned file later; never point
                # one at an image outside the selected local ROM directory.
                if not candidate.is_symlink() and candidate.is_file():
                    return candidate
            except OSError:
                continue
    return None
