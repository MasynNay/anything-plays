"""Strict native video and SPC audio evidence for original SNES test code.

Loads a temporary source-generated LoROM through production CoreSession,
measures actual Snes9x rendered video and PCM, and isolates core crashes.
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
from tools.snes_homebrew_fixture import write_snes_probe
from tools.probe_nes_homebrew import ObservedAudio


def _child(core, rom, seconds, report):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from PIL import Image
    from anything_plays.gba_emulator import Emulator, CoreSession
    emu = Emulator()
    emu.system = "snes"
    emu.inputs.system = "snes"
    emu.core_path = str(core)
    session = CoreSession(emu, "snes", rom, str(core))
    session.audio.close()
    session.audio = ObservedAudio()
    original = session.video
    frames, nonblank, hashes = 0, 0, set()
    def capture(ptr, width, height, pitch):
        nonlocal frames, nonblank
        prior = emu.frame_serial
        original(ptr, width, height, pitch)
        if emu.frame_serial == prior:
            return
        frames += 1
        if frames > 50 and frames % 11 != 1:
            return
        with emu.lock:
            frame = emu.frame
            if frame is None:
                return
            if int(frame.max()) < 8 or int(frame.min()) == int(frame.max()):
                return
            nonblank += 1
            hashes.add(hashlib.sha256(frame.tobytes()).hexdigest()[:16])
            if nonblank == 1:
                Image.fromarray(frame).save(
                    report.with_name("snes-original-frame.png")
                )
    session.video = capture
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
    duration = max(0.001, time.monotonic() - start)
    audio = session.audio
    passed = (
        error is None and frames >= 30 and frames / duration >= 20
        and nonblank >= 3 and len(hashes) >= 2
        and audio.samples > 1000 and audio.nonzero > 100
        and audio.peak > 0 and 8000 <= (audio.sample_rate or 0) <= 192000
    )
    data = {
        "system": "snes", "program": "original 65c816 + SPC IPL test",
        "native_video_frames": frames,
        "observed_fps": round(frames / duration, 2),
        "sampled_nonblank_frames": nonblank,
        "distinct_rgb_frames": len(hashes),
        "native_pcm_frames": audio.samples,
        "native_nonzero_pcm_values": audio.nonzero,
        "native_pcm_peak": audio.peak,
        "native_pcm_sample_rate": audio.sample_rate,
        "physical_speakers_verified": False,
        "passed": passed, "error": error,
    }
    report.write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(data, indent=2), flush=True)
    return 0 if passed else 1


def _parent(core, report, seconds):
    data = {"system": "snes", "passed": False, "native_exit_code": None,
            "timed_out": False, "details": None, "error": None}
    try:
        if not core.is_file():
            raise FileNotFoundError("Missing embedded Snes9x core")
        with tempfile.TemporaryDirectory(prefix="anything-plays-snes-ci-") as d:
            folder = Path(d)
            rom = folder / "original-snes-ppu-spc.sfc"
            data["fixture"] = write_snes_probe(rom)
            child = folder / "child.json"
            env = os.environ.copy()
            env["HOME"] = str(folder)
            env["XDG_CONFIG_HOME"] = str(folder / "config")
            cmd = [sys.executable, str(Path(__file__).resolve()), "--child",
                   "--core", str(core), "--rom", str(rom),
                   "--seconds", str(seconds), "--report", str(child)]
            try:
                process = subprocess.run(
                    cmd, capture_output=True, text=True, env=env,
                    timeout=seconds + 25, check=False,
                )
                data["native_exit_code"] = process.returncode
                data["console_tail"] = (process.stdout + process.stderr)[-12000:]
            except subprocess.TimeoutExpired as exc:
                data["timed_out"] = True
                output = exc.stdout or b""
                data["console_tail"] = (
                    output.decode("utf-8", "replace")
                    if isinstance(output, bytes) else output
                )[-12000:]
            if child.is_file():
                data["details"] = json.loads(child.read_text("utf-8"))
            data["passed"] = (
                data["native_exit_code"] == 0
                and isinstance(data["details"], dict)
                and data["details"].get("passed") is True
            )
            image = child.with_name("snes-original-frame.png")
            if image.is_file():
                report.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(image, report.with_name(image.name))
    except Exception as exc:
        data["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(data, indent=2), flush=True)
    return 0 if data["passed"] else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--core", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--seconds", type=int, default=8)
    ap.add_argument("--rom", type=Path)
    ap.add_argument("--child", action="store_true")
    args = ap.parse_args()
    if not 2 <= args.seconds <= 60:
        ap.error("seconds must be 2..60")
    if args.child:
        if args.rom is None:
            ap.error("--child requires --rom")
        return _child(args.core.resolve(), args.rom.resolve(), args.seconds,
                      args.report.resolve())
    return _parent(args.core.resolve(), args.report.resolve(), args.seconds)


if __name__ == "__main__":
    raise SystemExit(main())
