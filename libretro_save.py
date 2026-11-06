"""Load and safely write Libretro cartridge-backed SRAM files.

The original application's ``ROM-name.sav`` location is preserved, so moving
between versions does not lose existing game progress.
"""

import ctypes as C
from pathlib import Path


class SaveRAM:
    """Read and write memory type 0 (RETRO_MEMORY_SAVE_RAM)."""

    def __init__(self, rom_path, get_data, get_size):
        self.path = Path(rom_path).with_suffix(".sav")
        self.get_data = get_data
        self.get_size = get_size

    def _memory(self):
        pointer = self.get_data(0)
        size = self.get_size(0)
        return pointer, size

    def restore(self):
        pointer, size = self._memory()
        if pointer and size and self.path.is_file():
            data = self.path.read_bytes()
            C.memmove(pointer, data, min(size, len(data)))

    def persist(self):
        pointer, size = self._memory()
        if pointer and size:
            # Replace the file only after the entire SRAM snapshot is written.
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_bytes(C.string_at(pointer, size))
            temporary.replace(self.path)
