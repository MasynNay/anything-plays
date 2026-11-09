"""Isolated REAL GameCube software-video probe using licensed homebrew.

An ordinary native-core initialization check does not establish gameplay.
This runs the existing CoreSession with a pinned zlib-licensed GameCube DOL,
captures nonblank RGB video callbacks, and records observed frame throughput.
No commercial game, firmware, RetroArch, or standalone Dolphin is involved.

This is intentionally a two-process probe: a native crash or hung retro_run()
must not crash/indefinitely block the build host. Its report is CI evidence,
NOT a public compatibility or performance certification.
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

MAX_LOG_CHARS = 24000
# Merely drawing three frames does not make a GameCube game playable.
# This is deliberately conservative; full release QA still demands audio,
# controller, save, camera and long-uptime measurements on physical machines.
MIN_USABLE_FPS = 20.0


def evaluate_video_probe(error, frames, nonblank, elapsed):
    """Separate basic frame evidence from a minimally usable frame rate."""
    fps = round(frames / max(elapsed, 0.001), 2)
    frames_valid = error is None and frames >= 3 and nonblank >= 1
    return {
        "frames_valid": frames_valid,
        "minimum_usable_fps": MIN_USABLE_FPS,
        "fps_target_met": frames_valid and fps >= MIN_USABLE_FPS,
        "frames_per_second_observed": fps,
    }


class SilentProbeAudio:
    """Avoid requiring a physical audio device for video-only CI evidence."""

    def sample(self, left, right):
        return None

    def batch(self, pointer, frames):
        return int(frames)

    def start(self, rate):
        return None

    def close(self):
        return None


def _child(rom, core, seconds, report_path, cpu_core=None,
           exercise_controls=False, single_core=False, fast_controls=False,
           disable_fastmem=False):
    """Run real native gameplay; parent process enforces an absolute timeout."""
    import faulthandler

    # Native SIGSEGV traces belong in the report, not a discarded stderr
    # stream. Log each ABI lifecycle phase to identify the exact failure.
    faulthandler.enable(all_threads=True)
    from anything_plays import gba_emulator as engine
    from PIL import Image

    def stage(message):
        print("GC-PLAYBACK-STAGE: " + message, flush=True)

    class ProbeNativeCore(engine.NativeCore):
        """Delegate to the real core, logging calls that can fault natively."""

        def __init__(self, path):
            stage("dlopen begin")
            super().__init__(path)
            stage("dlopen succeeded")
            native_init = self.init
            native_load = self.load
            native_run = self.run
            native_device = self.set_controller_device
            if native_device is not None:
                def traced_device(port, device):
                    stage(f"retro_set_controller_port_device port={port} device={device}")
                    return native_device(port, device)
                self.set_controller_device = traced_device
            self._runs = 0

            def traced_init():
                stage("retro_init begin")
                value = native_init()
                stage("retro_init succeeded")
                return value

            def traced_load(game):
                stage("retro_load_game begin")
                result = native_load(game)
                stage(f"retro_load_game returned {result}")
                return result

            def traced_run():
                self._runs += 1
                if self._runs == 1 or self._runs % 120 == 0:
                    stage(f"retro_run frame {self._runs} begin")
                return native_run()

            self.init = traced_init
            self.load = traced_load
            self.run = traced_run

        def configure(self, *args, **kwargs):
            stage("configure callbacks begin")
            result = super().configure(*args, **kwargs)
            stage("configure callbacks succeeded")
            return result

        def close(self):
            stage("native deinitialize begin")
            try:
                return super().close()
            finally:
                stage("native deinitialize completed")

    class ProbeSession(engine.CoreSession):
        def _load_game(self):
            stage("query core identity and content path")
            return super()._load_game()

    # Instrument the production CoreSession's NativeCore construction only
    # inside this disposable child process; the installed app is unchanged.
    engine.NativeCore = ProbeNativeCore
    stage("creating emulator")
    emu = engine.Emulator()
    stage("emulator created")
    emu.system = "gamecube"
    emu.core_path = str(core)
    emu.inputs.system = "gamecube"
    emu.armed = False
    input_callback_calls = 0
    nonzero_input_samples = 0
    original_input_state = emu.inputs.state

    def observe_input_state(port, device, index, button_id):
        nonlocal input_callback_calls, nonzero_input_samples
        result = original_input_state(port, device, index, button_id)
        input_callback_calls += 1
        if result:
            nonzero_input_samples += 1
        return result

    emu.inputs.state = observe_input_state
    stage("creating game session")
    session = ProbeSession(emu, "gamecube", rom, str(core))
    stage("game session created")
    # CI-only CPU-mode override: isolate a generated-JIT-code segfault from
    # software-video initialization. The installed player's settings are
    # never changed by this diagnostic.
    if cpu_core is not None:
        session._software_options.values[b"dolphin_cpu_core"] = (
            str(cpu_core).encode("ascii")
        )
        stage("CPU emulation core override: " + str(cpu_core))
    if disable_fastmem:
        # Isolate emitted-code SIGSEGV from Dolphin's fast memory mapping,
        # retaining JIT core 1 for an apples-to-apples performance experiment.
        session._software_options.values[b"dolphin_fastmem"] = b"disabled"
        session._software_options.values[b"dolphin_fastmem_arena"] = b"disabled"
        stage("JIT fastmem and memory arena disabled")
    if single_core:
        # Test Dolphin's synchronous CPU/GPU execution as an alternative to
        # the dual-thread FIFO rendezvous that otherwise stalls presentation.
        session._software_options.values[b"dolphin_main_cpu_thread"] = b"disabled"
        stage("Single-core synchronous CPU/GPU emulation requested")
    session.audio.close()
    session.audio = SilentProbeAudio()

    decoded_frames = 0
    nonblank_frames = 0
    unique_nonblank_frames = set()
    last_shape = None
    preview = report_path.with_name("gamecube-homebrew-frame.png")
    original_video = session.video

    def observe_video(data, width, height, pitch):
        nonlocal decoded_frames, nonblank_frames, last_shape
        before = emu.frame_serial
        original_video(data, width, height, pitch)
        if emu.frame_serial != before:
            decoded_frames += 1
            if decoded_frames == 1:
                stage("first decoded software-video callback")
            if decoded_frames <= 20 or decoded_frames % 30 == 0:
                # Sample each early frame: controller-driven screen changes can
                # be sparse when a Libretro core suppresses duplicate video.
                with emu.lock:
                    frame = emu.frame
                    if frame is not None:
                        last_shape = list(frame.shape)
                        if int(frame.max()) > 4 and int(frame.min()) != int(frame.max()):
                            nonblank_frames += 1
                            unique_nonblank_frames.add(hashlib.sha256(frame.tobytes()).hexdigest()[:16])
                            if len(unique_nonblank_frames) == 1:
                                Image.fromarray(frame).save(preview, format="PNG")

    session.video = observe_video
    control_stop = threading.Event()
    control_worker = None
    exercise_controls = bool(exercise_controls or fast_controls)
    if exercise_controls:
        def exercise():
            # GC-Controller-Test is mostly static until controller state
            # changes. Two speeds let us distinguish a game-driven redraw
            # from a broken GPU or a bad input callback.
            buttons = ("A", "B", "Left", "Right", "Up", "Down",
                       "X", "Y", "Start")
            if fast_controls:
                i = 0
                while not control_stop.is_set():
                    button = buttons[i % len(buttons)]
                    emu.inputs.set_manual(button, True)
                    if control_stop.wait(0.028):
                        break
                    emu.inputs.set_manual(button, False)
                    if control_stop.wait(0.028):
                        break
                    i += 1
            else:
                for button in buttons:
                    if control_stop.wait(0.9):
                        break
                    emu.inputs.set_manual(button, True)
                    if control_stop.wait(0.4):
                        break
                    emu.inputs.set_manual(button, False)
            emu.inputs.release_manual()
        control_worker = threading.Thread(
            target=exercise, name="gamecube-ci-input-stimulus", daemon=True
        )
        control_worker.start()
    timer = threading.Timer(seconds, emu.stop_event.set)
    timer.daemon = True
    timer.start()
    start = time.monotonic()
    error = None
    try:
        stage("CoreSession.run begin")
        session.run()
        stage("CoreSession.run returned normally")
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        emu.stop_event.set()
        timer.cancel()
        control_stop.set()
        if control_worker is not None:
            control_worker.join(timeout=1)
        emu.inputs.release_manual()

    elapsed = round(time.monotonic() - start, 3)
    evidence = evaluate_video_probe(error, decoded_frames, nonblank_frames, elapsed)
    native_steps = getattr(session.native, "_runs", 0)
    interactive_valid = (
        error is None and exercise_controls and decoded_frames >= 3
        and len(unique_nonblank_frames) >= 3 and input_callback_calls >= 100
        and nonzero_input_samples >= 10 and native_steps >= 100
    )
    result = {
        "system": "gamecube",
        "cpu_core_mode": cpu_core or "default",
        "single_core": single_core,
        "core": core.name,
        "source": "pinned open-source GC-Controller-Test homebrew",
        "real_game_loaded": error is None,
        "video_callback_frames": decoded_frames,
        "nonblank_sampled_frames": nonblank_frames,
        "unique_nonblank_rgb_frames": len(unique_nonblank_frames),
        "controller_input_exercised": exercise_controls,
        "fast_controller_stimulus": fast_controls,
        "fastmem_disabled": disable_fastmem,
        "core_emulation_steps": native_steps,
        "emulation_steps_per_second": round(native_steps / max(elapsed, 0.001), 2),
        "static_homebrew_interactive_passed": interactive_valid,
        "input_callback_calls": input_callback_calls,
        "nonzero_gamecube_input_samples": nonzero_input_samples,
        "last_rgb_shape": last_shape,
        "seconds_elapsed": elapsed,
        **evidence,
        "audio_tested": False,
        "camera_actuation_tested": False,
        # A fast stream of blank or unchanging frames is not interactive
        # gameplay. Keep the probe verdict aligned with the workflow's
        # controller + changing-video acceptance, not FPS alone.
        "playback_probe_passed": evidence["fps_target_met"] and interactive_valid,
        "error": error,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result["playback_probe_passed"] else 1


def _parent(core, seconds, report, debugger=False, cpu_core=None,
            exercise_controls=False, single_core=False, fast_controls=False,
            disable_fastmem=False):
    """Keep a useful artifact even when native code segfaults or deadlocks."""
    started = time.monotonic()
    result = {
        "system": "gamecube",
        "probe": "real-homebrew-cpu-software-frames",
        "packaged_core": str(core),
        "cpu_core_mode": cpu_core or "default",
        "single_core": single_core,
        "controller_input_exercised": bool(exercise_controls or fast_controls),
        "fast_controller_stimulus": fast_controls,
        "fastmem_disabled": disable_fastmem,
        "seconds_requested": seconds,
        "probe_passed": False,
        "debugger": "gdb" if debugger else None,
        "timed_out": False,
        "child_returncode": None,
        "details": None,
        "error": None,
        "console_tail": "",
    }
    try:
        if not core.is_file():
            raise FileNotFoundError("Bundled GameCube core is missing")
        with tempfile.TemporaryDirectory(prefix="anything-plays-gamecube-ci-") as td:
            root = Path(td)
            homebrew = verified_homebrew(root / "GC-Controller-Test.dol")
            result["fixture_sha256"] = hashlib.sha256(homebrew.read_bytes()).hexdigest()
            child_report = root / "gamecube-child.json"
            env = os.environ.copy()
            env["HOME"] = str(root)
            env["XDG_CONFIG_HOME"] = str(root / "config")
            command = [
                sys.executable, str(Path(__file__).resolve()),
                "--child", "--core", str(core), "--rom", str(homebrew),
                "--seconds", str(seconds), "--report", str(child_report),
            ]
            if cpu_core is not None:
                command.extend(["--cpu-core", str(cpu_core)])
            if exercise_controls:
                command.append("--exercise-controls")
            if single_core:
                command.append("--single-core")
            if fast_controls:
                command.extend(["--fast-controls", "--exercise-controls"])
            if disable_fastmem:
                command.append("--disable-fastmem")
            if debugger:
                gdb = shutil.which("gdb")
                if gdb is None:
                    raise RuntimeError("GNU debugger is required for native crash traces")
                command = [
                    gdb, "--batch", "--quiet",
                    "-ex", "set pagination off",
                    "-ex", "set print thread-events off",
                    "-ex", "run",
                    "-ex", "thread apply all bt 24",
                    "--args", *command,
                ]
            try:
                completed = subprocess.run(
                    command, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True,
                    timeout=seconds + 30, check=False,
                )
                result["child_returncode"] = completed.returncode
                result["console_tail"] = completed.stdout[-MAX_LOG_CHARS:]
            except subprocess.TimeoutExpired as exc:
                result["timed_out"] = True
                data = exc.stdout or b""
                result["console_tail"] = (
                    data.decode("utf-8", "replace") if isinstance(data, bytes)
                    else data
                )[-MAX_LOG_CHARS:]
            if child_report.is_file():
                result["details"] = json.loads(child_report.read_text(encoding="utf-8"))
            result["probe_passed"] = (
                result["child_returncode"] == 0
                and isinstance(result["details"], dict)
                and result["details"].get("playback_probe_passed") is True
            )
            preview = child_report.with_name("gamecube-homebrew-frame.png")
            if preview.is_file():
                shutil.copyfile(preview, report.with_name(preview.name))
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        result["total_seconds"] = round(time.monotonic() - started, 2)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
    return 0 if result["probe_passed"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=25)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--debugger", action="store_true",
                        help="Run the native child under gdb and capture C++ backtraces")
    parser.add_argument("--cpu-core", choices=("0", "1", "5"),
                        help="Diagnostic: 0=interpreter, 1=x86 JIT, 5=cached interpreter")
    parser.add_argument("--disable-fastmem", action="store_true",
                        help="Disable JIT fastmem and memory arena to isolate native code crashes")
    parser.add_argument("--exercise-controls", action="store_true",
                        help="Pulse controller buttons to test changing rendered frames")
    parser.add_argument("--single-core", action="store_true",
                        help="Disable Dolphin's dual-core CPU thread for software renderer diagnosis")
    parser.add_argument("--fast-controls", action="store_true",
                        help="Stress controller-driven video callbacks on event-driven homebrew")
    parser.add_argument("--rom", type=Path)
    args = parser.parse_args(argv)
    if not 1 <= args.seconds <= 90:
        parser.error("seconds must be between 1 and 90")
    core = args.core.resolve()
    report = args.report.resolve()
    if args.child:
        if args.rom is None:
            parser.error("--rom is required for a child process")
        return _child(args.rom.resolve(), core, args.seconds, report,
                      cpu_core=args.cpu_core, exercise_controls=args.exercise_controls,
                      single_core=args.single_core, fast_controls=args.fast_controls,
                       disable_fastmem=args.disable_fastmem)
    return _parent(core, args.seconds, report, debugger=args.debugger,
                   cpu_core=args.cpu_core, exercise_controls=args.exercise_controls,
                   single_core=args.single_core, fast_controls=args.fast_controls,
                       disable_fastmem=args.disable_fastmem)


if __name__ == "__main__":
    raise SystemExit(main())
