"""Real packaged 3.2 SaveRAM restore/write/cold-restore QA.

Opt-in exclusively from the stable-identity frozen GUI, using a synthetic
cartridge under the disposable runner's HOME. No emulator, ROM execution,
camera, controller or physical input is activated. No retail saves tested.
"""
from __future__ import annotations

import ctypes as C
from pathlib import Path
import sys

from anything_plays.build_identity import current_identity
from anything_plays.libretro_save import SaveRAM
from anything_plays.v32_sram_fixture import (
    ROM_FOLDER, ROM_NAME, ROM_CANARY, OLD_SRAM, NEW_SRAM,
)


def _fixture(path, contents):
    if (not path.is_file() or path.is_symlink()
            or path.stat().st_nlink != 1
            or path.stat().st_size != len(contents)
            or path.read_bytes() != contents):
        raise RuntimeError("Synthetic 3.1.1 ROM/SRAM fixture unavailable or redirected")


def exercise_installed_stable_sram(app):
    """Verify real v3.2 Libretro SRAM load, atomic save and cold re-load."""
    identity = current_identity()
    if (not getattr(sys, "frozen", False)
            or identity.get("channel") != "v32_stable_candidate"
            or identity.get("settings_namespace") != "anything-plays-31"
            or identity.get("public_release_approved") is not False):
        raise RuntimeError("SRAM migration QA requires a frozen private stable upgrade")
    if (app.armed or app.cap is not None
            or app._gamepad.api is not None
            or getattr(app, "current_rom", None) is not None):
        raise RuntimeError("SRAM diagnostic may not run while devices or a game are active")
    home = Path.home()
    folder = home / ROM_FOLDER
    if not folder.is_dir() or folder.is_symlink():
        raise RuntimeError("Synthetic ROM folder missing or linked")
    rom = folder / ROM_NAME
    old_save = rom.with_suffix(".sav")
    _fixture(rom, ROM_CANARY)
    _fixture(old_save, OLD_SRAM)

    previous = C.create_string_buffer(len(OLD_SRAM))
    old_instance = SaveRAM(
        rom, lambda memory_type: C.addressof(previous) if memory_type == 0 else 0,
        lambda memory_type: len(OLD_SRAM) if memory_type == 0 else 0,
    )
    if old_instance.path != old_save:
        raise RuntimeError("3.2 stable build redirected legacy SRAM into preview storage")
    old_instance.restore()
    if previous.raw != OLD_SRAM:
        raise RuntimeError("3.2 could not restore old 3.1.1 cartridge-backed SRAM")
    # Use exactly the same atomic SaveRAM persistence used in normal game
    # shutdown. A stable save may change after running a new release.
    previous.raw = NEW_SRAM
    if old_instance.persist() is not True:
        raise RuntimeError("3.2 failed to atomically persist changed legacy SRAM")
    if old_instance.persist() is not False:
        raise RuntimeError("Unchanged SRAM was needlessly rewritten")
    _fixture(old_save, NEW_SRAM)

    reloaded = C.create_string_buffer(len(NEW_SRAM))
    fresh_instance = SaveRAM(
        rom, lambda memory_type: C.addressof(reloaded) if memory_type == 0 else 0,
        lambda memory_type: len(NEW_SRAM) if memory_type == 0 else 0,
    )
    fresh_instance.restore()
    if (fresh_instance.path != old_save or reloaded.raw != NEW_SRAM
            or fresh_instance.persist() is not False):
        raise RuntimeError("Cold 3.2 SRAM restore did not retain the new saved data")
    _fixture(rom, ROM_CANARY)
    if (app.armed or app.cap is not None
            or app._gamepad.api is not None
            or getattr(app, "current_rom", None) is not None):
        raise RuntimeError("SRAM diagnostic unexpectedly started gameplay or devices")
    return True
