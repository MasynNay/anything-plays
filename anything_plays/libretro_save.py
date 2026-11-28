"""Load and safely write Libretro cartridge-backed SRAM files.

The original application's ``ROM-name.sav`` location is preserved, so moving
between versions does not lose existing game progress.
"""

import ctypes as C
import hashlib
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time

from anything_plays.preview_storage import (
    is_v32_preview, is_v33_candidate, checked_preview_directory,
)

# Libretro SRAM is normally tiny. Reject corrupt/hostile reported sizes
# rather than allocating unlimited buffers while a game is running.
MAX_SAVE_RAM_BYTES = 64 * 1024 * 1024


def _save_file_signature(info):
    """Bounded metadata identity for one committed regular save file.

    A same-size cloud-sync replacement or in-place mutation must not be
    mistaken for the previously written bytes. No paths or file contents
    enter this token; ctime also detects edits that preserve mtime.
    """
    return (
        info.st_dev, info.st_ino, info.st_size,
        info.st_mtime_ns, info.st_ctime_ns,
    )


def _user_save_directory():
    """Writable user saves; isolated private QA never reads stable progress."""
    preview = is_v32_preview() or is_v33_candidate()
    scope = "Preview-3.3" if is_v33_candidate() else "Preview-3.2"
    linux_scope = "3.3-candidate" if is_v33_candidate() else "3.2-preview"
    if sys.platform == "win32":
        root = os.environ.get("APPDATA")
        base = Path(root) if root else Path.home() / "AppData" / "Roaming"
        return (checked_preview_directory(
            base / "AnythingPlays" / scope / "Saves", scope,
        ) if preview else base / "AnythingPlays" / "Saves")
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "AnythingPlays"
        return (checked_preview_directory(
            base / scope / "Saves", scope,
        ) if preview else base / "Saves")
    root = os.environ.get("XDG_DATA_HOME")
    base = Path(root) if root and Path(root).is_absolute() else Path.home() / ".local" / "share"
    return (checked_preview_directory(
        base / "anything-plays" / linux_scope / "saves", linux_scope,
    ) if preview else base / "anything-plays" / "saves")


def _fallback_path(rom_path):
    rom = Path(rom_path).resolve()
    key = str(rom).casefold() if sys.platform == "win32" else str(rom)
    digest = hashlib.sha256(os.fsencode(key)).hexdigest()[:20]
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", rom.stem).strip("_")[:48] or "game"
    return _user_save_directory() / (stem + "-" + digest + ".sav")



def _checked_native_save_path(path):
    """Validate every native-core child within preview's private save scope.

    The top-level save root alone is insufficient: an existing native-core,
    resume, neo-geo-pocket or ROM-specific child may be a symlink pointing
    directly into a public stable save directory. Leave stable layouts alone.
    """
    path = Path(path)
    if not (is_v32_preview() or is_v33_candidate()):
        return path
    scope = ("Preview-3.3" if is_v33_candidate() else "Preview-3.2")
    if sys.platform not in ("win32", "darwin"):
        scope = "3.3-candidate" if is_v33_candidate() else "3.2-preview"
    return checked_preview_directory(path, scope)


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
        return _checked_native_save_path(
            _user_save_directory() / "native-core" / "gamecube"
        )
    if system not in ("ngp", "ngpc"):
        raise ValueError("No native save directory defined for this core")
    fallback = _fallback_path(rom_path)
    return _checked_native_save_path(
        fallback.parent / "native-core" / "neo-geo-pocket" / fallback.stem
    )


