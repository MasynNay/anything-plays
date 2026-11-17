"""Embedded hardware-rendered GameCube session for Anything Plays.

No Dolphin UI, RetroArch binary, external emulator installation or second
game window is used. We own the OpenGL context, pass the FBO to Dolphin
Libretro and copy rendered frames to the existing Tk game canvas. The
base CoreSession handles *real PortAudio output*, keyboard/camera input and
save persistence.

Linux uses the proven EGL host; Windows and macOS use independently
auditable, hidden WGL/CGL contexts. The experimental interpreter/CPU
renderer must never be silently substituted for a missing GPU host.

This backend is not proof of 3D game compatibility; native GameCube playback
is still quarantined from stable 3.0 releases until cross-platform testing.
"""
from __future__ import annotations

import sys
import platform
import time
import math
import ctypes as C
from anything_plays.gba_emulator import CoreSession
from anything_plays.libretro_gpu_portable import choose_gamecube_gpu_host
from anything_plays.gamecube_preview import (
    should_capture, preview_fps, DEFAULT_PREVIEW_MODE, PreviewCadenceTracker,
    ReadbackTimingHistogram,
)
from anything_plays.gamecube_native_timing import GameCubeNativeTiming
from anything_plays.libretro_video import RETRO_HW_FRAME_BUFFER_VALID


MAX_GPU_NEGOTIATION_RECORDS = 16


