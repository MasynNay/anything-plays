"""Run original Atari 2600 cart through Stella 2014 embedded Libretro.

Isolated child prevents native emulator crashes from taking down CI.
Check changing RGB frames and actual nonzero PCM audio callbacks.
"""
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
from tools.atari_homebrew_fixture import write_atari_probe
from tools.probe_nes_homebrew import ObservedAudio

MIN_FPS = 20.0


def _child(core, rom, seconds, report):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from anything_plays.gba_emulator import Emulator, CoreSession
    from PIL import Image
    emu = Emulator()
    emu.system = "atari2600"
    emu.inputs.system = "atari2600"
    emu.core_path = str(core)
    session = CoreSession(emu, "atari2600", rom, str(core))
    session.audio.close()
    session.audio = ObservedAudio()
    original = session.video
    frames = 0
    nonblank = 0
    distinct = set()
    snapshot = report.with_name("atari-test-frame.png")

    def video(data, width, height, pitch):
        nonlocal frames, nonblank
        old = emu.frame_serial
        original(data, width, height, pitch)
        if emu.frame_serial == old:
            return
        frames += 1
        if frames > 48 and frames % 11 != 1:
            return
        with emu.lock:
            frame = emu.frame
            if frame is None:
                return
            if int(frame.max()) > 4 and int(frame.min()) != int(frame.max()):
                nonblank += 1
                distinct.add(hashlib.sha256(frame.tobytes()).hexdigest()[:16])
                if nonblank == 1:
                    Image.fromarray(frame).save(snapshot)
    session.video = video
    stop = threading.Timer(seconds, emu.stop_event.set)
    stop.daemon = True
    stop.start()
    start = time.monotonic()
    error = None
    try:
        session.run()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        emu.stop_event.set()
        stop.cancel()
    duration = max(time.monotonic() - start, .001)
    fps = round(frames / duration, 2)
    audio = session.audio
    passed = (
        error is None and frames >= 30 and fps >= MIN_FPS
        and nonblank >= 2 and len(distinct) >= 2
        and audio.nonzero >= 100 and audio.peak > 0
    )
    result = {
        "system": "atari2600", "source": "project-original cartridge",
        "fps": fps, "video_frames": frames,
        "nonblank_frames_sampled": nonblank,
        "unique_frame_hashes": len(distinct),
        "pcm_frame_samples": audio.samples,
        "pcm_nonzero_samples": audio.nonzero,
        "pcm_sample_peak": audio.peak,
        "audio_sample_rate": audio.sample_rate,
        "physical_speakers_tested": False,
        "seconds_elapsed": round(duration, 2),
        "passed": passed, "error": error,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if passed else 1


def _parent(core, report, seconds):
    data = {"system": "atari2600", "passed": False, "timed_out": False,
            "native_exit_code": None, "details": None, "error": None}
    try:
        if not core.is_file():
            raise FileNotFoundError("Stella 2014 core missing")
        with tempfile.TemporaryDirectory(prefix="anything-plays-atari-ci-") as tmp:
            folder = Path(tmp)
            rom = folder / "original-tia-colors-and-audio.a26"
            data["fixture"] = write_atari_probe(rom)
            child = folder / "child.json"
            env = os.environ.copy()
            env["HOME"] = str(folder)
            env["XDG_CONFIG_HOME"] = str(folder / "config")
            command = [
                sys.executable, str(Path(__file__).resolve()), "--child",
                "--core", str(core), "--rom", str(rom),
                "--seconds", str(seconds), "--report", str(child),
            ]
            try:
                process = subprocess.run(
                    command, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True, check=False,
                    timeout=seconds + 25,
                )
                data["native_exit_code"] = process.returncode
                data["console_tail"] = process.stdout[-14000:]
            except subprocess.TimeoutExpired as exc:
                data["timed_out"] = True
                output = exc.stdout or b""
                data["console_tail"] = (output.decode("utf-8", "replace")
                                        if isinstance(output, bytes) else output)[-14000:]
            if child.is_file():
                data["details"] = json.loads(child.read_text("utf-8"))
            data["passed"] = (
                data["native_exit_code"] == 0
                and isinstance(data["details"], dict)
                and data["details"].get("passed") is True
            )
            image = child.with_name("atari-test-frame.png")
            if image.is_file():
                import shutil
                shutil.copyfile(image, report.with_name(image.name))
    except Exception as exc:
        data["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(data, indent=2) + "\n")
        print(json.dumps(data, indent=2), flush=True)
    return 0 if data["passed"] else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--core", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--rom", type=Path)
    p.add_argument("--seconds", type=int, default=8)
    p.add_argument("--child", action="store_true")
    args = p.parse_args()
    if not 2 <= args.seconds <= 60:
        p.error("seconds must be 2..60")
    if args.child:
        if args.rom is None:
            p.error("--child requires --rom")
        return _child(args.core.resolve(), args.rom.resolve(),
                      args.seconds, args.report.resolve())
    return _parent(args.core.resolve(), args.report.resolve(), args.seconds)


if __name__ == "__main__":
    raise SystemExit(main())
