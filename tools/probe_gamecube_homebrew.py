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
import subprocess
import sys
import tempfile
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.gamecube_homebrew_fixture import verified_homebrew

MAX_LOG_CHARS = 8000


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


def _child(rom, core, seconds, report_path):
    """Run real native gameplay; parent process enforces an absolute timeout."""
    from anything_plays.gba_emulator import CoreSession, Emulator
    from PIL import Image

    emu = Emulator()
    emu.system = "gamecube"
    emu.core_path = str(core)
    emu.inputs.system = "gamecube"
    emu.armed = False
    session = CoreSession(emu, "gamecube", rom, str(core))
    session.audio.close()
    session.audio = SilentProbeAudio()

    decoded_frames = 0
    nonblank_frames = 0
    last_shape = None
    preview = report_path.with_name("gamecube-homebrew-frame.png")
    original_video = session.video

    def observe_video(data, width, height, pitch):
        nonlocal decoded_frames, nonblank_frames, last_shape
        before = emu.frame_serial
        original_video(data, width, height, pitch)
        if emu.frame_serial != before:
            decoded_frames += 1
            if decoded_frames % 5 == 1:
                # Inspect real decoded pixels, not merely libretro_run calls.
                with emu.lock:
                    frame = emu.frame
                    if frame is not None:
                        last_shape = list(frame.shape)
                        if int(frame.max()) > 4 and int(frame.min()) != int(frame.max()):
                            nonblank_frames += 1
                            Image.fromarray(frame).save(preview, format="PNG")

    session.video = observe_video
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

    elapsed = round(time.monotonic() - start, 3)
    result = {
        "system": "gamecube",
        "core": core.name,
        "source": "pinned open-source GC-Controller-Test homebrew",
        "real_game_loaded": error is None,
        "video_callback_frames": decoded_frames,
        "nonblank_sampled_frames": nonblank_frames,
        "last_rgb_shape": last_shape,
        "frames_per_second_observed": round(decoded_frames / max(elapsed, 0.001), 2),
        "seconds_elapsed": elapsed,
        "audio_tested": False,
        "camera_actuation_tested": False,
        "playback_probe_passed": error is None and decoded_frames >= 3 and nonblank_frames >= 1,
        "error": error,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result["playback_probe_passed"] else 1


def _parent(core, seconds, report):
    """Keep a useful artifact even when native code segfaults or deadlocks."""
    started = time.monotonic()
    result = {
        "system": "gamecube",
        "probe": "real-homebrew-cpu-software-frames",
        "packaged_core": str(core),
        "seconds_requested": seconds,
        "probe_passed": False,
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
                import shutil
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
    parser.add_argument("--rom", type=Path)
    args = parser.parse_args(argv)
    if not 1 <= args.seconds <= 90:
        parser.error("seconds must be between 1 and 90")
    core = args.core.resolve()
    report = args.report.resolve()
    if args.child:
        if args.rom is None:
            parser.error("--rom is required for a child process")
        return _child(args.rom.resolve(), core, args.seconds, report)
    return _parent(core, args.seconds, report)


if __name__ == "__main__":
    raise SystemExit(main())
