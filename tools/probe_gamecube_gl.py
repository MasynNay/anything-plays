"""Linux proof of concept: Dolphin OpenGL -> hidden EGL FBO -> in-app RGB frames.

No extra game window is created. Uses the *bundled* Dolphin Libretro core,
and the existing CoreSession and in-memory game panel frame queue.
This is experimental, isolated CI only: it does not enable hardware mode in
the released player. Each native failure is contained in a child process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.gamecube_homebrew_fixture import verified_homebrew
from tools.libretro_gpu_egl import EGLFrameHost
from anything_plays.gba_emulator import CoreSession, Emulator
from anything_plays.libretro_video import RETRO_HW_FRAME_BUFFER_VALID

MIN_VALID_VIDEO_FRAMES = 3
MIN_USABLE_FPS = 20.0
MAX_CAPTURE_LOG = 26000


class SilentAudio:
    """Count native audio output without requiring an OS sound device."""
    def __init__(self):
        self.batch_calls = 0
        self.sample_frames = 0
        self.sample_rate = None

    def sample(self, left, right):
        self.sample_frames += 1

    def batch(self, pointer, frames):
        self.batch_calls += 1
        self.sample_frames += int(frames)
        return int(frames)

    def start(self, rate):
        self.sample_rate = rate

    def close(self):
        return None


class RamProgress:
    """Bounded digest sampling to distinguish paused CPU from missing video."""
    def __init__(self):
        self.digests = set()
        self.samples = 0
        self.bytes_per_sample = 0
        self.error = None

    def sample(self, core):
        import ctypes as C
        try:
            size = int(core.memory_size(2))  # RETRO_MEMORY_SYSTEM_RAM
            ptr = core.memory_data(2)
            if not ptr or not 1024 <= size <= 64 * 1024 * 1024:
                self.error = "Core did not expose a bounded system RAM pointer"
                return
            length = min(size, 8 * 1024 * 1024)
            digest = hashlib.sha256(C.string_at(ptr, length)).hexdigest()[:16]
            self.digests.add(digest)
            self.samples += 1
            self.bytes_per_sample = length
        except (OSError, ValueError, OverflowError) as exc:
            self.error = f"{type(exc).__name__}: {exc}"

    @property
    def changed(self):
        return len(self.digests) > 1


class GLCoreSession(CoreSession):
    """Specialized research session sharing the production Libretro callbacks."""

    def __init__(self, emulator, rom, core_path, cpu_core, single_core=False):
        super().__init__(emulator, "gamecube", rom, core_path)
        self._software_options.values[b"dolphin_renderer"] = b"Hardware"
        # Disable duplicate-XFB suppression only in this isolated test: the
        # pinned GLContextLR::Swap() otherwise sends a null video pointer
        # when g_is_duplicate_frame is set. Count those callbacks separately.
        self._software_options.values[b"dolphin_skip_dupe_frames"] = b"disabled"
        if single_core:
            self._software_options.values[b"dolphin_main_cpu_thread"] = b"disabled"
        # The installed preview deliberately defaults to cached interpreter
        # while its software renderer's JIT crashes. Restore *explicit* x86
        # JIT in the isolated GPU experiment so default vs cached evidence
        # still compares distinct Dolphin CPU engines.
        self._software_options.values[b"dolphin_cpu_core"] = (
            str(cpu_core).encode("ascii") if cpu_core is not None else b"1"
        )
        self.hardware = None
        self.hardware_requests = 0
        self.hardware_frames = 0
        self.null_video_callbacks = 0
        self.raw_video_callbacks = 0
        self.gpu_error = None
        self.opengl_version = None
        self.opengl_renderer = None
        self.opengl_vendor = None
        self.final_gl_error = None

    def environment(self, command, data):
        if command == 14:  # RETRO_ENVIRONMENT_SET_HW_RENDER
            self.hardware_requests += 1
            return bool(self.hardware and self.hardware.accept_core_render(data))
        if command == 0x10000 | 44:  # Hardware renderer's shared-context request
            return True
        return super().environment(command, data)

    def _load_game(self):
        super()._load_game()
        if not self.hardware or not self.hardware.core_reset:
            raise RuntimeError("Dolphin never requested a supported OpenGL core context")
        # No real swap chain exists: the hidden frontend owns the FBO while
        # Dolphin's core calls its usual context-reset function.
        self.hardware.reset_core()

    def video(self, data, width, height, pitch):
        self.raw_video_callbacks += 1
        if not data:
            self.null_video_callbacks += 1
            return
        if data == RETRO_HW_FRAME_BUFFER_VALID:
            try:
                rgb = self.hardware.read_frame(width, height)
            except (ValueError, RuntimeError) as exc:
                self.gpu_error = f"{type(exc).__name__}: {exc}"
                return
            with self.emulator.lock:
                self.emulator.frame = rgb
                self.emulator.frame_serial += 1
            self.hardware_frames += 1
            self.final_gl_error = self.hardware.last_gl_error
        else:
            super().video(data, width, height, pitch)

    def run(self):
        with EGLFrameHost(width=640, height=576) as hardware:
            self.hardware = hardware
            self.opengl_version = hardware.opengl_version
            self.opengl_renderer = hardware.opengl_renderer
            self.opengl_vendor = hardware.opengl_vendor
            print("GL-PROBE: renderer =", hardware.opengl_renderer, flush=True)
            print("GL-PROBE: version =", hardware.opengl_version, flush=True)
            # CoreSession.run closes/unloads the native core while this EGL
            # context is still current; only then is its FBO destroyed.
            try:
                super().run()
            finally:
                self.hardware = None


def _child(core, rom, seconds, report, cpu_core, single_core=False,
           exercise_controls=False):
    from PIL import Image
    from anything_plays import gba_emulator as engine

    class TimedNativeCore(engine.NativeCore):
        """Capture native retro_run call counts and stalls before teardown."""
        def __init__(self, path):
            super().__init__(path)
            wrapped_run = self.run
            self.run_calls = 0
            self.slowest_call_s = 0.0
            self.ram_progress = RamProgress()

            def timed_run():
                started = time.monotonic()
                try:
                    return wrapped_run()
                finally:
                    elapsed = time.monotonic() - started
                    self.run_calls += 1
                    self.slowest_call_s = max(self.slowest_call_s, elapsed)
                    if self.run_calls == 1 or self.run_calls % 180 == 0:
                        self.ram_progress.sample(self)
                    if self.run_calls <= 5 or self.run_calls % 60 == 0:
                        print("GL-PROBE: retro_run", self.run_calls,
                              "seconds", round(elapsed, 3), flush=True)
            self.run = timed_run

    # Confined to the disposable child; never patch the player's native core.
    engine.NativeCore = TimedNativeCore
    emu = Emulator()
    emu.system = "gamecube"
    emu.inputs.system = "gamecube"
    emu.core_path = str(core)
    emu.armed = False
    controller_state_requests = 0
    nonzero_controller_samples = 0
    actual_input_state = emu.inputs.state

    def measure_controller(port, device, index, identity):
        nonlocal controller_state_requests, nonzero_controller_samples
        result = actual_input_state(port, device, index, identity)
        controller_state_requests += 1
        if result:
            nonzero_controller_samples += 1
        return result

    emu.inputs.state = measure_controller
    session = GLCoreSession(emu, rom, str(core), cpu_core=cpu_core, single_core=single_core)
    session.audio.close()
    session.audio = SilentAudio()

    decoded, nonblank, last_shape = 0, 0, None
    unique_nonblank_frames = set()
    minimum_sampled_rgb = None
    maximum_sampled_rgb = None
    label = ("cached" if cpu_core == "5" else "jit") + ("-single" if single_core else "-dual")
    preview = report.with_name(f"gamecube-opengl-frame-{label}.png")
    first_frame = report.with_name(f"gamecube-opengl-first-{label}.png")
    original = session.video

    def inspect_frame(data, width, height, pitch):
        nonlocal decoded, nonblank, last_shape
        nonlocal minimum_sampled_rgb, maximum_sampled_rgb
        serial = emu.frame_serial
        original(data, width, height, pitch)
        if emu.frame_serial == serial:
            return
        decoded += 1
        if decoded <= 48 or decoded % 11 == 1:
            with emu.lock:
                frame = emu.frame
                if frame is not None:
                    last_shape = list(frame.shape)
                    lo, hi = int(frame.min()), int(frame.max())
                    minimum_sampled_rgb = lo if minimum_sampled_rgb is None else min(minimum_sampled_rgb, lo)
                    maximum_sampled_rgb = hi if maximum_sampled_rgb is None else max(maximum_sampled_rgb, hi)
                    if decoded == 1:
                        # Preserve black startup frames too; they help debug
                        # incorrect framebuffer ownership separately.
                        Image.fromarray(frame).save(first_frame, format="PNG")
                    if hi > 4 and lo != hi:
                        nonblank += 1
                        unique_nonblank_frames.add(
                            hashlib.sha256(frame.tobytes()).hexdigest()[:16]
                        )
                        if nonblank == 1:
                            Image.fromarray(frame).save(preview, format="PNG")
    session.video = inspect_frame

    controller_stop = threading.Event()
    controller_worker = None
    if exercise_controls:
        def drive_buttons():
            # The upstream GC-Controller-Test homebrew normally draws only
            # when a physical pad changes. Without button stimuli a healthy
            # hardware renderer looks frozen despite live RAM and audio.
            buttons = ("A", "B", "Left", "Right", "Up", "Down",
                       "X", "Y", "Start")
            i = 0
            while not controller_stop.is_set():
                button = buttons[i % len(buttons)]
                emu.inputs.set_manual(button, True)
                if controller_stop.wait(0.055):
                    break
                emu.inputs.set_manual(button, False)
                if controller_stop.wait(0.055):
                    break
                i += 1
            emu.inputs.release_manual()
        controller_worker = threading.Thread(
            target=drive_buttons, daemon=True, name="gamecube-gl-input-stimulus"
        )
        controller_worker.start()
    timer = threading.Timer(seconds, emu.stop_event.set)
    timer.daemon = True
    timer.start()
    began = time.monotonic()
    error = None
    try:
        print("GL-PROBE: EGL frontend and Dolphin core startup", flush=True)
        session.run()
        print("GL-PROBE: Dolphin core returned normally", flush=True)
        if session.gpu_error:
            error = session.gpu_error
        if emu.error:
            error = str(emu.error)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        emu.stop_event.set()
        timer.cancel()
        controller_stop.set()
        if controller_worker is not None:
            controller_worker.join(timeout=1)
        emu.inputs.release_manual()
    elapsed = max(time.monotonic() - began, 0.001)
    fps = round(decoded / elapsed, 2)
    valid = error is None and decoded >= MIN_VALID_VIDEO_FRAMES and nonblank > 0
    interactive_homebrew = (
        valid and exercise_controls and len(unique_nonblank_frames) >= 2
        and controller_state_requests >= 100 and nonzero_controller_samples >= 10
        and session.native.ram_progress.changed
    )
    result = {
        "system": "gamecube", "host": "linux-offscreen-egl-opengl",
        "cpu_mode": cpu_core or "default", "single_core": single_core, "core": core.name,
        "seconds_elapsed": round(elapsed, 3),
        "hardware_negotiations": session.hardware_requests,
        "hardware_frames": session.hardware_frames,
        "raw_video_callbacks": session.raw_video_callbacks,
        "null_video_callbacks": session.null_video_callbacks,
        "video_frames": decoded, "nonblank_samples": nonblank,
        "distinct_nonblank_rgb_frames": len(unique_nonblank_frames),
        "controller_stimulus": exercise_controls,
        "native_controller_poll_calls": controller_state_requests,
        "native_nonzero_controller_samples": nonzero_controller_samples,
        "input_driven_hardware_video_verified": interactive_homebrew,
        "last_shape": last_shape, "observed_fps": fps,
        "native_retro_run_calls": getattr(session.native, "run_calls", 0),
        "slowest_native_retro_run_seconds": round(
            getattr(session.native, "slowest_call_s", 0), 3
        ),
        "native_audio_batch_calls": session.audio.batch_calls,
        "native_audio_sample_frames": session.audio.sample_frames,
        "native_audio_sample_rate": session.audio.sample_rate,
        "ram_digest_samples": getattr(session.native.ram_progress, "samples", 0),
        "ram_digest_distinct": len(
            getattr(session.native.ram_progress, "digests", ())
        ),
        "ram_progress_observed": session.native.ram_progress.changed,
        "ram_sample_bytes": session.native.ram_progress.bytes_per_sample,
        "ram_sample_error": session.native.ram_progress.error,
        "gl_version": session.opengl_version,
        "gl_vendor": session.opengl_vendor,
        "gl_renderer": session.opengl_renderer,
        "last_gl_error": session.final_gl_error,
        "sampled_rgb_min": minimum_sampled_rgb,
        "sampled_rgb_max": maximum_sampled_rgb,
        "frames_valid": valid,
        "playback_probe_passed": valid and fps >= MIN_USABLE_FPS,
        "minimum_usable_fps": MIN_USABLE_FPS,
        "audio_tested": False, "camera_tested": False,
        "save_tested": False, "error": error,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result["playback_probe_passed"] else 1


def _parent(core, seconds, report, cpu_core, single_core=False,
            exercise_controls=False):
    data = {
        "system": "gamecube", "mode": "offscreen-egl", "cpu_mode": cpu_core or "default",
        "single_core": single_core,
        "controller_stimulus": exercise_controls,
        "passed": False, "native_exit_code": None, "timed_out": False,
        "details": None, "error": None, "console_tail": "",
    }
    started = time.monotonic()
    try:
        if not core.is_file():
            raise FileNotFoundError("Bundled Dolphin Libretro core not found")
        with tempfile.TemporaryDirectory(prefix="anything-plays-gl-ci-") as root:
            temp = Path(root)
            rom = verified_homebrew(temp / "GC-Controller-Test.dol")
            data["fixture_sha256"] = hashlib.sha256(rom.read_bytes()).hexdigest()
            child = temp / "child-report.json"
            command = [
                sys.executable, str(Path(__file__).resolve()),
                "--child", "--core", str(core), "--rom", str(rom),
                "--seconds", str(seconds), "--report", str(child),
            ]
            if cpu_core is not None:
                command.extend(["--cpu-core", str(cpu_core)])
            if single_core:
                command.append("--single-core")
            if exercise_controls:
                command.append("--exercise-controls")
            env = os.environ.copy()
            env["HOME"] = str(temp)
            env["XDG_CONFIG_HOME"] = str(temp / "config")
            try:
                result = subprocess.run(
                    command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    timeout=seconds + 25, text=True, check=False, env=env,
                )
                data["native_exit_code"] = result.returncode
                data["console_tail"] = result.stdout[-MAX_CAPTURE_LOG:]
            except subprocess.TimeoutExpired as exc:
                data["timed_out"] = True
                captured = exc.stdout or b""
                data["console_tail"] = (
                    captured.decode("utf-8", errors="replace")
                    if isinstance(captured, bytes) else captured
                )[-MAX_CAPTURE_LOG:]
            if child.is_file():
                data["details"] = json.loads(child.read_text())
            data["passed"] = (
                data["native_exit_code"] == 0
                and isinstance(data["details"], dict)
                and data["details"].get("playback_probe_passed") is True
            )
            label = ("cached" if cpu_core == "5" else "jit") + ("-single" if single_core else "-dual")
            for category in ("first", "frame"):
                filename = f"gamecube-opengl-{category}-{label}.png"
                frame = temp / filename
                if frame.is_file():
                    report.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(frame, report.with_name(filename))
                    data[f"{category}_image_saved"] = True
    except Exception as exc:
        data["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        data["total_seconds"] = round(time.monotonic() - started, 3)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(data, indent=2) + "\n")
        print(json.dumps(data, indent=2), flush=True)
    return 0 if data["passed"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument("--cpu-core", choices=("0", "5"))
    parser.add_argument("--single-core", action="store_true",
                        help="Diagnose Dolphin frame-step/FIFO synchronization without dual-core")
    parser.add_argument("--exercise-controls", action="store_true",
                        help="Pulse an actual GameCube pad and verify GPU redraws")
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.seconds <= 180:
        parser.error("seconds must be in [1,180]")
    core = args.core.resolve()
    report = args.report.resolve()
    if args.child:
        if args.rom is None:
            parser.error("--child requires --rom")
        return _child(core, args.rom.resolve(), args.seconds, report, args.cpu_core,
                      single_core=args.single_core,
                      exercise_controls=args.exercise_controls)
    return _parent(core, args.seconds, report, args.cpu_core,
                   single_core=args.single_core,
                   exercise_controls=args.exercise_controls)


if __name__ == "__main__":
    raise SystemExit(main())