class SaveRAM:
    """Read and write memory type 0 (RETRO_MEMORY_SAVE_RAM)."""

    def __init__(self, rom_path, get_data, get_size):
        self.legacy_path = Path(rom_path).with_suffix(".sav")
        self.fallback_path = _fallback_path(rom_path)
        # Stable versions preserve the traditional ROM-adjacent save path.
        # Only the unreleased 3.2 preview starts in its own user data store.
        # This also means Restore NEVER reads an existing stable .sav file.
        self.path = (self.fallback_path
                     if (is_v32_preview() or is_v33_candidate()) else self.legacy_path)
        self.get_data = get_data
        self.get_size = get_size
        # A fixed-size digest prevents unbounded snapshot history and avoids
        # rewriting identical save RAM every few seconds for days.
        self._last_saved_digest = None
        # A digest of unchanged native SRAM says nothing about a file that
        # another app/backup sync replaced with different equal-size bytes.
        # Remember only the metadata of our last completed disk checkpoint.
        self._last_saved_file_signature = None

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
        if pointer and size and (is_v32_preview() or is_v33_candidate()):
            # A preview save may be created/replaced after the SaveRAM
            # constructor ran. Refuse linked destinations before reading.
            _user_save_directory()
            if self.path.is_symlink():
                raise ValueError("Preview save must not link to a stable file")
            if self.path.is_file() and self.path.stat().st_nlink != 1:
                # A regular-looking hardlink can point to an existing
                # stable SRAM file. Never import someone else's progress
                # through a linked preview destination.
                raise ValueError("Preview save must not share a stable file")
        if pointer and size and self.path.is_file():
            # Validate the *opened descriptor*, not only the earlier path:
            # another process can replace a save with a pipe or device after
            # is_file(). Nonblocking open prevents hanging on a swapped FIFO.
            # Private preview paths also refuse late symlink replacements on
            # platforms with O_NOFOLLOW. Public/stable users may deliberately
            # keep a linked .sav in cloud storage; preserve that contract.
            private = is_v32_preview() or is_v33_candidate()
            flags = (os.O_RDONLY | getattr(os, "O_BINARY", 0)
                     | getattr(os, "O_NONBLOCK", 0))
            if private:
                flags |= getattr(os, "O_NOFOLLOW", 0)
            with os.fdopen(os.open(self.path, flags), "rb") as stream:
                opened = os.fstat(stream.fileno())
                if not stat.S_ISREG(opened.st_mode):
                    raise ValueError("Saved game must be a regular file")
                if private and opened.st_nlink != 1:
                    # A hardlink may be swapped into the private directory
                    # after the initial path-based check. Do not import
                    # another installed version's cartridge progress.
                    raise ValueError("Preview save must not share a stable file")
                if private and self.path.is_symlink():
                    # Best-effort fallback on hosts without O_NOFOLLOW.
                    raise ValueError("Preview save must not link to a stable file")
                # Read only as much as the core can hold, plus one byte to
                # detect oversized or partial saves before writing any SRAM.
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
                self._last_saved_file_signature = _save_file_signature(opened)
            else:
                self._last_saved_digest = None
                self._last_saved_file_signature = None

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
        if digest == self._last_saved_digest:
            try:
                # Unchanged SRAM does not prove unchanged STORAGE. In
                # addition to truncation, a cloud-sync replacement or edit
                # may retain precisely the same file size. Compare one
                # bounded descriptor-derived signature (not file contents)
                # to the last successful checkpoint/restore identity.
                if (self._last_saved_file_signature is not None
                        and self.path.is_file()
                        and _save_file_signature(self.path.stat())
                        == self._last_saved_file_signature):
                    return False
            except (OSError, ValueError, TypeError, AttributeError):
                # Missing/remounted ROM media or failed stat means unknown,
                # never a reason to claim that the native SRAM was saved.
                # The ordinary atomic fallback will handle a write fault.
                pass
        destination = self.path
        if (is_v32_preview() or is_v33_candidate()):
            # Re-validate the preview parent immediately before replacing
            # files. No preview SRAM may follow a redirected stable directory.
            _user_save_directory()
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
        try:
            # Capture the committed path identity after os.replace(). A
            # metadata probe failure cannot undo a successful atomic save;
            # the next unchanged checkpoint safely retries verification.
            self._last_saved_file_signature = _save_file_signature(
                destination.stat()
            )
        except (OSError, ValueError, TypeError, AttributeError):
            self._last_saved_file_signature = None
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
            # Windows can briefly deny a replace when another app instance,
            # filesystem scanner or antivirus holds the current destination.
            # Retry only the known native sharing/access-violation codes; a
            # read-only path or broken storage should still reach the normal
            # user-writable fallback rather than spin indefinitely.
            for attempt in range(4):
                try:
                    os.replace(temporary, destination)
                    break
                except PermissionError as exc:
                    code = getattr(exc, "winerror", None)
                    if (os.name != "nt" or code not in (5, 32, 33)
                            or attempt == 3):
                        raise
                    time.sleep(0.025 * (attempt + 1))
        finally:
            # A failed or interrupted save must leave the previous committed
            # .sav untouched. Never unlink another writer's temporary file.
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
