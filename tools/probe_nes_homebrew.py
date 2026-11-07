"""Isolated, ROM-independent NES Libretro video and APU PCM smoke test.

The original test ROM is assembled in memory, never shipped to end users.
The child invokes the same CoreSession as Anything Plays, and the parent
contains segmentation faults / hangs with a hard timeout and JSON evidence.
"""
from __future__ import annotations

import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.nes_homebrew_fixture import write_nes_probe

MIN_FPS = 20.0
MAX_CAPTURE_CHARS = 12000


class ObservedAudio:
    """Measure real core-generated PCM without accessing a physical speaker."""
    def __init__(self):
        self.sample_rate = None
        self.samples = 0
        self.nonzero = 0
        self.peak = 0

    def start(self, rate):
        self.sample_rate = float(rate)

    def sample(self, left, right):
        self.samples += 1
        for value in (left, right):
            val = abs(int(value))
            self.nonzero += int(val != 0)
            self.peak = max(self.peak, val)

    def batch(self, pointer, frames):
        count = int(frames)
        if not 0 <= count <= 4096:
            return 0
        if pointer and count:
            arr = C.cast(pointer, C.POINTER(C.c_int16))
            for i in range(count * 2):
                val = abs(int(arr[i]))
                self.nonzero += int(val != 0)
                self.peak = max(self.peak, val)
            self.samples += count
        return count

    def close(self):
        pass


def _child(rom, core, seconds, report):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from anything_plays.gba_emulator import Emulator, CoreSession
    from PIL import Image
    emu = Emulator()
    emu.system = "nes"
    emu.inputs.system = "nes"
    emu.core_path = str(core)
    session = CoreSession(emu, "nes", rom, str(core))
    session.audio.close()
    session.audio = ObservedAudio()
    frames = 0
    nonblank = 0
    digests = set()
    preview = report.with_name("nes-test-frame.png")
    original = session.video

    def video(pointer, width, height, pitch):
        nonlocal frames, nonblank
        before = emu.frame_serial
        original(pointer, width, height, pitch)
        if emu.frame_serial == before:
            return
        frames += 1
        # The original ROM intentionally alternates palette colors every
        # frame. Sampling only every 10th frame is an even-period alias and
        # always sees the same phase, falsely reporting a frozen screen.
        # Inspect every startup frame, then use an odd stride.
        if frames > 48 and frames % 11 != 1:
            return
        with emu.lock:
            frame = emu.frame
            if frame is None:
                return
            low, high = int(frame.min()), int(frame.max())
            if high > 8 and high != low:
                nonblank += 1
                digests.add(hashlib.sha256(frame.tobytes()).hexdigest()[:16])
                if nonblank == 1:
                    Image.fromarray(frame).save(preview)
    session.video = video
    timer = threading.Timer(seconds, emu.stop_event.set)
    timer.daemon = True
    timer.start()
    start = time.monotonic()
    error = None
    try:
        session.run()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        emu.stop_event.set()
        timer.cancel()
    elapsed = max(time.monotonic() - start, 0.001)
    fps = round(frames / elapsed, 2)
    audio = session.audio
    passed = (
        error is None and frames >= 30 and fps >= MIN_FPS
        and nonblank >= 2 and len(digests) >= 2
        and audio.samples > 1000 and audio.nonzero > 100
        and audio.peak > 0 and audio.sample_rate is not None
    )
    data = {
        "system": "nes", "rom_source": "original project test ROM",
        "seconds_elapsed": round(elapsed, 3),
        "video_callback_frames": frames, "observed_fps": fps,
        "nonblank_sampled_frames": nonblank,
        "unique_nonblank_frame_hashes": len(digests),
        "apu_audio_sample_frames": audio.samples,
        "apu_nonzero_sample_values": audio.nonzero,
        "apu_sample_peak": audio.peak,
        "sample_rate": audio.sample_rate,
        "actual_speakers_tested": False,
        "playback_probe_passed": passed,
        "error": error,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(data, indent=2), flush=True)
    return 0 if passed else 1


def _parent(core, report, seconds):
    data = {
        "system": "nes", "passed": False, "native_exit_code": None,
        "timed_out": False, "error": None, "details": None, "fixture": None,
        "console_tail": "",
    }
    started = time.monotonic()
    try:
        if not core.is_file():
            raise FileNotFoundError("Missing standalone FCEUmm core")
        with tempfile.TemporaryDirectory(prefix="anything-plays-nes-ci-") as folder:
            directory = Path(folder)
            rom = directory / "original-nes-video-audio.nes"
            data["fixture"] = write_nes_probe(rom)
            child = directory / "nes-child.json"
            env = os.environ.copy()
            env["HOME"] = str(directory)
            env["XDG_CONFIG_HOME"] = str(directory / "config")
            command = [
                sys.executable, str(Path(__file__).resolve()),
                "--child", "--core", str(core), "--rom", str(rom),
                "--seconds", str(seconds), "--report", str(child),
            ]
            try:
                finished = subprocess.run(
                    command, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True,
                    timeout=seconds + 20, check=False,
                )
                data["native_exit_code"] = finished.returncode
                data["console_tail"] = finished.stdout[-MAX_CAPTURE_CHARS:]
            except subprocess.TimeoutExpired as exc:
                data["timed_out"] = True
                raw = exc.stdout or b""
                data["console_tail"] = (
                    raw.decode("utf-8", "replace") if isinstance(raw, bytes)
                    else raw
                )[-MAX_CAPTURE_CHARS:]
            if child.is_file():
                data["details"] = json.loads(child.read_text("utf-8"))
            data["passed"] = (
                data["native_exit_code"] == 0
                and isinstance(data["details"], dict)
                and data["details"].get("playback_probe_passed") is True
            )
            preview = child.with_name("nes-test-frame.png")
            if preview.is_file():
                report.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copyfile(preview, report.with_name(preview.name))
    except Exception as exc:
        data["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        data["elapsed"] = round(time.monotonic() - started, 2)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(data, indent=2) + "\n")
        print(json.dumps(data, indent=2), flush=True)
    return 0 if data["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=8)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--rom", type=Path)
    args = parser.parse_args()
    if not 2 <= args.seconds <= 60:
        parser.error("seconds must be between 2 and 60")
    if args.child:
        if args.rom is None:
            parser.error("--child requires --rom")
        return _child(args.rom.resolve(), args.core.resolve(),
                      args.seconds, args.report.resolve())
    return _parent(args.core.resolve(), args.report.resolve(), args.seconds)


if __name__ == "__main__":
    raise SystemExit(main())
