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
from anything_plays.libretro_abi import (
    AUDIO, AUDIO_BATCH, AVInfo, CoreInfo, ENV, GameInfo, INPUT_POLL,
    INPUT_STATE, VIDEO,
)
from anything_plays.libretro_audio import AudioSink
from anything_plays.libretro_input import BUTTONS, IDS, InputBuffer
from anything_plays.libretro_save import SaveRAM
from anything_plays.n64_software import SoftwareN64Options
from anything_plays.libretro_video import SUPPORTED_FORMATS, decode_frame
from anything_plays.systems import SYSTEMS


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
        self.pixel_format = 0  # Libretro defaults to RGB1555.
        self._software_options = SoftwareN64Options() if system == "n64" else None
        self.save_ram = None
        self._rom_buffers = []
        self._rom_path_bytes = os.fsencode(str(self.rom))
        self._system_dir_buffer = self._make_system_directory()

    @staticmethod
    def _make_system_directory():
        if sys.platform == "darwin":
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
            self.pixel_format = requested
            return True
        if command in (9, 31) and data:  # GET_SYSTEM_DIRECTORY / GET_SAVE_DIRECTORY
            C.cast(data, C.POINTER(C.c_char_p))[0] = C.cast(
                self._system_dir_buffer, C.c_char_p
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

    def _game_info(self, full_path):
        """Build one retro_game_info and retain its buffers for the core's life."""
        path_bytes = self._rom_path_bytes
        if full_path:
            return GameInfo(path_bytes, None, 0, None)
        rom_bytes = self.rom.read_bytes()
        buffer = C.create_string_buffer(rom_bytes)
        self._rom_buffers.append(buffer)
        return GameInfo(path_bytes, C.cast(buffer, C.c_void_p), len(rom_bytes), None)

    def _load_game(self):
        if not self.rom.is_file():
            raise FileNotFoundError(f"ROM not found: {self.rom}")

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
            self.audio.start(av.timing.sample_rate)
            self.save_ram = SaveRAM(
                self.rom, self.native.memory_data, self.native.memory_size
            )
            self.save_ram.restore()
            self.emulator.running = True

            frame_number = 0
            next_frame = time.monotonic()
            while not self.emulator.stop_event.is_set():
                self.emulator.inputs.before_frame(self.emulator.armed)
                self.native.run()
                self.emulator.inputs.after_frame()
                frame_number += 1
                if frame_number % 300 == 0:
                    self.save_ram.persist()

                next_frame += 1 / frames_per_second
                remaining = next_frame - time.monotonic()
                if remaining > 0:
                    self.emulator.stop_event.wait(remaining)
                elif remaining < -0.25:
                    next_frame = time.monotonic()
            self.save_ram.persist()
        finally:
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
        self.armed = False
        self.error = None
        self.frame = None
        self.lock = threading.Lock()
        self.system = "gba"
        self.core_path = find_core(self.system)
        self.rom = None

    def find_system_core(self):
        """Look up the core for the console selected in the interface."""
        return find_core(self.system)

    def start(self, rom):
        """Stop the previous session before starting a fresh worker thread."""
        self.stop()
        if self.thread is not None and self.thread.is_alive():
            raise RuntimeError("The previous emulator is still shutting down")
        self.rom = str(rom)
        self.error = None
        self.stop_event.clear()
        with self.lock:
            self.frame = None
        self.thread = threading.Thread(target=self._run, daemon=True, name="libretro")
        self.thread.start()

    def press(self, button, frames=8):
        if self.running and self.armed and self.inputs.id_for(button) is not None:
            self.inputs.queue_press(button, frames)

    def set_manual(self, button, down):
        self.inputs.set_manual(button, down)

    def release_manual(self):
        self.inputs.release_manual()

    def disarm(self):
        self.armed = False
        # Commands are drained in the worker on the next frame. Avoid mutating
        # its held-button dictionary concurrently with native callbacks.

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
            self.inputs.disarm()

    def _run(self):
        try:
            CoreSession(self, self.system, self.rom, self.core_path).run()
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
        finally:
            self.armed = False
            self.running = False
            self.inputs.release_manual()
            # Do not race Tk's UI thread by clearing the video frame here.
