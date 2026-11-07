"""Run mGBA and Snes9x through the native Libretro API.

This module owns the emulator thread and Libretro lifecycle. Video conversion,
audio output, joypad state, core discovery, and SRAM persistence each live in
small modules with tests. No operating-system keyboard events are injected.

The public ``Emulator`` interface is kept compatible with the original app.
In particular, ``frame`` is protected by ``lock`` and ``armed`` only controls
camera input; manual controls operate independently.
"""

import ctypes as C
import os
from pathlib import Path
import sys
import threading
import time

from anything_plays.core_locator import find_core
from anything_plays.gamecube_software import (
    DolphinSoftwareOptions, find_dolphin_core,
    packaged_dolphin_system_directory,
)
from anything_plays.libretro_abi import (
    AUDIO, AUDIO_BATCH, AVInfo, CoreInfo, ENV, GameInfo, INPUT_POLL,
    INPUT_STATE, VIDEO,
)
from anything_plays.libretro_audio import AudioSink
from anything_plays.libretro_input import (
    BUTTONS, IDS, InputBuffer, TWO_PLAYER_SYSTEMS,
)
from anything_plays.libretro_save import SaveRAM, native_core_save_directory
from anything_plays.libretro_state import LibretroRecoveryState
from anything_plays.neopop_flash import check_cartridge_flash, InvalidNeoPopFlash
from anything_plays.n64_software import SoftwareN64Options, find_parallel_n64_core
from anything_plays.libretro_video import (
    SUPPORTED_FORMATS, SOFTWARE_RGBA8888, decode_frame,
)
from anything_plays.systems import SYSTEMS


# Legacy Libretro cores may request the complete ROM in one pointer-sized
# memory allocation. GameCube/other disc systems must use full-path loading,
# not silently copy entire disc images into the application's heap.
MAX_IN_MEMORY_ROM_BYTES = 256 * 1024 * 1024


class NativeCore:
    """Bind one dynamic library with explicit Libretro argument signatures."""

    def __init__(self, path):
        self.library = C.CDLL(str(path))
        self.set_environment = self._function("retro_set_environment", None, [ENV])
        self.set_video = self._function("retro_set_video_refresh", None, [VIDEO])
        self.set_audio = self._function("retro_set_audio_sample", None, [AUDIO])
        self.set_audio_batch = self._function(
            "retro_set_audio_sample_batch", None, [AUDIO_BATCH]
        )
        self.set_poll = self._function("retro_set_input_poll", None, [INPUT_POLL])
        self.set_state = self._function("retro_set_input_state", None, [INPUT_STATE])
        # The Libretro ABI allows the frontend to choose the device for each
        # port. Dolphin requires an explicit GameCube pad on port zero: merely
        # registering an input_state callback leaves its controller unset.
        self.set_controller_device = getattr(
            self.library, "retro_set_controller_port_device", None
        )
        if self.set_controller_device is not None:
            self.set_controller_device.argtypes = [C.c_uint, C.c_uint]
            self.set_controller_device.restype = None
        self.init = self._function("retro_init", None, [])
        self.deinit = self._function("retro_deinit", None, [])
        self.load = self._function("retro_load_game", C.c_bool, [C.POINTER(GameInfo)])
        self.unload = self._function("retro_unload_game", None, [])
        self.run = self._function("retro_run", None, [])
        self.system_info = self._function(
            "retro_get_system_info", None, [C.POINTER(CoreInfo)]
        )
        self.av_info = self._function(
            "retro_get_system_av_info", None, [C.POINTER(AVInfo)]
        )
        self.memory_data = self._function("retro_get_memory_data", C.c_void_p, [C.c_uint])
        self.memory_size = self._function("retro_get_memory_size", C.c_size_t, [C.c_uint])
        self.callbacks = []
        self.initialized = False
        self.loaded = False

    def _function(self, name, result, arguments):
        function = getattr(self.library, name)
        function.restype = result
        function.argtypes = arguments
        return function

    def configure(self, environment, video, audio, inputs):
        """Register and retain callbacks until the core has been deinitialized."""
        self.callbacks = [
            ENV(environment), VIDEO(video), AUDIO(audio.sample),
            AUDIO_BATCH(audio.batch), INPUT_POLL(lambda: None),
            INPUT_STATE(inputs.state),
        ]
        self.set_environment(self.callbacks[0])
        self.set_video(self.callbacks[1])
        self.set_audio(self.callbacks[2])
        self.set_audio_batch(self.callbacks[3])
        self.set_poll(self.callbacks[4])
        self.set_state(self.callbacks[5])

    def close(self):
        """Release game memory before core state, then drop callback references."""
        try:
            if self.loaded:
                self.unload()
        finally:
            try:
                if self.initialized:
                    self.deinit()
            finally:
                self.callbacks.clear()
                self.loaded = False
                self.initialized = False


