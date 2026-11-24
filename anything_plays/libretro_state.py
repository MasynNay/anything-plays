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
import stat
from pathlib import Path
import tempfile
import time

from anything_plays.libretro_save import (
    _checked_native_save_path, _fallback_path, _user_save_directory,
)
from anything_plays.preview_storage import is_v32_preview, is_v33_candidate

MAGIC = b"AP30ST\0\1"
MAX_STATE_BYTES = 64 * 1024 * 1024
MAX_HEADER_BYTES = 4096
MAX_ROM_IDENTITY_BYTES = 32 * 1024 * 1024
MAX_CORE_IDENTITY_BYTES = 64 * 1024 * 1024


def _hash_file(path, limit):
    """Hash only the bounded regular file actually opened, not an earlier path."""
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError("Native game or emulator identity file unavailable")
    flags = (os.O_RDONLY | getattr(os, "O_BINARY", 0)
             | getattr(os, "O_NOFOLLOW", 0)
             | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(os.open(candidate, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or candidate.is_symlink():
            raise ValueError("Native game or emulator identity file unavailable")
        if not 0 < opened.st_size <= limit:
            raise ValueError("Native game or emulator identity file too large")
        digest = hashlib.sha256()
        remaining = opened.st_size
        while remaining:
            chunk = stream.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ValueError("Native game or emulator identity file changed")
            digest.update(chunk)
            remaining -= len(chunk)
        # A file can grow after fstat; never hash bytes beyond the limit or
        # silently accept an identity that changed partway through the read.
        if stream.read(1):
            raise ValueError("Native game or emulator identity file changed")
    return digest.hexdigest()


def state_file_path(rom, system):
    """One checkpoint per ROM identity path, separated from cartridge flash."""
    if system not in ("ngp", "ngpc"):
        raise ValueError("Native resume states are supported only for NGP/NGPC")
    base = _fallback_path(rom)
    return _checked_native_save_path(
        _user_save_directory() / "native-core" / "resume"
        / (system + "-" + base.stem + ".apstate")
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
        self._last_packet_size = None
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
        if self.path.is_symlink():
            raise ValueError("Refusing symlinked native resume file")
        _checked_native_save_path(self.path)
        if not self.path.is_file():
            return False
        private = is_v32_preview() or is_v33_candidate()
        flags = (os.O_RDONLY | getattr(os, "O_BINARY", 0)
                 | getattr(os, "O_NOFOLLOW", 0)
                 | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(os.open(self.path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            # The path may be replaced after is_file()/stat(): validate the
            # actual descriptor before reading even the first magic byte.
            if not stat.S_ISREG(opened.st_mode):
                raise ValueError("Native resume must be a regular file")
            if self.path.is_symlink():
                raise ValueError("Refusing symlinked native resume file")
            if private and opened.st_nlink != 1:
                raise ValueError("Preview recovery state cannot share a stable file")
            if opened.st_size > MAX_STATE_BYTES + MAX_HEADER_BYTES + 16:
                raise ValueError("Native resume file exceeds safe size limit")
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
        self._last_packet_size = opened.st_size
        return True

    def persist(self):
        """Checkpoint changed native machine state with atomic replace."""
        size = self._native_size()
        buffer = C.create_string_buffer(size)
        if not self._serialize(buffer, size):
            raise RuntimeError("Native core could not serialize recovery state")
        payload = buffer.raw
        digest = hashlib.sha256(payload).hexdigest()
        # A private QA checkpoint must never refer to another install,
        # including when its native payload is unchanged and would be skipped.
        private = is_v32_preview() or is_v33_candidate()
        if private:
            _checked_native_save_path(self.path)
            if self.path.is_symlink():
                raise ValueError("Refusing symlinked native resume")
            if self.path.is_file() and self.path.stat().st_nlink != 1:
                raise ValueError("Preview recovery state cannot share a stable file")
        if digest == self._last_digest and self._last_packet_size is not None:
            try:
                # Identical in-memory state is not proof that a removable
                # drive still holds a complete checkpoint. Repair deleted or
                # truncated files without hashing them on every tick.
                if (not self.path.is_symlink() and self.path.is_file()
                        and self.path.stat().st_size == self._last_packet_size):
                    return False
            except OSError:
                pass
        header = json.dumps(
            self._header(payload), sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(header) > MAX_HEADER_BYTES:
            raise ValueError("Native resume metadata exceeds limit")
        packet = MAGIC + len(header).to_bytes(4, "big") + header + payload
        # Revalidate every preview-specific parent just before touching disk.
        # Constructor-time path checks alone cannot protect from a later
        # symlinked native-core/resume directory.
        _checked_native_save_path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise ValueError("Refusing to replace symlinked native resume")
        if (private and self.path.is_file()
                and self.path.stat().st_nlink != 1):
            raise ValueError("Preview recovery state cannot share a stable file")
        # Never use a fixed .apstate.tmp name. Two independent instances
        # saving the same game could truncate one another's in-flight state
        # or unlink a buffer the other is about to publish. A unique sibling
        # on the same filesystem gives every writer its own complete packet.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=self.path.name + ".",
                suffix=".tmp",
                dir=self.path.parent,
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(packet)
                stream.flush()
                os.fsync(stream.fileno())
            # Concurrent Windows instances can briefly hold the destination
            # open while publishing their own checkpoint. Keep this writer's
            # unique, fully flushed temporary file intact and retry only
            # documented native access/sharing violations, with a strict
            # bounded delay. Other storage errors must fail immediately so
            # the previous committed checkpoint stays recoverable.
            for attempt in range(5):
                try:
                    os.replace(temporary, self.path)
                    break
                except PermissionError as exc:
                    code = getattr(exc, "winerror", None)
                    if (os.name != "nt" or code not in (5, 32, 33)
                            or attempt == 4):
                        raise
                    time.sleep(0.025 * (attempt + 1))
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
        self._last_digest = digest
        self._last_packet_size = len(packet)
        return True
