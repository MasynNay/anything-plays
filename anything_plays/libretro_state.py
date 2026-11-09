"""Bounded, atomic Libretro recovery states for Neo Geo Pocket games.

Beetle NeoPop writes its own cartridge flash files, but a core's flash
writer can fail to reproduce some homebrew saves across cold restarts.
Retaining a verified last-session native save-state adds a separate recovery
layer. The native flash directory is not replaced or modified.

Auto-resume is limited to NGP/NGPC. Core-specific serialized states are
accepted ONLY for identical ROM bytes and identical native emulator bytes.
A corrupt, oversized or incompatible state never gets passed to C code.
"""
from __future__ import annotations

import ctypes as C
import hashlib
import json
import os
from pathlib import Path

from anything_plays.libretro_save import _fallback_path, _user_save_directory

MAGIC = b"AP30ST\0\1"
MAX_STATE_BYTES = 64 * 1024 * 1024
MAX_HEADER_BYTES = 4096
MAX_ROM_IDENTITY_BYTES = 32 * 1024 * 1024
MAX_CORE_IDENTITY_BYTES = 64 * 1024 * 1024


def _hash_file(path, limit):
    candidate = Path(path)
    if not candidate.is_file() or candidate.is_symlink():
        raise ValueError("Native game or emulator identity file unavailable")
    length = candidate.stat().st_size
    if not 0 < length <= limit:
        raise ValueError("Native game or emulator identity file too large")
    digest = hashlib.sha256()
    with candidate.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def state_file_path(rom, system):
    """One checkpoint per ROM identity path, separated from cartridge flash."""
    if system not in ("ngp", "ngpc"):
        raise ValueError("Native resume states are supported only for NGP/NGPC")
    base = _fallback_path(rom)
    return _user_save_directory() / "native-core" / "resume" / (
        system + "-" + base.stem + ".apstate"
    )


class LibretroRecoveryState:
    def __init__(self, rom, system, core_path, native):
        if system not in ("ngp", "ngpc"):
            raise ValueError("No full-state checkpoint for this system")
        self.path = state_file_path(rom, system)
        self.rom_sha = _hash_file(rom, MAX_ROM_IDENTITY_BYTES)
        self.core_sha = _hash_file(core_path, MAX_CORE_IDENTITY_BYTES)
        self.system = system
        self._last_digest = None
        self._size = getattr(native.library, "retro_serialize_size", None)
        self._serialize = getattr(native.library, "retro_serialize", None)
        self._restore = getattr(native.library, "retro_unserialize", None)
        if any(fn is None for fn in (
            self._size, self._serialize, self._restore,
        )):
            raise RuntimeError("Native core does not support recovery states")
        self._size.argtypes = []
        self._size.restype = C.c_size_t
        self._serialize.argtypes = [C.c_void_p, C.c_size_t]
        self._serialize.restype = C.c_bool
        self._restore.argtypes = [C.c_void_p, C.c_size_t]
        self._restore.restype = C.c_bool

    def _native_size(self):
        length = int(self._size())
        if not 0 < length <= MAX_STATE_BYTES:
            raise ValueError("Unusable/oversized native serialized state")
        return length

    def _header(self, payload):
        return {
            "format": 1,
            "system": self.system,
            "rom_sha256": self.rom_sha,
            "core_sha256": self.core_sha,
            "bytes": len(payload),
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
        }

    def restore(self):
        """False for a new game; reject corruption before native unserialize."""
        if not self.path.is_file():
            return False
        if self.path.is_symlink():
            raise ValueError("Refusing symlinked native resume file")
        if self.path.stat().st_size > MAX_STATE_BYTES + MAX_HEADER_BYTES + 16:
            raise ValueError("Native resume file exceeds safe size limit")
        with self.path.open("rb") as stream:
            if stream.read(len(MAGIC)) != MAGIC:
                raise ValueError("Native resume header not recognized")
            header_size = int.from_bytes(stream.read(4), "big")
            if not 2 <= header_size <= MAX_HEADER_BYTES:
                raise ValueError("Native resume metadata has invalid length")
            header_bytes = stream.read(header_size)
            if len(header_bytes) != header_size:
                raise ValueError("Truncated native resume metadata")
            metadata = json.loads(header_bytes.decode("utf-8"))
            if not isinstance(metadata, dict):
                raise ValueError("Native resume metadata malformed")
            expected = self._native_size()
            if (metadata.get("format") != 1
                    or metadata.get("system") != self.system
                    or metadata.get("rom_sha256") != self.rom_sha
                    or metadata.get("core_sha256") != self.core_sha
                    or metadata.get("bytes") != expected):
                raise ValueError(
                    "Native resume belongs to different ROM/core or size"
                )
            payload = stream.read(expected + 1)
            if len(payload) != expected:
                raise ValueError("Native resume payload truncated/oversized")
        digest = hashlib.sha256(payload).hexdigest()
        if digest != metadata.get("payload_sha256"):
            raise ValueError("Native resume payload checksum mismatch")
        buffer = C.create_string_buffer(payload)
        if not self._restore(buffer, len(payload)):
            raise RuntimeError("Native core rejected compatible recovery state")
        self._last_digest = digest
        return True

    def persist(self):
        """Checkpoint changed native machine state with atomic replace."""
        size = self._native_size()
        buffer = C.create_string_buffer(size)
        if not self._serialize(buffer, size):
            raise RuntimeError("Native core could not serialize recovery state")
        payload = buffer.raw
        digest = hashlib.sha256(payload).hexdigest()
        if digest == self._last_digest and self.path.is_file():
            return False
        header = json.dumps(
            self._header(payload), sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(header) > MAX_HEADER_BYTES:
            raise ValueError("Native resume metadata exceeds limit")
        packet = MAGIC + len(header).to_bytes(4, "big") + header + payload
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise ValueError("Refusing to replace symlinked native resume")
        temp = self.path.with_suffix(".apstate.tmp")
        try:
            if temp.is_symlink():
                raise ValueError("Refusing symlinked temporary resume file")
            with temp.open("wb") as stream:
                stream.write(packet)
                stream.flush()
                os.fsync(stream.fileno())
            temp.replace(self.path)
        finally:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
        self._last_digest = digest
        return True
