"""Validate Beetle NeoPop's native .flash container before loading cartridges.

The upstream C parser trusts header.total_file_length and block_count. A
truncated, damaged or oversized user save could otherwise cause a large native
allocation or an out-of-bounds read. This module validates the actual
little-endian native structure sizes used by NeoPop on all four v3 targets.

It never modifies saved game progress, never declares gameplay restoration
successful, and does not attempt to repair a damaged save automatically.
"""

import hashlib
from pathlib import Path
import struct


FLASH_MAGIC = 0x0053
MAX_FLASH_BLOCKS = 256
MAX_FLASH_FILE_BYTES = 8 * 1024 * 1024
HEADER = struct.Struct("<HHI")  # valid_flash_id, block_count, file_length
BLOCK_HEADER = struct.Struct("<IH2x")  # address, length, 2 C padding bytes


class InvalidNeoPopFlash(ValueError):
    """Native NeoPop save is malformed; fail before passing it to the C core."""


def inspect_neopop_flash(path):
    """Read and validate one native NeoPop flash; return bounded diagnostics.

    The native core uses the ROM basename to construct '<basename>.flash'
    inside RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY. A missing file means an
    unplayed cartridge, not a validation error.
    """
    target = Path(path)
    if target.is_symlink():
        raise InvalidNeoPopFlash("Neo Geo Pocket flash save cannot be a symlink")
    if not target.exists():
        return None
    if not target.is_file():
        raise InvalidNeoPopFlash("Neo Geo Pocket flash save is not a regular file")
    actual_size = target.stat().st_size
    if actual_size < HEADER.size or actual_size > MAX_FLASH_FILE_BYTES:
        raise InvalidNeoPopFlash("Neo Geo Pocket flash save exceeds safe size bounds")
    # Size checked before opening: no unbounded read of a corrupt native save.
    with target.open("rb") as source:
        data = source.read(MAX_FLASH_FILE_BYTES + 1)
    if len(data) != actual_size:
        raise InvalidNeoPopFlash("Neo Geo Pocket flash save changed during validation")
    try:
        magic, block_count, declared_size = HEADER.unpack_from(data)
    except struct.error as exc:
        raise InvalidNeoPopFlash("Neo Geo Pocket flash header is incomplete") from exc
    if magic != FLASH_MAGIC:
        raise InvalidNeoPopFlash("Neo Geo Pocket flash header has invalid magic")
    if not 1 <= block_count <= MAX_FLASH_BLOCKS:
        raise InvalidNeoPopFlash("Neo Geo Pocket flash block count is invalid")
    if declared_size != actual_size:
        raise InvalidNeoPopFlash("Neo Geo Pocket flash header size disagrees with file")
    pos = HEADER.size
    blocks = []
    for index in range(block_count):
        if pos + BLOCK_HEADER.size > len(data):
            raise InvalidNeoPopFlash("Neo Geo Pocket flash block header truncated")
        address, length = BLOCK_HEADER.unpack_from(data, pos)
        pos += BLOCK_HEADER.size
        if length == 0 or pos + length > len(data):
            raise InvalidNeoPopFlash("Neo Geo Pocket flash block data truncated")
        if address > 0xFFFFFF or address + length > 0x1000000:
            raise InvalidNeoPopFlash("Neo Geo Pocket flash address outside cartridge bus")
        blocks.append({"address": address, "bytes": length})
        pos += length
    if pos != len(data):
        raise InvalidNeoPopFlash("Neo Geo Pocket flash contains unexpected trailing bytes")
    return {
        "file_bytes": actual_size,
        "block_count": block_count,
        "blocks": blocks,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def check_cartridge_flash(rom_path, save_directory):
    """Reject malformed native flash *before* NeoPop retro_load_game."""
    rom = Path(rom_path)
    return inspect_neopop_flash(Path(save_directory) / (rom.stem + ".flash"))