class CoreSession:
    """Own everything that must live on the Libretro worker thread."""

    def __init__(self, emulator, system, rom, core_path):
        self.emulator = emulator
        self.system = system
        self.rom = Path(rom).resolve()
        self.core_path = core_path
        self.native = None
        self.audio = AudioSink()
        self.audio.set_volume(getattr(emulator, "volume", 0.35))
        # Dolphin SWGfx hands us the CPU-owned RGBA8 texture directly:
        # unlike standard Libretro XRGB8888, the byte order is R,G,B,A.
        # Other consoles retain Libretro's RGB1555 default.
        self.pixel_format = SOFTWARE_RGBA8888 if system == "gamecube" else 0
        self._software_options = (
            SoftwareN64Options() if system == "n64" else
            DolphinSoftwareOptions() if system == "gamecube" else None
        )
        self.save_ram = None
        self.recovery_state = None
        # The native cartridge .flash remains independent. A verified
        # checkpoint can recover if the native core fails to apply flash
        # on a later cold start. Native-flash-only labs disable this.
        self.enable_state_resume = True
        self._rom_buffers = []
        self._rom_path_bytes = os.fsencode(str(self.rom))
        self._system_dir_buffer = self._make_system_directory()
        # These native cores write their own save files, independently
        # of RETRO_MEMORY_SAVE_RAM. NGP/NGPC cartridge flash is persisted by
        # Beetle NeoPop at unload as <ROM-stem>.flash in GET_SAVE_DIRECTORY.
        # Every ROM needs a unique user-writable directory or two different
        # games with the same filename can silently overwrite progress.
        # Dolphin keeps its independent user save directory and Sys files.
        if system in ("gamecube", "ngp", "ngpc"):
            save_folder = native_core_save_directory(self.rom, system)
            save_folder.mkdir(parents=True, exist_ok=True)
        else:
            # Unused by generic SRAM-only cores. The native environment
            # callback continues to point their save request at system_dir.
            save_folder = Path.home() / ".config" / "anything-plays"
        self._save_dir_buffer = C.create_string_buffer(
            os.fsencode(str(save_folder))
        )

    def _make_system_directory(self):
        if self.system == "gamecube":
            # Abort before loading a core if the one-click installer omitted
            # Dolphin's mandatory game-compatibility system files.
            folder = packaged_dolphin_system_directory(self.core_path)
        elif sys.platform == "darwin":
            folder = Path.home() / "Library" / "Application Support" / "AnythingPlays"
        else:
            folder = Path.home() / ".config" / "anything-plays"
        folder.mkdir(parents=True, exist_ok=True)
        return C.create_string_buffer(os.fsencode(str(folder)))

    def environment(self, command, data):
        """Respond to the subset of environment requests our cores require."""
        if self._software_options is not None:
            response = self._software_options.environment(command, data)
            if response is not None:
                return response
        if command == 10 and data:  # RETRO_ENVIRONMENT_SET_PIXEL_FORMAT
            requested = C.cast(data, C.POINTER(C.c_int))[0]
            if requested not in SUPPORTED_FORMATS:
                return False
            # Dolphin's pinned Libretro core negotiates XRGB8888 at init,
            # but its software SWTexture video callback supplies raw RGBA8.
            # Keep the private decoder marker for that exact combination or
            # red and blue channels will be swapped on every rendered frame.
            if self.system == "gamecube" and requested == 1:
                self.pixel_format = SOFTWARE_RGBA8888
            else:
                self.pixel_format = requested
            return True
        if command in (9, 31) and data:  # GET_SYSTEM_DIRECTORY / GET_SAVE_DIRECTORY
            folder = (self._save_dir_buffer if self.system in
                      ("gamecube", "ngp", "ngpc") and command == 31
                      else self._system_dir_buffer)
            C.cast(data, C.POINTER(C.c_char_p))[0] = C.cast(
                folder, C.c_char_p
            )
            return True
        if command == 3 and data:  # GET_CAN_DUPE: repeat the previous frame.
            C.cast(data, C.POINTER(C.c_bool))[0] = True
            return True
        if command == 18:  # SET_SUPPORT_NO_GAME (no content-less mode used).
            return True
        return False

    def video(self, data, width, height, pitch):
        """Copy a core-owned video frame before the native callback returns."""
        try:
            frame = decode_frame(data, width, height, pitch, self.pixel_format)
        except (ValueError, OverflowError):
            return
        if frame is not None:
            with self.emulator.lock:
                self.emulator.frame = frame
                self.emulator.frame_serial += 1

    def _game_info(self, full_path):
        """Build one retro_game_info and retain its buffers for the core's life."""
        path_bytes = self._rom_path_bytes
        if full_path:
            return GameInfo(path_bytes, None, 0, None)
        size = self.rom.stat().st_size
        if size < 0 or size > MAX_IN_MEMORY_ROM_BYTES:
            raise ValueError(
                f"{self.rom.name} is too large for the core's in-memory ROM "
                f"interface ({size:,} bytes). Select a compatible game or "
                "a core that supports loading from a file path."
            )
        # A ROM on removable/network storage can grow after stat(). Never
        # call read_bytes() here: it can allocate unbounded memory before
        # a post-read size check has a chance to reject the file.
        with self.rom.open("rb") as stream:
            rom_bytes = stream.read(MAX_IN_MEMORY_ROM_BYTES + 1)
        if len(rom_bytes) > MAX_IN_MEMORY_ROM_BYTES:
            raise ValueError("ROM changed size while loading; refusing oversized buffer")
        buffer = C.create_string_buffer(rom_bytes)
        self._rom_buffers.append(buffer)
        return GameInfo(path_bytes, C.cast(buffer, C.c_void_p), len(rom_bytes), None)

    def _load_game(self):
        if not self.rom.is_file():
            raise FileNotFoundError(f"ROM not found: {self.rom}")
        if self.system in ("ngp", "ngpc"):
            # Upstream NeoPop's C flash loader trusts unbounded lengths and
            # block counts from the file. Reject corrupt saves before calling
            # retro_load_game(), preserving the original for manual recovery.
            try:
                check_cartridge_flash(
                    self.rom, os.fsdecode(self._save_dir_buffer.value)
                )
            except InvalidNeoPopFlash as exc:
                raise RuntimeError(
                    "Unsafe Neo Geo Pocket cartridge save. The original "
                    "file was preserved, not deleted. Move it out of the "
                    "game's save folder before starting without that save. "
                    + str(exc)
                ) from exc

        info = CoreInfo()
        self.native.system_info(C.byref(info))
        game = self._game_info(bool(info.need_fullpath))
        accepted = bool(self.native.load(C.byref(game)))

        if not accepted:
            library = (info.library_name or b"unknown").decode(errors="replace")
            raise RuntimeError(
                f"{SYSTEMS[self.system].title} core ({library}) rejected "
                f"{self.rom.name} (need_fullpath={bool(info.need_fullpath)}). "
                "Check the Terminal for details."
            )
        self.native.loaded = True
        if self.system in TWO_PLAYER_SYSTEMS:
            # Only configure controller ports *after* retro_load_game, when
            # Dolphin's serial interface and other core-specific input
            # devices are ready. Player 2 must be registered or the second
            # fish can produce callbacks that the game never sees.
            select_device = getattr(self.native, "set_controller_device", None)
            if select_device is None:
                if self.system == "gamecube":
                    raise RuntimeError(
                        "Dolphin Libretro core has no controller-port API"
                    )
            else:
                select_device(0, 1)
                select_device(1, 1)  # Player 2: RETRO_DEVICE_JOYPAD

    def persist_game_progress(self):
        """Persist battery SRAM AND safe NGP recovery without killing gameplay."""
        written = False
        if self.save_ram is not None:
            try:
                written = bool(self.save_ram.persist())
            except (OSError, ValueError, MemoryError) as exc:
                self.emulator.save_warning = (
                    "Battery save failed; game is still running: " + str(exc)[:140]
                )
        if self.recovery_state is not None:
            try:
                written = bool(self.recovery_state.persist()) or written
            except (OSError, ValueError, RuntimeError, MemoryError) as exc:
                self.emulator.save_warning = (
                    "Recovery save failed; game is still running: " + str(exc)[:140]
                )
        return written

    def run(self):
        if not self.core_path or not Path(self.core_path).is_file():
            raise RuntimeError(
                f"{SYSTEMS[self.system].title} bundled emulator core not found. "
                "Please reinstall Anything Plays."
            )
        self.emulator.inputs.system = self.system
        self.native = NativeCore(self.core_path)
        try:
            self.native.configure(
                self.environment, self.video, self.audio, self.emulator.inputs
            )
            self.native.init()
            self.native.initialized = True
            self._load_game()

            av = AVInfo()
            self.native.av_info(C.byref(av))
            frames_per_second = (
                av.timing.fps if 20 < av.timing.fps < 240 else 59.7275
            )
            # The same AudioSink handles every Libretro console (including
            # hardware-rendered GameCube), so the game-panel gain is live.
            self.emulator.audio_sink = self.audio
            self.audio.start(av.timing.sample_rate)
            self.emulator.audio_warning = getattr(self.audio, "output_error", None)
            self.save_ram = SaveRAM(
                self.rom, self.native.memory_data, self.native.memory_size
            )
            try:
                self.save_ram.restore()
            except (OSError, ValueError, MemoryError) as exc:
                # Continue gameplay even when an existing .sav is corrupt
                # or on disconnected storage. Warn instead of crashing.
                self.emulator.save_warning = (
                    "Could not restore saved game: " + str(exc)[:140]
                )
            if self.system in ("ngp", "ngpc") and self.enable_state_resume:
                # The core's own .flash read occurs inside _load_game.
                # An independent, correctly fingerprinted state is a
                # last-session recovery layer, not a replacement for flash.
                try:
                    self.recovery_state = LibretroRecoveryState(
                        self.rom, self.system, self.core_path, self.native)
                    if self.recovery_state.restore():
                        self.emulator.resume_info = (
                            "Restored the last verified Neo Geo Pocket session."
                        )
                except (OSError, ValueError, RuntimeError, MemoryError) as exc:
                    # Preserve a corrupt/incompatible checkpoint for manual
                    # recovery rather than deleting it or crashing gameplay.
                    self.recovery_state = None
                    self.emulator.save_warning = (
                        "Native resume unavailable; started game normally: "
                        + str(exc)[:140]
                    )
            self.emulator.running = True
            self.emulator.launching = False

            frame_number = 0
            next_frame = time.monotonic()
            while not self.emulator.stop_event.is_set():
                self.emulator.inputs.before_frame(self.emulator.armed)
                self.native.run()
                self.emulator.inputs.after_frame()
                frame_number += 1
                if frame_number % 300 == 0:
                    self.persist_game_progress()

                next_frame += 1 / frames_per_second
                remaining = next_frame - time.monotonic()
                if remaining > 0:
                    self.emulator.stop_event.wait(remaining)
                elif remaining < -0.25:
                    next_frame = time.monotonic()
            self.persist_game_progress()
        finally:
            if getattr(self.emulator, "audio_sink", None) is self.audio:
                self.emulator.audio_sink = None
            self.audio.close()
            if self.native is not None:
                self.native.close()


