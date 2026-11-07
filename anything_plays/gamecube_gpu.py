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
import ctypes as C
from anything_plays.gba_emulator import CoreSession
from anything_plays.libretro_gpu_portable import choose_gamecube_gpu_host
from anything_plays.libretro_video import RETRO_HW_FRAME_BUFFER_VALID


class GameCubeHardwareSession(CoreSession):
    """Connect Libretro Dolphin to the same framebuffer the GUI displays."""

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
        self.raw_video_callbacks = 0
        self.null_video_callbacks = 0
        self.opengl_error = None
        self.hardware_requests = []

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
                self.hardware_requests.append(request)
            accepted = bool(
                self.host is not None and self.host.accept_core_render(data)
            )
            if request is not None:
                request["granted"] = accepted
                # Preserve native negotiation evidence even if a macOS
                # core aborts before Python can serialize its report.
                print("GAMECUBE-GPU-NEGOTIATION:", request, flush=True)
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
        if data == RETRO_HW_FRAME_BUFFER_VALID:
            try:
                rgb = self.host.read_frame(width, height)
            except (RuntimeError, ValueError) as exc:
                # Surface loss is a real playback failure, not an invitation
                # to keep emulating silently with black graphics.
                self.opengl_error = f"{type(exc).__name__}: {exc}"
                self.emulator.stop_event.set()
                return
            with self.emulator.lock:
                self.emulator.frame = rgb
                self.emulator.frame_serial += 1
            self.hardware_frames += 1
            return
        # Cores may supply a software frame even after HW negotiation.
        super().video(data, width, height, pitch)

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
