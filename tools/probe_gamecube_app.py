"""Exercise the actual embedded GameCube player, not just its research adapter.

Linux CI uses Dolphin Libretro's native accelerated GPU path, the regular
CoreSession inputs / frame queue, and a real AudioSink subclass that forwards
stereo PCM to PortAudio when an output device exists. The headless runner
typically lacks a speaker; we report that limitation explicitly.

The native game runs only in an isolated subprocess. No commercial ROM,
standalone Dolphin process, RetroArch installation or external game window
is used. This verifies input-driven homebrew video, not continuous 3D game FPS.
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

MAX_LOG = 15000

# Only these fixed, privacy-safe identifiers may reach private CI receipts.
GC_BOOT_PHASES = frozenset((
    "pre_libretro_load", "gpu_context_constructing",
    "gpu_context_construct_failed", "gpu_context_opening",
    "gpu_context_open_failed", "gpu_context_ready",
    "gpu_render_negotiating", "gpu_render_rejected", "gpu_render_accepted",
    "libretro_loading_game", "libretro_load_rejected",
    "game_loaded_postload_failure", "game_loaded",
))
GC_FAILURE_CODES = frozenset((
    "none", "retro_load_game_rejected", "unsupported_hw_render_context",
    "controller_port_api_missing", "gpu_surface_readback_failed",
    "native_core_missing", "pre_game_load_failure", "game_load_failure",
    "post_game_load_failure", "gpu_factory_failure", "gpu_open_failure",
    "native_core_init_failure", "native_hw_context_rejected",
    "native_core_init_failure_after_hw_accept",
))


def classify_gamecube_boot_failure(error, phase):
    """Classify an error by constant code, never expose its raw message."""
    if error is None:
        return "none"
    message = str(error)
    if "need_fullpath=" in message and " rejected " in message:
        return "retro_load_game_rejected"
    if "did not register a supported accelerated render context" in message:
        return "unsupported_hw_render_context"
    if "has no controller-port API" in message:
        return "controller_port_api_missing"
    if "bundled emulator core not found" in message:
        return "native_core_missing"
    if "GPU" in message and "readback" in message:
        return "gpu_surface_readback_failed"
    return {
        "pre_libretro_load": "pre_game_load_failure",
        "gpu_context_constructing": "gpu_factory_failure",
        "gpu_context_construct_failed": "gpu_factory_failure",
        "gpu_context_opening": "gpu_open_failure",
        "gpu_context_open_failed": "gpu_open_failure",
        "gpu_context_ready": "native_core_init_failure",
        "gpu_render_negotiating": "native_hw_context_rejected",
        "gpu_render_rejected": "native_hw_context_rejected",
        "gpu_render_accepted": "native_core_init_failure_after_hw_accept",
        "libretro_loading_game": "game_load_failure",
        "libretro_load_rejected": "game_load_failure",
        "game_loaded_postload_failure": "post_game_load_failure",
        "game_loaded": "post_game_load_failure",
    }.get(phase, "pre_game_load_failure")

class BootTrackedGPUContext:
    """Research-only wrapper: preserve real GPU host lifecycle semantics."""

    def __init__(self, delegate, phase_callback):
        self._delegate = delegate
        self._phase_callback = phase_callback

    def __enter__(self):
        self._phase_callback("gpu_context_opening")
        try:
            host = self._delegate.__enter__()
        except Exception:
            self._phase_callback("gpu_context_open_failed")
            raise
        self._phase_callback("gpu_context_ready")
        return host

    def __exit__(self, exc_type, exc, tb):
        # Never intercept or suppress production context cleanup exceptions.
        return self._delegate.__exit__(exc_type, exc, tb)


def make_tracked_gpu_context(factory, phase_callback, **kwargs):
    """Observe GPU factory vs context-entry failure, with no raw logs."""
    phase_callback("gpu_context_constructing")
    try:
        context = factory(**kwargs)
    except Exception:
        phase_callback("gpu_context_construct_failed")
        raise
    return BootTrackedGPUContext(context, phase_callback)


def linux_rss_mb():
    """Sample the actual native Dolphin worker's resident memory."""
    if not sys.platform.startswith("linux"):
        return None
    try:
        pages = int(Path("/proc/self/statm").read_text("ascii").split()[1])
        return pages * os.sysconf("SC_PAGE_SIZE") / 1048576
    except (OSError, IndexError, ValueError):
        return None



