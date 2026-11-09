"""macOS N64 process isolation: each ROM gets a NEW native core process.

ParaLLEl-N64 survives one game on macOS but its native globals do not
reinitialize for a second game in the same app process. Direct dlclose crashes
inside dyld on both Intel and Apple Silicon. This bridge preserves the exact
Tk Emulator façade, local P1/P2 and camera input, live audio and cartridge
saves, but runs N64's Libretro module in a fresh spawned process per ROM.

No external emulator or user download. The child uses the already bundled
core and owns its audio device; only bounded frames, current control states
and status are shared. Crash/timeout cannot segfault the Tk parent.
"""
from __future__ import annotations

import multiprocessing as mp
from pathlib import Path
import time
import traceback

import numpy as np

from anything_plays.libretro_video import decode_frame

MAX_VIDEO_WIDTH = 1024
MAX_VIDEO_HEIGHT = 1024
MAX_VIDEO_BYTES = MAX_VIDEO_WIDTH * MAX_VIDEO_HEIGHT * 3
PORT_STRIDE = 20  # 16 RetroPad digital IDs + 4 analog X/Y axes
INPUT_COUNT = PORT_STRIDE * 2
N64_CAPTURE_INTERVAL = 1 / 30.0


class SharedN64Inputs:
    """Libretro callback in child reads the parent's current controls."""

    def __init__(self, values, system="n64"):
        self.values = values
        self.system = system

    def state(self, port, device, index, button):
        if port not in (0, 1):
            return 0
        if device == 1 and 0 <= button < 16:
            offset = button
        elif device == 5 and index in (0, 1) and button in (0, 1):
            offset = 16 + 2 * index + button
        else:
            return 0
        return self.values[port * PORT_STRIDE + offset]

    def before_frame(self, armed):
        return None  # Parent snapshots controls at 60 Hz.

    def after_frame(self):
        return None


class ChildEmulator:
    """Minimal CoreSession interface, entirely inside the game subprocess."""

    def __init__(self, control, stopped, state, gain, system="n64"):
        self.inputs = SharedN64Inputs(control, system)
        self.stop_event = stopped
        self._state = state
        self._gain = gain
        self.armed = True
        self.isolated_process = True
        self.audio_sink = None
        self.audio_warning = None
        self.save_warning = None
        self.resume_info = None
        self.launching = True

    @property
    def running(self):
        return self._state.value == 1

    @running.setter
    def running(self, yes):
        if yes:
            self._state.value = 1

    @property
    def volume(self):
        return self._gain.value


def _child_main(rom, core, control, stopped, state, gain,
                pixels, width, height, serial, guard, error_pipe, system="n64"):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from anything_plays.gba_emulator import CoreSession

    emulator = ChildEmulator(control, stopped, state, gain, system)
    try:
        session = CoreSession(emulator, system, rom, core)
        # The N64 child is a one-game OS process; CoreSession MUST NOT
        # call dlclose on macOS. Exiting this subprocess discards all
        # native global state without running dyld unload destructors.
        def share_video(data, w, h, pitch):
            frame = decode_frame(data, w, h, pitch, session.pixel_format)
            if frame is None:
                return
            if (frame.ndim != 3 or frame.shape[2] != 3
                    or frame.shape[0] > MAX_VIDEO_HEIGHT
                    or frame.shape[1] > MAX_VIDEO_WIDTH):
                return
            packed = np.ascontiguousarray(frame)
            blob = packed.tobytes()
            if len(blob) > MAX_VIDEO_BYTES:
                return
            with guard:
                np.frombuffer(pixels, dtype=np.uint8, count=len(blob))[:] = (
                    np.frombuffer(blob, dtype=np.uint8)
                )
                width.value = packed.shape[1]
                height.value = packed.shape[0]
                serial.value += 1
            session.audio.set_volume(gain.value)
        session.video = share_video
        session.run()
        if emulator.save_warning:
            error_pipe.send(("save-warning", emulator.save_warning))
        if emulator.audio_warning:
            error_pipe.send(("audio-warning", emulator.audio_warning))
    except BaseException as exc:
        state.value = 3
        try:
            error_pipe.send((
                "error", f"{type(exc).__name__}: {exc}\n"
                + traceback.format_exc(limit=8)
            ))
        except (BrokenPipeError, OSError):
            pass
    finally:
        if state.value != 3:
            state.value = 2
        error_pipe.close()


def _publish_controls(buffer, shared):
    """Run camera/manual pulses on parent; send stable N64 Libretro values."""
    buffer.before_frame(True)
    for port in (0, 1):
        offset = port * PORT_STRIDE
        for key in range(16):
            shared[offset + key] = buffer.state(port, 1, 0, key)
        for axis in (0, 1):
            for direction in (0, 1):
                shared[offset + 16 + axis * 2 + direction] = (
                    buffer.state(port, 5, axis, direction)
                )
    buffer.after_frame()


