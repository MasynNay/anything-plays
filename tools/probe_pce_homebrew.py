"""Strict native Beetle PCE FAST HuCard A/V diagnostic with original CPU ROM.

Core loading is not success: real changing VDC frames AND nonzero HuC6280 PSG
PCM must arrive through Anything Plays' production embedded CoreSession.
The generated ROM is temporary and does not use or include a CD BIOS.
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
from tools.pce_homebrew_fixture import write_pce_probe
from tools.probe_nes_homebrew import ObservedAudio


def _child(core, rom, seconds, report):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from PIL import Image
    from anything_plays.gba_emulator import Emulator, CoreSession
    emu = Emulator()
    emu.system = emu.inputs.system = "pce"
    emu.core_path = str(core)
    session = CoreSession(emu, "pce", rom, str(core))
    session.audio.close()
    session.audio = ObservedAudio()
    raw_video = session.video
    callbacks = nonblank = 0
    hashes = set()
    any_hashes = set()
    lows, highs = 255, 0
    means = []
    first_size = None

    def capture(pointer, width, height, pitch):
        nonlocal callbacks, nonblank, lows, highs, first_size
        prior = emu.frame_serial
        raw_video(pointer, width, height, pitch)
        if prior == emu.frame_serial:
            return
        callbacks += 1
        if callbacks > 60 and callbacks % 11 != 1:
            return
        with emu.lock:
            frame = emu.frame
            if frame is None:
                return
            low, high = int(frame.min()), int(frame.max())
            lows, highs = min(lows, low), max(highs, high)
            if first_size is None:
                first_size = list(frame.shape)
                Image.fromarray(frame).save(report.with_name("pce-original-frame.png"))
            if len(means) < 12:
                means.append(round(float(frame.mean()), 3))
            digest = hashlib.sha256(frame.tobytes()).hexdigest()[:16]
            any_hashes.add(digest)
            if high > 8 and high != low:
                nonblank += 1
                hashes.add(digest)

    session.video = capture
    timeout = threading.Timer(seconds, emu.stop_event.set)
    timeout.daemon = True
    timeout.start()
    begun = time.monotonic()
    error = None
    try:
        session.run()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        emu.stop_event.set()
        timeout.cancel()
    duration = max(time.monotonic() - begun, .001)
    pcm = session.audio
    passed = (
        error is None and callbacks >= 30 and callbacks / duration >= 20
        and nonblank >= 3 and len(hashes) >= 2
        and pcm.samples > 1000 and pcm.nonzero > 100
        and pcm.peak > 0 and 8000 <= (pcm.sample_rate or 0) <= 192000
    )
    result = {
        "system": "pce", "source": "original HuC6280 HuCard, no CD BIOS",
        "native_rgb_callbacks": callbacks,
        "native_fps": round(callbacks / duration, 2),
        "sampled_nonblank_frames": nonblank,
        "distinct_nonblank_rgb_frames": len(hashes),
        "all_distinct_frames": len(any_hashes),
        "frame_shape": first_size, "observed_rgb_range": [lows, highs],
        "first_frame_means": means,
        "native_audio_pcm_frames": pcm.samples,
        "native_nonzero_pcm_values": pcm.nonzero,
        "native_audio_peak": pcm.peak,
        "sample_rate": pcm.sample_rate,
        "physical_speakers_tested": False,
        "passed": passed, "error": error,
    }
    report.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if passed else 1


def _parent(core, report, seconds):
    outcome = {"system": "pce", "passed": False,
               "native_exit_code": None, "timed_out": False,
               "details": None, "error": None}
    try:
        if not core.is_file():
            raise FileNotFoundError("Missing Mednafen PCE FAST Libretro core")
        with tempfile.TemporaryDirectory(prefix="ap-original-hucard-") as folder:
            root = Path(folder)
            rom = root / "original-pce-vdc-psg.pce"
            outcome["fixture"] = write_pce_probe(rom)
            child = root / "child.json"
            env = os.environ.copy()
            env["HOME"] = str(root)
            env["XDG_CONFIG_HOME"] = str(root / "config")
            cmd = [
                sys.executable, str(Path(__file__).resolve()), "--child",
                "--core", str(core), "--rom", str(rom),
                "--seconds", str(seconds), "--report", str(child),
            ]
            try:
                run = subprocess.run(
                    cmd, env=env, text=True, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, timeout=seconds + 25, check=False,
                )
                outcome["native_exit_code"] = run.returncode
                outcome["console_tail"] = run.stdout[-12000:]
            except subprocess.TimeoutExpired as exc:
                outcome["timed_out"] = True
                raw = exc.stdout or b""
                outcome["console_tail"] = (
                    raw.decode("utf-8", "replace") if isinstance(raw, bytes)
                    else raw
                )[-12000:]
            if child.is_file():
                outcome["details"] = json.loads(child.read_text("utf-8"))
            if child.with_name("pce-original-frame.png").is_file():
                shutil.copyfile(
                    child.with_name("pce-original-frame.png"),
                    report.with_name("pce-original-frame.png"),
                )
            outcome["passed"] = (
                outcome["native_exit_code"] == 0
                and isinstance(outcome["details"], dict)
                and outcome["details"].get("passed") is True
            )
    except Exception as exc:
        outcome["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(outcome, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(outcome, indent=2), flush=True)
    return 0 if outcome["passed"] else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--core",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--seconds",type=int,default=8)
    p.add_argument("--rom",type=Path)
    p.add_argument("--child",action="store_true")
    args=p.parse_args()
    if not 2<=args.seconds<=60:
        p.error("Seconds must be 2..60")
    if args.child:
        if args.rom is None:
            p.error("--child requires --rom")
        return _child(args.core.resolve(),args.rom.resolve(),args.seconds,
                      args.report.resolve())
    return _parent(args.core.resolve(),args.report.resolve(),args.seconds)


if __name__=="__main__":
    raise SystemExit(main())