class Emulator:
    """Thread-safe facade used by the Tkinter application."""

    def __init__(self):
        self.inputs = InputBuffer()
        # Expose legacy attributes for compatibility with existing extensions.
        self.commands = self.inputs.commands
        self.manual_buttons = self.inputs.manual_buttons
        self.manual_lock = self.inputs.manual_lock
        self.stop_event = threading.Event()
        self.thread = None
        self.running = False
        self.launching = False
        self.last_error = None
        self.armed = False
        self.error = None
        self.save_warning = None
        self.audio_warning = None
        self.resume_info = None
        self.volume = 0.35
        self.audio_sink = None
        self.frame = None
        self.frame_serial = 0  # Monotonic per-session video revision for Tk.
        self.lock = threading.Lock()
        self.system = "gba"
        self.core_path = find_core(self.system)
        self.rom = None

    def find_system_core(self):
        """Look up the core for the console selected in the interface."""
        # The external RetroArch launcher may use Mupen64Plus-Next, but
        # the experimental in-panel software renderer requires ParaLLEl-N64.
        if self.system == "n64":
            return find_parallel_n64_core()
        if self.system == "gamecube":
            return find_dolphin_core()
        return find_core(self.system)

    def start(self, rom):
        """Stop the previous session before starting a fresh worker thread."""
        self.stop()
        if self.thread is not None and self.thread.is_alive():
            raise RuntimeError("The previous emulator is still shutting down")
        self.rom = str(rom)
        self.running = False
        self.launching = True
        self.last_error = None
        self.error = None
        self.save_warning = None
        self.audio_warning = None
        self.resume_info = None
        self.stop_event.clear()
        with self.lock:
            self.frame = None
            self.frame_serial += 1
        self.thread = threading.Thread(target=self._run, daemon=True, name="libretro")
        self.thread.start()

    def set_volume(self, level):
        """Adjust only this application's audio, including active games."""
        try:
            volume = float(level)
        except (TypeError, ValueError, OverflowError):
            volume = 0.35
        if not 0.0 <= volume <= 1.0:
            volume = max(0.0, min(1.0, volume)) if volume == volume else 0.35
        self.volume = volume
        sink = self.audio_sink
        if sink is not None:
            sink.set_volume(volume)

    def set_camera_buttons(self, player_one=(), player_two=()):
        """Publish one atomic camera snapshot, with independent P1/P2 holds."""
        if self.running and self.armed:
            self.inputs.set_camera_buttons(player_one, player_two)

    def press(self, button, frames=8, port=0):
        if self.running and self.armed and self.inputs.id_for(button) is not None:
            self.inputs.queue_press(button, frames, port=port)

    def set_manual(self, button, down):
        self.inputs.set_manual(button, down)

    def release_manual(self):
        self.inputs.release_manual()

    def disarm(self):
        self.armed = False
        # Stop must clear P1/P2 camera holds and queued pulses immediately,
        # even if the native core is currently blocked in retro_run().
        self.inputs.disarm()

    def stop(self):
        """Request worker shutdown, keeping it tracked if it does not exit."""
        self.release_manual()
        self.disarm()
        self.stop_event.set()
        worker = self.thread
        if worker is not None and worker.is_alive():
            worker.join(timeout=4)
        if worker is None or not worker.is_alive():
            self.thread = None
            self.running = False
            self.launching = False
            self.inputs.disarm()

    def _run(self):
        try:
            if self.system == "gamecube":
                # Lazy import avoids a CoreSession -> GameCube circular import.
                # Offscreen accelerated rendering, not Dolphin's slow/crashing
                # CPU-only software renderer, owns game frames.
                from anything_plays.gamecube_gpu import GameCubeHardwareSession
                GameCubeHardwareSession(self, self.rom, self.core_path).run()
            else:
                CoreSession(self, self.system, self.rom, self.core_path).run()
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.error = self.last_error
        finally:
            # All session paths, including errors BEFORE running=True,
            # must allow a new ROM attempt without restarting Anything Plays.
            self.launching = False
            self.armed = False
            self.running = False
            self.inputs.disarm()
            self.inputs.release_manual()
            # Do not race Tk's UI thread by clearing the video frame here.