class MacN64ProcessSession:
    """Run one N64 game in a disposable process, keeping app UI responsive."""

    def __init__(self, emulator, rom, core_path):
        self.emulator = emulator
        self.system = "n64"
        self.rom = str(Path(rom).resolve())
        self.core = str(Path(core_path).resolve())

    def run(self):
        ctx = mp.get_context("spawn")  # NEVER fork a live macOS Tk app.
        control = ctx.RawArray("i", INPUT_COUNT)
        pixels = ctx.RawArray("B", MAX_VIDEO_BYTES)
        width = ctx.Value("i", 0)
        height = ctx.Value("i", 0)
        serial = ctx.Value("i", 0)
        state = ctx.Value("i", 0)
        gain = ctx.Value("d", float(self.emulator.volume))
        guard = ctx.Lock()
        stopped = ctx.Event()
        parent, child = ctx.Pipe(duplex=False)
        process = ctx.Process(
            target=_child_main,
            args=(self.rom, self.core, control, stopped, state, gain,
                  pixels, width, height, serial, guard, child, self.system),
            name=f"AnythingPlays-{self.system}-isolated",
            daemon=True,
        )
        # The shared memory is bounded and is never exposed to the Tk thread.
        last_frame = -1
        last_capture = 0.0
        last_message = None
        started = False
        spawned = False
        try:
            self.emulator.inputs.system = self.system
            process.start()
            spawned = True
            child.close()
            while not self.emulator.stop_event.is_set():
                if state.value == 1:
                    started = True
                    self.emulator.running = True
                    self.emulator.launching = False
                if parent.poll():
                    try:
                        kind, message = parent.recv()
                    except EOFError:
                        kind, message = "error", "isolated worker closed its status channel"
                    if kind == "error":
                        last_message = message.splitlines()[0]
                    elif kind == "save-warning":
                        self.emulator.save_warning = message
                    elif kind == "audio-warning":
                        self.emulator.audio_warning = message
                if not process.is_alive():
                    break
                gain.value = float(self.emulator.volume)
                self.emulator.inputs.before_frame(self.emulator.armed)
                # All writes originate in this one owning parent thread.
                for port in (0, 1):
                    offset = port * PORT_STRIDE
                    for key in range(16):
                        control[offset + key] = self.emulator.inputs.state(
                            port, 1, 0, key
                        )
                    for axis in (0, 1):
                        for direction in (0, 1):
                            control[offset + 16 + axis * 2 + direction] = (
                                self.emulator.inputs.state(
                                    port, 5, axis, direction
                                )
                            )
                self.emulator.inputs.after_frame()
                now = time.monotonic()
                if (now - last_capture >= N64_CAPTURE_INTERVAL
                        and serial.value != last_frame):
                    with guard:
                        w, h = width.value, height.value
                        n = w * h * 3
                        if 0 < w <= MAX_VIDEO_WIDTH and 0 < h <= MAX_VIDEO_HEIGHT:
                            image = np.frombuffer(
                                pixels, dtype=np.uint8, count=n
                            ).copy().reshape((h, w, 3))
                            last_frame = serial.value
                        else:
                            image = None
                    if image is not None:
                        with self.emulator.lock:
                            self.emulator.frame = image
                            self.emulator.frame_serial += 1
                    last_capture = now
                self.emulator.stop_event.wait(1 / 60.0)
            if not self.emulator.stop_event.is_set():
                if not started:
                    raise RuntimeError(
                        f"{self.system} subprocess ended before gameplay began: "
                        + (last_message or f"exit code {process.exitcode}")
                    )
                if process.exitcode not in (0, None) or state.value == 3:
                    raise RuntimeError(
                        f"{self.system} subprocess stopped unexpectedly: "
                        + (last_message or f"exit code {process.exitcode}")
                    )
        finally:
            stopped.set()
            if spawned:
                process.join(timeout=5)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=3)
                    if process.is_alive():
                        process.kill()
                        process.join(timeout=2)
            parent.close()
            try:
                child.close()
            except OSError:
                pass
            self.emulator.inputs.disarm()
            self.emulator.running = False
            self.emulator.launching = False


class ExperimentalSoftwareCoreProcessSession(MacN64ProcessSession):
    """Opt-in research bridge for 2D Libretro cores, never a default app runtime.

    Uses the existing bounded shared-memory frame/input transport, core-owned
    audio and save lifecycle. Each game starts a fresh child process; no ROMs,
    audio, screenshots or personal data are uploaded. Does NOT support the
    Dolphin hardware-framebuffer path or replace its native integration.
    Process separation does NOT determine redistribution license compliance.
    """

    def __init__(self, emulator, system, rom, core_path):
        from anything_plays.systems import SYSTEMS

        if (system not in SYSTEMS or system in ("n64", "gamecube")
                or SYSTEMS[system].backend != "libretro"):
            raise ValueError("Experimental process bridge supports only 2D Libretro profiles")
        super().__init__(emulator, rom, core_path)
        self.system = system