def _child(core, rom, report, seconds, require_audio=False,
           require_animated=False, max_growth_mb=None,
           require_controller_effect=False):
    import faulthandler
    faulthandler.enable(all_threads=True)
    import ctypes as C
    import numpy as np
    from PIL import Image
    from anything_plays.gba_emulator import Emulator
    from anything_plays.gamecube_gpu import GameCubeHardwareSession
    from anything_plays.libretro_audio import AudioSink

    class ObservedActualAudioSink(AudioSink):
        def __init__(self):
            super().__init__()
            self.sample_rate = None
            self.pcm_frames = 0
            self.pcm_nonzero = 0

        def start(self, rate):
            self.sample_rate = float(rate)
            super().start(rate)

        def sample(self, left, right):
            self.pcm_frames += 1
            self.pcm_nonzero += int(left != 0) + int(right != 0)
            return super().sample(left, right)

        def batch(self, pointer, frames):
            count = int(frames)
            if pointer and 0 < count <= 192000:
                raw = np.ctypeslib.as_array(
                    C.cast(pointer, C.POINTER(C.c_int16)),
                    shape=(count * 2,),
                )
                self.pcm_frames += count
                self.pcm_nonzero += int(np.count_nonzero(raw))
            return super().batch(pointer, frames)

    class ResearchGameCubeHardwareSession(GameCubeHardwareSession):
        # Track production loader boundaries without modifying the loader.
        # CoreSession.close() can clear native.loaded after an exception.
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.qa_boot_phase = "pre_libretro_load"
            production_factory = self._host_factory
            self._host_factory = lambda **options: make_tracked_gpu_context(
                production_factory, self._record_qa_phase, **options
            )

        def _record_qa_phase(self, phase):
            self.qa_boot_phase = phase

        def environment(self, command, data):
            if command != 14:
                return super().environment(command, data)
            self.qa_boot_phase = "gpu_render_negotiating"
            granted = super().environment(command, data)
            self.qa_boot_phase = (
                "gpu_render_accepted" if granted else "gpu_render_rejected"
            )
            return granted

        def _load_game(self):
            self.qa_boot_phase = "libretro_loading_game"
            try:
                super()._load_game()
            except Exception:
                self.qa_boot_phase = (
                    "game_loaded_postload_failure"
                    if self.native is not None and self.native.loaded
                    else "libretro_load_rejected"
                )
                raise
            self.qa_boot_phase = "game_loaded"

    emu = Emulator()
    emu.system = "gamecube"
    emu.core_path = str(core)
    emu.inputs.system = "gamecube"
    session = ResearchGameCubeHardwareSession(emu, rom, str(core))
    session.audio.close()
    session.audio = ObservedActualAudioSink()
    original_video = session.video
    unique_frames = set()
    rss_samples = []
    frame_callbacks = 0
    sampled_nonblank = 0
    controller_active_frames = 0
    controller_idle_frames = 0
    preview = report.with_name("gamecube-app-accelerated-frame.png")

    def sample_real_output(data, width, height, pitch):
        nonlocal frame_callbacks, sampled_nonblank
        nonlocal controller_active_frames, controller_idle_frames
        before = emu.frame_serial
        original_video(data, width, height, pitch)
        if emu.frame_serial == before:
            return
        frame_callbacks += 1
        # Look at an unobstructed left-edge background sample, well away
        # from the rotating cube. The actual original PowerPC homebrew
        # changes GX_SetCopyClear only while PAD_BUTTON_A is held.
        # This is a direct framebuffer effect, not a mock input poll.
        with emu.lock:
            image = emu.frame
            if image is not None and image.shape[0] >= 24 and image.shape[1] >= 96:
                r, g, b = map(int, image[image.shape[0] // 2,
                                         image.shape[1] // 12, :3])
                if g >= 135 and g >= r + 60 and g >= b + 55:
                    controller_active_frames += 1
                if r <= 45 and g <= 65 and b <= 95:
                    controller_idle_frames += 1
        if frame_callbacks % 120 == 0:
            resident = linux_rss_mb()
            if resident is not None:
                rss_samples.append((time.monotonic(), resident))
        if frame_callbacks <= 65 or frame_callbacks % 31 == 1:
            with emu.lock:
                frame = emu.frame
                if frame is None:
                    return
                low, high = int(frame.min()), int(frame.max())
                if low == high or high < 5:
                    return
                sampled_nonblank += 1
                fingerprint = hashlib.sha256(frame.tobytes()).hexdigest()[:16]
                unique_frames.add(fingerprint)
                if sampled_nonblank == 1:
                    Image.fromarray(frame).save(preview)

    session.video = sample_real_output
    original_state = emu.inputs.state
    polls, nonzero_polls = 0, 0

    def sample_real_input(port, device, index, identity):
        nonlocal polls, nonzero_polls
        value = original_state(port, device, index, identity)
        polls += 1
        if value:
            nonzero_polls += 1
        return value

    emu.inputs.state = sample_real_input
    stop = threading.Event()

    def press_buttons():
        buttons = ("A", "B", "Left", "Right", "X", "Y", "Start")
        index = 0
        while not stop.is_set():
            button = buttons[index % len(buttons)]
            emu.inputs.set_manual(button, True)
            if stop.wait(0.22 if button == "A" else 0.055):
                break
            emu.inputs.set_manual(button, False)
            if stop.wait(0.055):
                break
            index += 1
        emu.inputs.release_manual()

    controller = threading.Thread(target=press_buttons, daemon=True)
    controller.start()
    timeout = threading.Timer(seconds, emu.stop_event.set)
    timeout.daemon = True
    timeout.start()
    start = time.monotonic()
    error = None
    try:
        session.run()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        emu.stop_event.set()
        stop.set()
        timeout.cancel()
        controller.join(timeout=2)
        emu.inputs.release_manual()
    elapsed = max(time.monotonic() - start, 0.001)
    core_visual_ok = (
        error is None and frame_callbacks >= 12 and sampled_nonblank >= 6
        and len(unique_frames) >= 3 and polls >= 100 and nonzero_polls >= 10
        and session.audio.pcm_frames >= 1000
    )
    continuous_video_ok = (
        frame_callbacks / elapsed >= 20 and len(unique_frames) >= 8
    )
    real_audio_ok = (
        session.audio.pcm_nonzero >= 200
        and 8000 <= (session.audio.sample_rate or 0) <= 192000
    )
    warmup = min(90.0, max(5.0, seconds * 0.15))
    stable = [v for when, v in rss_samples if when - start >= warmup]
    growth = max(0.0, max(stable) - stable[0]) if stable else None
    memory_ok = (max_growth_mb is None or
                 (growth is not None and growth <= max_growth_mb))
    controller_effect_ok = (
        controller_active_frames >= 2 and controller_idle_frames >= 2
        and nonzero_polls >= 10
    )
    passed = (
        core_visual_ok
        and (not require_animated or continuous_video_ok)
        and (not require_audio or real_audio_ok)
        and memory_ok
        and (not require_controller_effect or controller_effect_ok)
    )
    evidence = {
        "system": "gamecube",
        "backend": "production GameCubeHardwareSession + platform GPU host",
        "native_startup_phase": session.qa_boot_phase,
        "native_boot_failure_category": classify_gamecube_boot_failure(
            error, session.qa_boot_phase
        ),
        "native_hw_context_request_count": len(session.hardware_requests),
        "native_hw_context_accepted": any(
            request.get("granted") is True
            for request in session.hardware_requests
        ),
        "core": core.name,
        "uses_external_dolphin": False,
        "uses_separate_game_window": False,
        "passes_in_app_frame_queue": True,
        "seconds": round(elapsed, 3),
        # 'continuous_render_fps' below is HISTORICAL preview readback
        # throughput, not emulated-game FPS. Count the distinct pipeline
        # stages so a synthetic menu with sparse video callbacks cannot
        # be misinterpreted as a 5-FPS emulator.
        "gamecube_rgb_callback_frames": frame_callbacks,
        "raw_libretro_video_callbacks": session.raw_video_callbacks,
        "null_libretro_video_callbacks": session.null_video_callbacks,
        "preview_readback_skips": session.preview_readback_skips,
        "native_run_loop_fps": round(
            session.native_run_timing.native_run_calls / elapsed, 2
        ),
        "gamecube_preview_capture_fps": round(frame_callbacks / elapsed, 2),
        "sampled_nonblank_frames": sampled_nonblank,
        "distinct_rgb_frame_hashes": len(unique_frames),
        "native_controller_polls": polls,
        "nonzero_controller_polls": nonzero_polls,
        "native_pcm_frame_samples": session.audio.pcm_frames,
        "native_pcm_nonzero_values": session.audio.pcm_nonzero,
        "continuous_render_fps": round(frame_callbacks / elapsed, 2),
        "gpu_readback_calls": session.gpu_readback_calls,
        "gpu_readback_total_seconds": round(session.gpu_readback_seconds, 4),
        "gpu_readback_mean_ms": round(
            1000.0 * session.gpu_readback_seconds /
            max(session.gpu_readback_calls, 1), 3),
        "gpu_readback_max_ms": round(
            1000.0 * session.gpu_readback_max_seconds, 3),
        "gpu_readback_fraction_elapsed": round(
            session.gpu_readback_seconds / elapsed, 4),
        # The native-loop timings encompass Dolphin CPU/JIT + GPU work
        # + callbacks. GL readback is a measured SUBSET, not a competing
        # independent time bucket.
        **session.native_run_timing.snapshot(
            gpu_readback_seconds=session.gpu_readback_seconds
        ),
        "rss_sample_count": len(rss_samples),
        "rss_warmup_seconds": warmup,
        "native_rss_growth_mb": None if growth is None else round(growth, 2),
        "native_rss_growth_limit_mb": max_growth_mb,
        "native_rss_growth_verified": memory_ok,
        "native_controller_active_green_frames": controller_active_frames,
        "native_controller_idle_dark_frames": controller_idle_frames,
        "gamecube_button_a_visual_effect_verified": controller_effect_ok,
        "controller_effect_required": require_controller_effect,
        "continuous_video_20fps_requirement_met": continuous_video_ok,
        "native_nonzero_pcm_requirement_met": real_audio_ok,
        "continuous_animated_video_required": require_animated,
        "nonzero_gamecube_audio_required": require_audio,
        "native_pcm_sample_rate": session.audio.sample_rate,
        "native_gpu_requests": session.hardware_requests,
        "requested_cpu_core": session._software_options.values.get(
            b"dolphin_cpu_core", b"?"
        ).decode("ascii", "replace"),
        "native_cpu_architecture": __import__("platform").machine(),
        "system_audio_device_active": session.audio.output_active,
        "physical_speaker_tested": False,
        "continuous_3d_gameplay_tested": False,
        "gamecube_ready_for_release": False,
        "passed": passed,
        "error": error,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2), flush=True)
    return 0 if passed else 1


def _parent(core, report, seconds, rom_override=None,
            require_audio=False, require_animated=False,
            max_growth_mb=None, require_controller_effect=False):
    outcome = {
        "probe": "production embedded GameCube rendering / native sound",
        "passed": False, "native_exit_code": None,
        "timed_out": False, "details": None, "error": None,
    }
    report = report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not core.is_file():
            raise FileNotFoundError("Missing native Dolphin core")
        with tempfile.TemporaryDirectory(prefix="ap-v30-gamecube-app-") as tmp:
            root = Path(tmp)
            if rom_override is not None:
                own = Path(rom_override).resolve()
                if (own.suffix.lower() != ".dol" or not own.is_file()
                        or not 100 <= own.stat().st_size <= 4 * 1024 * 1024):
                    raise ValueError("Expected an original bounded GameCube .dol")
                rom = root / "AnythingPlays-Original-AV.dol"
                shutil.copyfile(own, rom)
                outcome["original_av_dol_sha256"] = hashlib.sha256(
                    rom.read_bytes()).hexdigest()
            else:
                rom = verified_homebrew(root / "GC-Controller-Test.dol")
            # The verified immutable zlib fixture has a stable extracted
            # DOL digest. Record just its SHA to independently attest which
            # test binary the installed 3.2 native GPU path actually ran.
            outcome["fixture_sha256"] = hashlib.sha256(rom.read_bytes()).hexdigest()
            child_report = root / "child.json"
            command = [
                sys.executable, str(Path(__file__).resolve()), "--child",
                "--core", str(core), "--rom", str(rom),
                "--report", str(child_report), "--seconds", str(seconds),
            ]
            if require_audio:
                command.append("--require-audio")
            if require_animated:
                command.append("--require-animated")
            if max_growth_mb is not None:
                command.extend(["--max-growth-mb", str(max_growth_mb)])
            if require_controller_effect:
                command.append("--require-controller-effect")
            env = os.environ.copy()
            env["HOME"] = str(root)
            env["XDG_CONFIG_HOME"] = str(root / "config")
            try:
                finished = subprocess.run(
                    command, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True,
                    timeout=seconds + 35, check=False,
                )
                outcome["native_exit_code"] = finished.returncode
                outcome["console_tail"] = finished.stdout[-MAX_LOG:]
            except subprocess.TimeoutExpired as exc:
                outcome["timed_out"] = True
                raw = exc.stdout or b""
                outcome["console_tail"] = (
                    raw.decode("utf-8", "replace") if isinstance(raw, bytes)
                    else raw
                )[-MAX_LOG:]
            if child_report.is_file():
                outcome["details"] = json.loads(child_report.read_text())
            outcome["passed"] = (
                outcome["native_exit_code"] == 0
                and isinstance(outcome["details"], dict)
                and outcome["details"].get("passed") is True
            )
            frame = child_report.with_name("gamecube-app-accelerated-frame.png")
            if frame.is_file():
                shutil.copyfile(frame, report.with_name(frame.name))
    except Exception as exc:
        outcome["error"] = f"{type(exc).__name__}: {exc}"
    report.write_text(json.dumps(outcome, indent=2) + "\n")
    print(json.dumps(outcome, indent=2), flush=True)
    return 0 if outcome["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=15)
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--require-audio", action="store_true",
                        help="Require actual nonzero GameCube PCM samples")
    parser.add_argument("--require-animated", action="store_true",
                        help="Require continuously changing frames at >=20fps")
    parser.add_argument("--max-growth-mb", type=float,
                        help="Bound RSS growth after warm-up, on Linux")
    parser.add_argument("--require-controller-effect", action="store_true",
                        help="Require native GameCube A-button visual response")
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if not 2 <= args.seconds <= 1800:
        parser.error("--seconds must be 2..1800")
    if args.max_growth_mb is not None and not 0 <= args.max_growth_mb <= 4096:
        parser.error("--max-growth-mb must be 0..4096")
    if args.child:
        if args.rom is None:
            parser.error("--rom is required for child")
        return _child(
            args.core.resolve(), args.rom.resolve(),
            args.report.resolve(), args.seconds,
            require_audio=args.require_audio,
            require_animated=args.require_animated,
            max_growth_mb=args.max_growth_mb,
            require_controller_effect=args.require_controller_effect,
        )
    return _parent(
        args.core.resolve(), args.report.resolve(), args.seconds,
        rom_override=args.rom, require_audio=args.require_audio,
        require_animated=args.require_animated,
        max_growth_mb=args.max_growth_mb,
        require_controller_effect=args.require_controller_effect,
    )


if __name__ == "__main__":
    raise SystemExit(main())
