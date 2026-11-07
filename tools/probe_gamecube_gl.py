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
    def sample(self, left, right):
        return None

    def batch(self, pointer, frames):
        return int(frames)

    def start(self, rate):
        return None

    def close(self):
        return None


class GLCoreSession(CoreSession):
    """Specialized research session sharing the production Libretro callbacks."""

    def __init__(self, emulator, rom, core_path, cpu_core):
        super().__init__(emulator, "gamecube", rom, core_path)
        self._software_options.values[b"dolphin_renderer"] = b"Hardware"
        if cpu_core is not None:
            self._software_options.values[b"dolphin_cpu_core"] = (
                str(cpu_core).encode("ascii")
            )
        self.hardware = None
        self.hardware_requests = 0
        self.hardware_frames = 0
        self.gpu_error = None

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
        else:
            super().video(data, width, height, pitch)

    def run(self):
        with EGLFrameHost(width=640, height=576) as hardware:
            self.hardware = hardware
            # CoreSession.run closes/unloads the native core while this EGL
            # context is still current; only then is its FBO destroyed.
            try:
                super().run()
            finally:
                self.hardware = None


def _child(core, rom, seconds, report, cpu_core):
    from PIL import Image
    emu = Emulator()
    emu.system = "gamecube"
    emu.inputs.system = "gamecube"
    emu.core_path = str(core)
    emu.armed = False
    session = GLCoreSession(emu, rom, str(core), cpu_core=cpu_core)
    session.audio.close()
    session.audio = SilentAudio()

    decoded, nonblank, last_shape = 0, 0, None
    preview = report.with_name("gamecube-opengl-frame.png")
    original = session.video

    def inspect_frame(data, width, height, pitch):
        nonlocal decoded, nonblank, last_shape
        serial = emu.frame_serial
        original(data, width, height, pitch)
        if emu.frame_serial == serial:
            return
        decoded += 1
        if decoded == 1 or decoded % 10 == 0:
            with emu.lock:
                frame = emu.frame
                if frame is not None:
                    last_shape = list(frame.shape)
                    if int(frame.max()) > 4 and int(frame.min()) != int(frame.max()):
                        nonblank += 1
                        if nonblank == 1:
                            Image.fromarray(frame).save(preview, format="PNG")
    session.video = inspect_frame

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
    elapsed = max(time.monotonic() - began, 0.001)
    fps = round(decoded / elapsed, 2)
    valid = error is None and decoded >= MIN_VALID_VIDEO_FRAMES and nonblank > 0
    result = {
        "system": "gamecube", "host": "linux-offscreen-egl-opengl",
        "cpu_mode": cpu_core or "default", "core": core.name,
        "seconds_elapsed": round(elapsed, 3),
        "hardware_negotiations": session.hardware_requests,
        "hardware_frames": session.hardware_frames,
        "video_frames": decoded, "nonblank_samples": nonblank,
        "last_shape": last_shape, "observed_fps": fps,
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


def _parent(core, seconds, report, cpu_core):
    data = {
        "system": "gamecube", "mode": "offscreen-egl", "cpu_mode": cpu_core or "default",
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
            frame = temp / "gamecube-opengl-frame.png"
            if frame.is_file():
                report.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(frame, report.with_name("gamecube-opengl-frame.png"))
                data["frame_evidence_saved"] = True
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
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.seconds <= 90:
        parser.error("seconds must be in [1,90]")
    core = args.core.resolve()
    report = args.report.resolve()
    if args.child:
        if args.rom is None:
            parser.error("--child requires --rom")
        return _child(core, args.rom.resolve(), args.seconds, report, args.cpu_core)
    return _parent(core, args.seconds, report, args.cpu_core)


if __name__ == "__main__":
    raise SystemExit(main())
