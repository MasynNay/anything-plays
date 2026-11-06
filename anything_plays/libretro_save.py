"""Load and safely write Libretro cartridge-backed SRAM files.

The original application's ``ROM-name.sav`` location is preserved, so moving
between versions does not lose existing game progress.
"""

import ctypes as C
import hashlib
from pathlib import Path


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
        size = self.get_size(0)
        return pointer, size

    def restore(self):
        pointer, size = self._memory()
        if pointer and size and self.path.is_file():
            data = self.path.read_bytes()
            C.memmove(pointer, data, min(size, len(data)))
            restored = C.string_at(pointer, size)
            self._last_saved_digest = hashlib.blake2b(
                restored, digest_size=16
            ).digest()

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