class GameCubeHardwareSession(CoreSession):
    """Connect Libretro Dolphin to the same framebuffer the GUI displays."""

    @staticmethod
    def _optional_clock(clock):
        """Never let a failed diagnostic timer unwind a ctypes callback.

        A nonfinite or non-monotonic clock is *not* a frame timestamp.
        A missing readback duration is simply omitted from aggregate
        timing; the real native frame and audio work still proceed.
        """
        try:
            value = clock()
            if (type(value) in (int, float) and math.isfinite(value)
                    and value >= 0):
                return value
        except Exception:
            pass
        return None

    def __init__(self, emulator, rom, core_path, *, host_factory=None):
        super().__init__(emulator, "gamecube", rom, core_path)
        # libretro's CPU identifiers are architecture-specific: 1=JIT64,
        # 4=JITARM64, 5=cached interpreter. An x86 JIT selection on
        # Apple Silicon prevents BootManager::BootCore from starting.
        architecture = platform.machine().lower()
        jit_mode = b"4" if architecture in ("arm64", "aarch64") else b"1"
        self._software_options.values.update({
            b"dolphin_renderer": b"Hardware",
            # The patched software renderer requires an interpreter fallback,
            # but unmodified upstream hardware Libretro has proven JIT input
            # and GPU output in a native sandbox. Never silently inherit the
            # software mode's conservative setting.
            b"dolphin_cpu_core": jit_mode,
            b"dolphin_skip_dupe_frames": b"disabled",
        })
        self._host_factory = host_factory or choose_gamecube_gpu_host()
        self.host = None
        self.hardware_frames = 0
        # Per-frame GL readback is synchronous; keep bounded counters so
        # slow Intel CGL sessions can be diagnosed without assuming the CPU
        # emulator, GPU context, or canvas is at fault.
        self.gpu_readback_seconds = 0.0
        self.gpu_readback_max_seconds = 0.0
        self.gpu_readback_calls = 0
        self.gpu_readback_timing_samples = 0
        self._readback_histogram = ReadbackTimingHistogram()
        self.preview_clock_failures = 0
        self.native_run_timing = GameCubeNativeTiming()
        self.preview_readback_skips = 0
        self._last_preview_capture = None
        self._last_preview_publication = None
        self._last_preview_readback_duration = 0.0
        self._preview_cadence = PreviewCadenceTracker()
        self.raw_video_callbacks = 0
        self.null_video_callbacks = 0
        self.opengl_error = None
        self.hardware_requests = []
        self.hardware_negotiations_total = 0

    def environment(self, command, data):
        if command == 14:  # RETRO_ENVIRONMENT_SET_HW_RENDER
            from anything_plays.libretro_gpu_egl import HardwareRenderCallback
            request = None
            if data:
                callback = C.cast(data, C.POINTER(HardwareRenderCallback)).contents
                request = {
                    "type": int(callback.context_type),
                    "version": [int(callback.version_major), int(callback.version_minor)],
                    "granted": False,
                }
                # A faulty core may request the hardware context repeatedly.
                # Keep only the most recent few scalar records, not an
                # unbounded list of native handshake events.
                self.hardware_negotiations_total += 1
                if len(self.hardware_requests) == MAX_GPU_NEGOTIATION_RECORDS:
                    del self.hardware_requests[0]
                self.hardware_requests.append(request)
            accepted = bool(
                self.host is not None and self.host.accept_core_render(data)
            )
            if request is not None:
                request["granted"] = accepted
                # The first few requests are useful in crash logs (not
                # device identifiers). Never emit unbounded repeated lines
                # from a looping native callback over a long session.
                if self.hardware_negotiations_total <= MAX_GPU_NEGOTIATION_RECORDS:
                    try:
                        print("GAMECUBE-GPU-NEGOTIATION:", request, flush=True)
                    except Exception:
                        # A closed/broken stdout pipe is not a failed
                        # OpenGL context. Never unwind optional logging
                        # through a native Libretro ctypes callback.
                        pass
            return accepted
        if command == 0x10000 | 44:  # HW shared context (Dolphin fork)
            return True
        return super().environment(command, data)

    def _load_game(self):
        super()._load_game()
        if not self.host or not self.host.core_reset:
            raise RuntimeError(
                "Dolphin did not register a supported accelerated render context"
            )
        self.host.reset_core()

    def video(self, data, width, height, pitch):
        self.raw_video_callbacks += 1
        if not data:
            self.null_video_callbacks += 1
            return
        # After a hardware error Dolphin may briefly emit *software* video
        # callbacks too. Never publish ANY frame after graphics failure or
        # while a native Stop request is in progress.
        if (self.opengl_error is not None or
                self.emulator.stop_event.is_set()):
            return
        if data == RETRO_HW_FRAME_BUFFER_VALID:
            # glReadPixels blocks on GPU/CPU synchronization. Copy only as
            # fast as the selected preview rate, but NEVER skip retro_run()
            # frames, audio, controller updates, or internal Dolphin work.
            now = self._optional_clock(time.monotonic)
            mode = getattr(
                self.emulator, "gamecube_preview_mode", DEFAULT_PREVIEW_MODE
            )
            tracker = getattr(self, "_preview_cadence", None)
            if tracker is not None:
                # Show the requested new preview cap immediately, even when
                # throttling skips the first callback after a mode change.
                tracker.reset_for(mode)
            if now is None:
                # Invalid timing is neither a deliberately skipped GL
                # readback nor a native emulation frame failure.
                self.preview_clock_failures = (
                    getattr(self, "preview_clock_failures", 0) + 1
                )
                return
            # Keep normal fast GPU copies on the target start-to-start
            # cadence. Only an *over-budget* previous readback adds a short
            # recovery interval from completion; otherwise even a healthy
            # 60 FPS / 4ms GPU would be needlessly reduced to ~30 FPS.
            interval = 1.0 / preview_fps(mode) - 0.001
            previous_slow = (
                getattr(self, "_last_preview_readback_duration", 0.0)
                >= interval
            )
            previous_publication = getattr(
                self, "_last_preview_publication", None
            )
            if (not should_capture(self._last_preview_capture, now, mode)
                    or (previous_slow and not should_capture(
                        previous_publication, now, mode
                    ))):
                self.preview_readback_skips += 1
                return
            begun = self._optional_clock(time.perf_counter)
            try:
                rgb = self.host.read_frame(width, height)
                shape = getattr(rgb, "shape", ())
                # A torn GL context can return an empty or malformed buffer
                # without raising. Never publish it to Tk/OBS as a fresh
                # game image or count it as a valid hardware frame.
                if (len(shape) != 3 or shape[0] != height
                        or shape[1] != width or shape[2] != 3 or
                        str(getattr(rgb, "dtype", "")) != "uint8"):
                    # Shape and channel type alone are insufficient: an
                    # interrupted/resized GL readback can return an RGB8
                    # frame for a PREVIOUS viewport. Never publish those
                    # stale or mismatched pixels as the active native game.
                    # The first-party GL host returns exactly (height,
                    # width, 3) on a successful bounded readback.
                    raise ValueError("GPU readback returned invalid RGB pixels")
            except Exception as exc:
                # Driver/GL wrappers can raise additional exception classes
                # (including unexpected extension-defined ones). Let none
                # unwind through Dolphin's ctypes video callback. Stop this
                # broken host and preserve only a fixed, safe error category;
                # native driver paths, device IDs and custom exception class
                # names must never enter the GUI diagnostic report.
                kind = type(exc).__name__
                if kind not in (
                    "RuntimeError", "ValueError", "OSError", "TypeError",
                    "OverflowError", "MemoryError", "AttributeError",
                    "IndexError", "KeyError", "AssertionError",
                ):
                    kind = "UnexpectedError"
                self.opengl_error = f"GPU readback failed ({kind})"
                self.emulator.stop_event.set()
                return
            finished = self._optional_clock(time.perf_counter)
            # A host sleep/resume in glReadPixels (or a discontinuous
            # diagnostic timer) must not report hours of active GPU cost.
            # Preserve the actual captured pixels independently of timing.
            valid_readback_timing = (
                begun is not None and finished is not None
                and finished >= begun and finished - begun <= 3600.0
            )
            if valid_readback_timing:
                duration = finished - begun
                self.gpu_readback_seconds += duration
                self.gpu_readback_max_seconds = max(
                    self.gpu_readback_max_seconds, duration
                )
                self.gpu_readback_timing_samples = (
                    getattr(self, "gpu_readback_timing_samples", 0) + 1
                )
                hist = getattr(self, "_readback_histogram", None)
                if hist is not None:
                    hist.record(duration)
            else:
                self.preview_clock_failures = (
                    getattr(self, "preview_clock_failures", 0) + 1
                )
            self.gpu_readback_calls += 1
            with self.emulator.lock:
                # A Stop can arrive while glReadPixels is blocking. Never
                # let that late result repaint a stopped/failed session even
                # though the pre-read callback guard saw an active game.
                if self.emulator.stop_event.is_set() or self.opengl_error is not None:
                    return
                self.emulator.frame = rgb
                self.emulator.frame_serial += 1
            self.hardware_frames += 1
            # Normal preview cadence stays anchored to the callback start.
            # An over-budget GL readback additionally delays the next copy
            # from publication, so a slow readback cannot trigger an
            # immediate second GPU stall. This changes preview copies only.
            self._last_preview_capture = now
            publication_time = self._optional_clock(time.monotonic)
            if publication_time is None or publication_time < now:
                self.preview_clock_failures = (
                    getattr(self, "preview_clock_failures", 0) + 1
                )
                # Never fabricate a publication time on an invalid clock.
                self._last_preview_publication = None
                self._last_preview_readback_duration = 0.0
                publication_time = None
            else:
                self._last_preview_publication = publication_time
                elapsed = publication_time - now
                # A suspended host is not 3600s of active GPU readback.
                self._last_preview_readback_duration = (
                    elapsed if elapsed <= 3600.0 else 0.0
                )
            tracker = getattr(self, "_preview_cadence", None)
            if tracker is not None:
                tracker.record_published(publication_time, mode)
            return
        # Cores may supply a software frame even after HW negotiation.
        super().video(data, width, height, pitch)

    def performance_snapshot(self):
        """Bounded, allowlisted counters only; no game frames/device strings.

        A manual setup check can read these counters on the Tk thread while
        Dolphin continues running. Values are best-effort live aggregates,
        not a hardware GPU or physical-speaker pass/fail certificate.
        """
        metrics = self.native_run_timing.snapshot(
            gpu_readback_seconds=self.gpu_readback_seconds
        )
        metrics.update({
            "gpu_readback_calls": self.gpu_readback_calls,
            "gpu_readback_timing_samples": getattr(
                self, "gpu_readback_timing_samples", 0
            ),
            "gamecube_preview_clock_failures": getattr(
                self, "preview_clock_failures", 0
            ),
            "gpu_readback_max_ms": round(
                self.gpu_readback_max_seconds * 1000, 3
            ),
            "gamecube_hardware_frames": self.hardware_frames,
            "gamecube_preview_readback_skips": self.preview_readback_skips,
        })
        hist = getattr(self, "_readback_histogram", None)
        metrics.update(
            hist.snapshot() if hist is not None
            else ReadbackTimingHistogram().snapshot()
        )
        metrics.update(self.audio.delivery_snapshot())
        tracker = getattr(self, "_preview_cadence", None)
        metrics.update(
            tracker.snapshot() if tracker is not None
            else PreviewCadenceTracker().snapshot()
        )
        return {
            "format": "anything-plays-gamecube-performance",
            "version": 1,
            "scope": "aggregate_native_av_not_physical_hardware_certification",
            "metrics": metrics,
        }

    def run(self):
        with self._host_factory(width=640, height=576) as host:
            self.host = host
            try:
                # The context exists before retro_init; Dolphin negotiates
                # callbacks during startup and resets the core after loading.
                # CoreSession.run unloads Dolphin BEFORE the EGL host closes.
                super().run()
            finally:
                self.host = None
                if self.opengl_error is not None:
                    raise RuntimeError(self.opengl_error)
