"""Real Nintendo 64 software-video CI probe using public-domain homebrew.

The actual bundled ParaLLEl N64 library must decode nonblank frames through
Anything Plays' regular CoreSession. A successful dlopen alone is insufficient.
This two-process smoke probe cannot crash or hang the CI parent process and
never distributes any homebrew with an installer.
"""
from __future__ import annotations

import argparse
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
from tools.n64_homebrew_fixture import verified_homebrew

MIN_FRAMES = 3
MIN_USABLE_FPS = 20.0
MAX_LOG = 18000


class SilentAudio:
    def sample(self, left, right):
        return None

    def batch(self, pointer, frames):
        return int(frames)

    def start(self, rate):
        return None

    def close(self):
        return None


def _child(rom, core, seconds, report):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from anything_plays.gba_emulator import Emulator, CoreSession
    from PIL import Image

    emu = Emulator()
    emu.system = "n64"
    emu.inputs.system = "n64"
    emu.core_path = str(core)
    emu.armed = False
    session = CoreSession(emu, "n64", rom, str(core))
    session.audio.close()
    session.audio = SilentAudio()

    original_video = session.video
    frames = 0
    nonblank = 0
    image_path = report.with_name("n64-homebrew-frame.png")
    shape = None

    def inspect_frame(data, width, height, pitch):
        nonlocal frames, nonblank, shape
        before = emu.frame_serial
        original_video(data, width, height, pitch)
        if emu.frame_serial == before:
            return
        frames += 1
        if (frames % 5) != 1:
            return
        with emu.lock:
            frame = emu.frame
            if frame is not None:
                shape = list(frame.shape)
                if int(frame.max()) > 4 and int(frame.min()) != int(frame.max()):
                    nonblank += 1
                    if nonblank == 1:
                        Image.fromarray(frame).save(image_path, format="PNG")

    session.video = inspect_frame
    stop = threading.Timer(seconds, emu.stop_event.set)
    stop.daemon = True
    stop.start()
    start = time.monotonic()
    error = None
    try:
        print("N64-PROBE: core session start", flush=True)
        session.run()
        print("N64-PROBE: core session returned", flush=True)
        if emu.error:
            error = str(emu.error)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        emu.stop_event.set()
        stop.cancel()

    elapsed = max(time.monotonic() - start, 0.001)
    fps = round(frames / elapsed, 2)
    good = error is None and frames >= MIN_FRAMES and nonblank >= 1
    result = {
        "system": "n64",
        "fixture": "SaveTest-N64 public domain homebrew",
        "loaded": error is None,
        "video_callback_frames": frames,
        "nonblank_samples": nonblank,
        "last_frame_shape": shape,
        "seconds_elapsed": round(elapsed, 3),
        "observed_fps": fps,
        "minimum_usable_fps": MIN_USABLE_FPS,
        "frames_valid": good,
        "playback_probe_passed": good and fps >= MIN_USABLE_FPS,
        "camera_tested": False,
        "save_tested": False,
        "error": error,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result["playback_probe_passed"] else 1


def copy_frame_evidence(preview: Path, report: Path) -> bool:
    """Preserve frame evidence even when the CI output directory is absent."""
    preview = Path(preview)
    report = Path(report)
    if not preview.is_file():
        return False
    output = report.with_name(preview.name)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(preview, output)
    return True


def _parent(core, seconds, report):
    start = time.monotonic()
    result = {
        "system": "n64", "probe_passed": False, "timed_out": False,
        "error": None, "details": None, "console_tail": "",
        "child_returncode": None,
    }
    try:
        if not core.is_file():
            raise FileNotFoundError("Bundled ParaLLEl N64 core is missing")
        with tempfile.TemporaryDirectory(prefix="anything-plays-n64-probe-") as tmp:
            folder = Path(tmp)
            rom = folder / "savetest.z64"
            result["source"] = verified_homebrew(rom)
            child_report = folder / "n64-child.json"
            env = os.environ.copy()
            env["HOME"] = str(folder)
            env["XDG_CONFIG_HOME"] = str(folder / "config")
            cmd = [
                sys.executable, str(Path(__file__).resolve()),
                "--child", "--core", str(core),
                "--rom", str(rom), "--seconds", str(seconds),
                "--report", str(child_report),
            ]
            try:
                completed = subprocess.run(
                    cmd, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True,
                    timeout=seconds + 30, check=False,
                )
                result["child_returncode"] = completed.returncode
                result["console_tail"] = completed.stdout[-MAX_LOG:]
            except subprocess.TimeoutExpired as exc:
                result["timed_out"] = True
                output = exc.stdout or b""
                result["console_tail"] = (
                    output.decode("utf-8", "replace")
                    if isinstance(output, bytes) else output
                )[-MAX_LOG:]
            if child_report.is_file():
                result["details"] = json.loads(child_report.read_text("utf-8"))
            result["probe_passed"] = (
                result["child_returncode"] == 0
                and isinstance(result["details"], dict)
                and result["details"].get("playback_probe_passed") is True
            )
            image_path = child_report.with_name("n64-homebrew-frame.png")
            result["image_evidence_saved"] = copy_frame_evidence(image_path, report)
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        result["total_seconds"] = round(time.monotonic() - start, 3)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
    return 0 if result["probe_passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.seconds <= 90:
        parser.error("seconds must be 1..90")
    core = args.core.resolve()
    report = args.report.resolve()
    if args.child:
        if args.rom is None:
            parser.error("--rom is required for a probe child")
        return _child(args.rom.resolve(), core, args.seconds, report)
    return _parent(core, args.seconds, report)


if __name__ == "__main__":
    raise SystemExit(main())
