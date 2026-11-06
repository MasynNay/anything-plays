"""Load and safely write Libretro cartridge-backed SRAM files.

The original application's ``ROM-name.sav`` location is preserved, so moving
between versions does not lose existing game progress.
"""

import ctypes as C
import hashlib
from pathlib import Path

# Libretro SRAM is normally tiny. Reject corrupt/hostile reported sizes
# rather than allocating unlimited buffers while a game is running.
MAX_SAVE_RAM_BYTES = 64 * 1024 * 1024


class SaveRAM:
    """Read and write memory type 0 (RETRO_MEMORY_SAVE_RAM)."""

    def __init__(self, rom_path, get_data, get_size):
        self.path = Path(rom_path).with_suffix(".sav")
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
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_bytes(snapshot)
        temporary.replace(self.path)
        self._last_saved_digest = digest
        return True
