"""Native Atari 7800 MARIA video and TIA PCM acceptance probe.

The ROM is original and generated only at CI time. Requires nonblank,
changing real ProSystem frames and core-produced nonzero audio samples.
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
from tools.atari7800_homebrew_fixture import write_atari7800_probe
from tools.probe_nes_homebrew import ObservedAudio


def _child(core, rom, seconds, report):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from PIL import Image
    from anything_plays.gba_emulator import Emulator, CoreSession

    emu = Emulator()
    emu.system = emu.inputs.system = "atari7800"
    emu.core_path = str(core)
    session = CoreSession(emu, "atari7800", rom, str(core))
    session.audio.close()
    session.audio = ObservedAudio()
    original = session.video
    frames = nonblank = 0
    hashes = set()
    all_frame_hashes = set()
    frame_rgb_low, frame_rgb_high = 255, 0
    first_frame_size = None
    first_frame_means = []

    def capture(ptr, width, height, pitch):
        nonlocal frames, nonblank, frame_rgb_low, frame_rgb_high, first_frame_size
        previous = emu.frame_serial
        original(ptr, width, height, pitch)
        if emu.frame_serial == previous:
            return
        frames += 1
        if frames > 60 and frames % 11 != 1:
            return
        with emu.lock:
            frame = emu.frame
            if frame is None:
                return
            low, high = int(frame.min()), int(frame.max())
            frame_rgb_low = min(frame_rgb_low, low)
            frame_rgb_high = max(frame_rgb_high, high)
            if first_frame_size is None:
                first_frame_size = list(frame.shape)
                Image.fromarray(frame).save(
                    report.with_name("atari7800-original-frame.png")
                )
            if len(first_frame_means) < 12:
                first_frame_means.append(round(float(frame.mean()), 3))
            digest = hashlib.sha256(frame.tobytes()).hexdigest()[:16]
            all_frame_hashes.add(digest)
            if high > 8 and high != low:
                nonblank += 1
                hashes.add(digest)

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
    duration = max(time.monotonic() - start, 0.001)
    audio = session.audio
    passed = (
        error is None and frames >= 30 and frames / duration >= 20
        and nonblank >= 3 and len(hashes) >= 2
        and audio.samples > 1000 and audio.nonzero > 100
        and audio.peak > 0 and 8000 <= (audio.sample_rate or 0) <= 192000
    )
    result = {
        "system": "atari7800",
        "program": "original 6502 MARIA raster and TIA channel zero",
        "real_frames": frames,
        "observed_fps": round(frames / duration, 2),
        "sampled_nonblank_frames": nonblank,
        "distinct_rgb_frames": len(hashes),
        "total_distinct_frame_hashes_including_blank": len(all_frame_hashes),
        "rgb_min_observed": frame_rgb_low,
        "rgb_max_observed": frame_rgb_high,
        "first_frame_shape": first_frame_size,
        "first_frame_mean_samples": first_frame_means,
        "native_audio_frames": audio.samples,
        "native_nonzero_pcm_values": audio.nonzero,
        "audio_peak": audio.peak,
        "sample_rate": audio.sample_rate,
        "physical_speakers_verified": False,
        "passed": passed, "error": error,
    }
    report.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if passed else 1


def _parent(core, report, seconds):
    result = {"system": "atari7800", "passed": False,
              "native_exit_code": None, "timed_out": False,
              "details": None, "error": None}
    try:
        if not core.is_file():
            raise FileNotFoundError("Missing native ProSystem core")
        with tempfile.TemporaryDirectory(prefix="ap-atari7800-original-") as d:
            folder = Path(d)
            rom = folder / "original-maria-psg.a78"
            result["fixture"] = write_atari7800_probe(rom)
            child = folder / "child.json"
            env = os.environ.copy()
            env["HOME"] = str(folder)
            env["XDG_CONFIG_HOME"] = str(folder / "config")
            cmd = [sys.executable, str(Path(__file__).resolve()), "--child",
                   "--core", str(core), "--rom", str(rom),
                   "--seconds", str(seconds), "--report", str(child)]
            try:
                p = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    env=env, text=True, check=False, timeout=seconds + 25,
                )
                result["native_exit_code"] = p.returncode
                result["console_tail"] = p.stdout[-12000:]
            except subprocess.TimeoutExpired as exc:
                result["timed_out"] = True
                raw = exc.stdout or b""
                result["console_tail"] = (
                    raw.decode("utf-8", "replace")
                    if isinstance(raw, bytes) else raw
                )[-12000:]
            if child.is_file():
                result["details"] = json.loads(child.read_text("utf-8"))
            result["passed"] = (
                result["native_exit_code"] == 0
                and isinstance(result["details"], dict)
                and result["details"].get("passed") is True
            )
            preview = child.with_name("atari7800-original-frame.png")
            if preview.is_file():
                report.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(preview, report.with_name(preview.name))
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
    return 0 if result["passed"] else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--core", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--seconds", type=int, default=8)
    p.add_argument("--rom", type=Path)
    p.add_argument("--child", action="store_true")
    a = p.parse_args()
    if not 2 <= a.seconds <= 60:
        p.error("--seconds must be 2..60")
    if a.child:
        if a.rom is None:
            p.error("--child requires --rom")
        return _child(a.core.resolve(), a.rom.resolve(), a.seconds,
                      a.report.resolve())
    return _parent(a.core.resolve(), a.report.resolve(), a.seconds)


if __name__ == "__main__":
    raise SystemExit(main())
