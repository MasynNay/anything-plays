"""Check real mGBA Libretro extension support without distributing game ROMs.

Run explicitly with AP_TEST_NATIVE_CORE=1 after downloading an mGBA core.
Ordinary unit tests skip this external-binary check.
"""

import ctypes as C
import os
from pathlib import Path
import tempfile
import time
import unittest

from anything_plays.core_locator import find_core
from anything_plays.gba_emulator import Emulator
from anything_plays.libretro_abi import CoreInfo


def _make_test_rom(system, with_battery=False):
    """Create a tiny homebrew GB cartridge that executes an idle loop."""
    payload = bytearray(32768)
    # NOP; JP $0150 at cartridge entry, then JR -2 forever.
    payload[0x100:0x104] = b"\x00\xc3\x50\x01"
    # Minimum GB identification signature required by mGBA.
    payload[0x104:0x108] = bytes((0xCE, 0xED, 0x66, 0x66))
    payload[0x134:0x141] = b"ANYTHINGPLAYS"
    payload[0x143] = 0x80 if system == "gbc" else 0x00
    payload[0x147] = 0x03 if with_battery else 0x00  # MBC1+RAM+BATTERY or ROM-only
    payload[0x148] = 0x00  # 32 KiB ROM
    payload[0x149] = 0x02 if with_battery else 0x00  # 8 KiB RAM
    checksum = 0
    for address in range(0x134, 0x14D):
        checksum = (checksum - payload[address] - 1) & 0xFF
    payload[0x14D] = checksum
    payload[0x150:0x152] = b"\x18\xfe"
    return bytes(payload)


@unittest.skipUnless(os.environ.get("AP_TEST_NATIVE_CORE") == "1",
                     "Requires a separately downloaded Libretro mGBA core")
class RealMGBASupport(unittest.TestCase):
    def test_game_boy_color_and_advance_extensions(self):
        paths = {name: find_core(name) for name in ("gb", "gbc", "gba")}
        self.assertTrue(all(paths.values()), "mGBA binary not found")
        self.assertEqual(len(set(paths.values())), 1,
                         "GB, GBC and GBA should use the same mGBA binary")
        path = Path(paths["gba"])
        self.assertIn("mgba", path.name.lower())

        library = C.CDLL(str(path))
        describe = library.retro_get_system_info
        describe.argtypes = [C.POINTER(CoreInfo)]
        describe.restype = None
        info = CoreInfo()
        describe(C.byref(info))
        reported = (info.valid_extensions or b"").decode("utf-8", "replace")
        extensions = {ext.strip(". ").lower() for ext in reported.replace(";", "|").split("|")}
        self.assertTrue({"gb", "gbc", "gba"} <= extensions,
                        f"mGBA core did not advertise GB/GBC/GBA: {reported}")


    def test_game_boy_and_color_render_with_minimal_homebrew_rom(self):
        """Exercise core load and live video without including copyrighted ROMs."""
        with tempfile.TemporaryDirectory(prefix="anything-plays-mgba-") as directory:
            for system in ("gb", "gbc"):
                with self.subTest(system=system):
                    rom = Path(directory) / f"minimal.{system}"
                    rom.write_bytes(_make_test_rom(system))

                    emulator = Emulator()
                    emulator.system = system
                    emulator.core_path = find_core(system)
                    emulator.start(rom)
                    frame = None
                    try:
                        deadline = time.monotonic() + 5.0
                        while time.monotonic() < deadline:
                            if emulator.error:
                                self.fail(emulator.error)
                            with emulator.lock:
                                frame = emulator.frame
                            if emulator.running and frame is not None:
                                break
                            time.sleep(0.05)
                        self.assertTrue(emulator.running, emulator.error)
                        self.assertIsNotNone(frame, "No video frame received")
                        self.assertEqual(frame.shape[-1], 3)
                    finally:
                        emulator.stop()
                    self.assertIsNone(emulator.error)


    def test_existing_mbc1_battery_save_round_trips(self):
        """Restore and persist a prior raw GB/GBC .sav using real mGBA SRAM."""
        import threading

        from anything_plays.gba_emulator import CoreSession

        with tempfile.TemporaryDirectory(prefix="anything-plays-save-") as directory:
            for system in ("gb", "gbc"):
                with self.subTest(system=system):
                    rom = Path(directory) / f"saved.{system}"
                    rom.write_bytes(_make_test_rom(system, with_battery=True))
                    save_file = rom.with_suffix(".sav")
                    original = bytes(range(256)) * 32  # 8 KiB legacy raw save.
                    changed = b"\xa5" * len(original)
                    save_file.write_bytes(original)

                    emulator = Emulator()
                    emulator.system = system
                    emulator.core_path = find_core(system)
                    session = CoreSession(emulator, system, rom, emulator.core_path)
                    errors = []

                    def run_core():
                        try:
                            session.run()
                        except Exception as exc:
                            errors.append(exc)

                    worker = threading.Thread(target=run_core, daemon=True)
                    worker.start()
                    try:
                        deadline = time.monotonic() + 5.0
                        while (not emulator.running and not errors
                               and time.monotonic() < deadline):
                            time.sleep(0.05)
                        if errors:
                            self.fail(f"Core startup failed: {errors[0]}")
                        self.assertTrue(emulator.running, "Native core did not start")
                        self.assertIsNotNone(session.save_ram)
                        pointer, size = session.save_ram._memory()
                        self.assertTrue(pointer)
                        self.assertEqual(size, len(original))
                        self.assertEqual(C.string_at(pointer, size), original)
                        C.memmove(pointer, changed, size)
                    finally:
                        emulator.stop_event.set()
                        worker.join(timeout=5.0)

                    self.assertFalse(worker.is_alive(), "Native core failed to exit")
                    self.assertFalse(errors, f"Core failed: {errors}")
                    self.assertEqual(save_file.read_bytes(), changed)


if __name__ == "__main__":
    unittest.main()
