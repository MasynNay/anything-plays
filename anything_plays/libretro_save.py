"""Load and safely write Libretro cartridge-backed SRAM files.

The original application's ``ROM-name.sav`` location is preserved, so moving
between versions does not lose existing game progress.
"""

import ctypes as C
import hashlib
import os
from pathlib import Path
import re
import sys
import tempfile

# Libretro SRAM is normally tiny. Reject corrupt/hostile reported sizes
# rather than allocating unlimited buffers while a game is running.
MAX_SAVE_RAM_BYTES = 64 * 1024 * 1024


def _user_save_directory():
    """Use a user-writable data directory, not the application's install."""
    if sys.platform == "win32":
        root = os.environ.get("APPDATA")
        base = Path(root) if root else Path.home() / "AppData" / "Roaming"
        return base / "AnythingPlays" / "Saves"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "AnythingPlays" / "Saves"
    root = os.environ.get("XDG_DATA_HOME")
    base = Path(root) if root and Path(root).is_absolute() else Path.home() / ".local" / "share"
    return base / "anything-plays" / "saves"


def _fallback_path(rom_path):
    rom = Path(rom_path).resolve()
    key = str(rom).casefold() if sys.platform == "win32" else str(rom)
    digest = hashlib.sha256(os.fsencode(key)).hexdigest()[:20]
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", rom.stem).strip("_")[:48] or "game"
    return _user_save_directory() / (stem + "-" + digest + ".sav")



def native_core_save_directory(rom_path, system):
    """Provide writable native save paths independent from installed emulator cores.

    Beetle NeoPop does not expose its cartridge flash through Libretro SRAM:
    it reads and writes <ROM-stem>.flash under GET_SAVE_DIRECTORY itself.
    Reusing a global save directory would make games in different ROM
    libraries with the same filename overwrite each other's progress.
    Keep the directory under the user's writable application data folder,
    not next to a ROM on a removable/read-only drive.
    """
    if system == "gamecube":
        # Dolphin's virtual memory cards are shared at console level, like
        # physical GameCube cards; keep them stable across game/core updates.
        # This must be a user-owned platform data path, not installed Sys.
        return _user_save_directory() / "native-core" / "gamecube"
    if system not in ("ngp", "ngpc"):
        raise ValueError("No native save directory defined for this core")
    fallback = _fallback_path(rom_path)
    return fallback.parent / "native-core" / "neo-geo-pocket" / fallback.stem


class SaveRAM:
    """Read and write memory type 0 (RETRO_MEMORY_SAVE_RAM)."""

    def __init__(self, rom_path, get_data, get_size):
        self.path = Path(rom_path).with_suffix(".sav")
        self.legacy_path = self.path
        self.fallback_path = _fallback_path(rom_path)
        self.get_data = get_data
        self.get_size = get_size
        # A fixed-size digest prevents unbounded snapshot history and avoids
        # rewriting identical save RAM every few seconds for days.
        self._last_saved_digest = None

    def _memory(self):
        pointer = self.get_data(0)
        size = int(self.get_size(0))
        if size < 0 or size > MAX_SAVE_RAM_BYTES:
            raise ValueError(
                f"Libretro save RAM size exceeds the {MAX_SAVE_RAM_BYTES // (1024 * 1024)} MiB limit"
            )
        return pointer, size

    def restore(self):
        pointer, size = self._memory()
        # Once the read-only ROM library has a newer user-owned save,
        # never replace it by an older legacy file from beside the ROM.
        if pointer and size and self.fallback_path.is_file():
            self.path = self.fallback_path
        if pointer and size and self.path.is_file():
            # Read only as much as this core can hold, plus one byte to
            # detect oversized/partial legacy saves. A corrupt multi-GB save
            # must not exhaust memory before gameplay even begins.
            with self.path.open("rb") as stream:
                data = stream.read(size + 1)
            C.memmove(pointer, data, min(size, len(data)))
            # An incomplete or oversized legacy .sav must be normalized on
            # the next safe persist, rather than mistaken for a valid full
            # snapshot and skipped forever.
            if len(data) == size:
                restored = C.string_at(pointer, size)
                self._last_saved_digest = hashlib.blake2b(
                    restored, digest_size=16
                ).digest()
            else:
                self._last_saved_digest = None

    def persist(self):
        """Write only changed SRAM, replacing a complete snapshot atomically.

        Return True if a file was written and False when nothing changed.
        Keeping a single digest (not every past save) bounds memory use even
        during weeks of uninterrupted gameplay.
        """
        pointer, size = self._memory()
        if not pointer or not size:
            return False
        snapshot = C.string_at(pointer, size)
        digest = hashlib.blake2b(snapshot, digest_size=16).digest()
        if digest == self._last_saved_digest and self.path.is_file():
            return False
        destination = self.path
        try:
            self._write_atomic(destination, snapshot,
                               create_directory=(destination == self.fallback_path))
        except OSError:
            if destination == self.fallback_path:
                raise
            destination = self.fallback_path
            self._write_atomic(destination, snapshot, create_directory=True)
        self.path = destination
        self._last_saved_digest = digest
        return True

    @staticmethod
    def _write_atomic(destination, snapshot, *, create_directory):
        if create_directory:
            destination.parent.mkdir(parents=True, exist_ok=True)
        elif not destination.parent.is_dir():
            # Do not accidentally recreate an unplugged removable ROM mount.
            raise FileNotFoundError("The ROM directory is unavailable")
        # Two independent app versions can open the same user ROM. A fixed
        # <ROM>.sav.tmp path lets their writes overwrite each other and one
        # process delete another process's in-flight snapshot. Use a private
        # temporary file in the SAME directory for atomic rename semantics.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=destination.name + ".", suffix=".tmp",
                dir=destination.parent, delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(snapshot)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            # A failed or interrupted save must leave the previous committed
            # .sav untouched. Never unlink another writer's temporary file.
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
