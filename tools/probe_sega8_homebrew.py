"""Native Genesis Plus GX audio/video check with original SMS and GG cartridges.

Runs each test in an isolated child process so native faults cannot mark
a false positive. Requires changing, nonblank RGB and genuine core PSG PCM.
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
from tools.sega8_homebrew_fixture import SYSTEMS, write_sega8_probe
from tools.probe_nes_homebrew import ObservedAudio


def _child(system, core, rom, seconds, report):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from PIL import Image
    from anything_plays.gba_emulator import Emulator, CoreSession

    emu = Emulator()
    emu.system = system
    emu.inputs.system = system
    emu.core_path = str(core)
    session = CoreSession(emu, system, rom, str(core))
    session.audio.close()
    session.audio = ObservedAudio()
    original = session.video
    frames, nonblank, fingerprints = 0, 0, set()

    def capture(pointer, width, height, pitch):
        nonlocal frames, nonblank
        previous = emu.frame_serial
        original(pointer, width, height, pitch)
        if emu.frame_serial == previous:
            return
        frames += 1
        if frames > 55 and frames % 11 != 1:
            return
        with emu.lock:
            image = emu.frame
            if image is None:
                return
            if int(image.max()) < 8 or int(image.max()) == int(image.min()):
                return
            nonblank += 1
            fingerprints.add(hashlib.sha256(image.tobytes()).hexdigest()[:16])
            if nonblank == 1:
                Image.fromarray(image).save(
                    report.with_name(f"{system}-test-frame.png")
                )
    session.video = capture
    timer = threading.Timer(seconds, emu.stop_event.set)
    timer.daemon = True
    timer.start()
    started = time.monotonic()
    error = None
    try:
        session.run()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        emu.stop_event.set()
        timer.cancel()
    duration = max(0.001, time.monotonic() - started)
    audio = session.audio
    passed = (
        error is None and frames >= 30 and frames / duration >= 20
        and nonblank >= 3 and len(fingerprints) >= 2
        and audio.samples > 1000 and audio.nonzero > 100
        and audio.peak > 0 and 8000 <= (audio.sample_rate or 0) <= 192000
    )
    result = {
        "system": system, "source": "original Z80 Sega 8-bit diagnostic",
        "real_video_frames": frames,
        "observed_fps": round(frames / duration, 2),
        "nonblank_sampled_frames": nonblank,
        "distinct_rgb_frames": len(fingerprints),
        "psg_pcm_frames": audio.samples,
        "nonzero_audio_samples": audio.nonzero,
        "audio_peak": audio.peak, "sample_rate": audio.sample_rate,
        "physical_speaker_tested": False, "passed": passed, "error": error,
    }
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if passed else 1


def _parent(system, core, report, seconds):
    result = {"system": system, "passed": False, "native_exit_code": None,
              "timed_out": False, "details": None, "error": None}
    try:
        if not core.is_file():
            raise FileNotFoundError("Missing native Genesis Plus GX core")
        with tempfile.TemporaryDirectory(prefix="anything-plays-sega8-") as tmp:
            root = Path(tmp)
            suffix = ".gg" if system == "gamegear" else ".sms"
            rom = root / ("original-sega8" + suffix)
            result["fixture"] = write_sega8_probe(rom, system)
            child_report = root / "child.json"
            command = [
                sys.executable, str(Path(__file__).resolve()), "--child",
                "--system", system, "--core", str(core), "--rom", str(rom),
                "--seconds", str(seconds), "--report", str(child_report),
            ]
            env = os.environ.copy()
            env["HOME"] = str(root)
            env["XDG_CONFIG_HOME"] = str(root / "config")
            try:
                child = subprocess.run(
                    command, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True,
                    timeout=seconds + 25, check=False,
                )
                result["native_exit_code"] = child.returncode
                result["console_tail"] = child.stdout[-12000:]
            except subprocess.TimeoutExpired as exc:
                result["timed_out"] = True
                raw = exc.stdout or b""
                result["console_tail"] = (
                    raw.decode("utf-8", "replace") if isinstance(raw, bytes)
                    else raw
                )[-12000:]
            if child_report.is_file():
                result["details"] = json.loads(child_report.read_text("utf-8"))
            result["passed"] = (
                result["native_exit_code"] == 0
                and isinstance(result["details"], dict)
                and result["details"].get("passed") is True
            )
            preview = child_report.with_name(f"{system}-test-frame.png")
            if preview.is_file():
                report.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(preview, report.with_name(preview.name))
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2) + "\n",
                          encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
    return 0 if result["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--system", required=True, choices=SYSTEMS)
    parser.add_argument("--seconds", type=int, default=8)
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if not 2 <= args.seconds <= 60:
        parser.error("seconds must be 2..60")
    if args.child:
        if args.rom is None:
            parser.error("--child requires --rom")
        return _child(args.system, args.core.resolve(), args.rom.resolve(),
                      args.seconds, args.report.resolve())
    return _parent(args.system, args.core.resolve(), args.report.resolve(),
                   args.seconds)


if __name__ == "__main__":
    raise SystemExit(main())
