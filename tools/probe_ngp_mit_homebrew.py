"""Strict Neo Geo Pocket / Color native video and audio acceptance, CI-only.

MIT-licensed game/test authors retain rights. The app doesn't distribute or
download these ROMs. One isolated native CoreSession is required to produce
changing nonblank game frames, real PCM and no crash. No emulator API may
synthesize frames or audio to satisfy the gate.
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
from tools.ngp_mit_fixtures import FIXTURES, fetch_test_fixture
from tools.probe_nes_homebrew import ObservedAudio


def _child(system, core, rom, seconds, report):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from PIL import Image
    from anything_plays.gba_emulator import Emulator, CoreSession
    emulator = Emulator()
    emulator.system = emulator.inputs.system = system
    emulator.core_path = str(core)
    session = CoreSession(emulator, system, rom, str(core))
    session.audio.close()
    session.audio = ObservedAudio()

    original_video = session.video
    callbacks = nonblank = 0
    hashes = set()
    all_hashes = set()
    rgb_bounds = [255, 0]
    first_shape = None
    def observe_video(pointer, width, height, pitch):
        nonlocal callbacks, nonblank, first_shape
        before = emulator.frame_serial
        original_video(pointer, width, height, pitch)
        if emulator.frame_serial == before:
            return
        callbacks += 1
        if callbacks > 90 and callbacks % 11 != 1:
            return
        with emulator.lock:
            frame = emulator.frame
            if frame is None:
                return
            low, high = int(frame.min()), int(frame.max())
            rgb_bounds[0] = min(low, rgb_bounds[0])
            rgb_bounds[1] = max(high, rgb_bounds[1])
            digest = hashlib.sha256(frame.tobytes()).hexdigest()[:16]
            all_hashes.add(digest)
            if first_shape is None:
                first_shape = list(frame.shape)
                Image.fromarray(frame).save(
                    report.with_name(system + "-first-frame.png")
                )
            if high > 8 and low != high:
                nonblank += 1
                hashes.add(digest)
    session.video = observe_video
    timer = threading.Timer(seconds, emulator.stop_event.set)
    timer.daemon = True
    timer.start()
    start = time.monotonic()
    exception = None
    try:
        session.run()
    except Exception as exc:
        exception = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        emulator.stop_event.set()
        timer.cancel()
    elapsed = max(0.001, time.monotonic() - start)
    pcm = session.audio
    video_ok = (
        callbacks >= 30 and callbacks / elapsed >= 20
        and nonblank >= 3 and len(hashes) >= 2
    )
    audio_ok = (
        pcm.samples > 1000 and pcm.nonzero > 100 and pcm.peak > 0
        and 8000 <= (pcm.sample_rate or 0) <= 192000
    )
    passed = exception is None and video_ok and audio_ok
    evidence = {
        "system": system,
        "source": "pinned MIT homebrew, no proprietary game",
        "native_video_frames": callbacks,
        "observed_fps": round(callbacks / elapsed, 2),
        "sampled_nonblank_frames": nonblank,
        "distinct_nonblank_frames": len(hashes),
        "distinct_all_frames": len(all_hashes),
        "frame_shape": first_shape,
        "rgb_min_max": rgb_bounds,
        "native_audio_frames": pcm.samples,
        "native_nonzero_pcm_values": pcm.nonzero,
        "native_audio_peak": pcm.peak,
        "sample_rate": pcm.sample_rate,
        "video_gate_passed": video_ok,
        "audio_gate_passed": audio_ok,
        "physical_speakers_verified": False,
        "real_user_game_compatibility_verified": False,
        "passed": passed, "error": exception,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(evidence, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2), flush=True)
    return 0 if passed else 1


def _parent(system, core, report, seconds):
    outcome = {
        "system": system, "passed": False, "native_exit_code": None,
        "timed_out": False, "fixture": None, "details": None, "error": None,
    }
    try:
        if not core.is_file():
            raise FileNotFoundError("Missing embedded Mednafen NeoPop core")
        with tempfile.TemporaryDirectory(prefix="ap-v30-ngp-ci-") as tmp:
            root = Path(tmp)
            rom = root / ("pinned-mit-test" + FIXTURES[system]["ext"])
            outcome["fixture"] = fetch_test_fixture(system, rom)
            child_report = root / "child-result.json"
            env = os.environ.copy()
            env["HOME"] = str(root)
            env["XDG_CONFIG_HOME"] = str(root / "config")
            command = [
                sys.executable, str(Path(__file__).resolve()), "--child",
                "--system", system, "--core", str(core), "--rom", str(rom),
                "--seconds", str(seconds), "--report", str(child_report),
            ]
            try:
                worker = subprocess.run(
                    command, capture_output=True, text=True, check=False,
                    timeout=seconds + 30, env=env,
                )
                outcome["native_exit_code"] = worker.returncode
                outcome["console_tail"] = (worker.stdout + worker.stderr)[-14000:]
            except subprocess.TimeoutExpired as exc:
                outcome["timed_out"] = True
                raw = exc.stdout or b""
                outcome["console_tail"] = (
                    raw.decode("utf-8", "replace") if isinstance(raw, bytes)
                    else raw
                )[-14000:]
            if child_report.is_file():
                outcome["details"] = json.loads(
                    child_report.read_text(encoding="utf-8")
                )
            frame = child_report.with_name(system + "-first-frame.png")
            if frame.is_file():
                report.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(frame, report.with_name(frame.name))
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", choices=tuple(FIXTURES), required=True)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--seconds", type=int, default=12)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if not 2 <= args.seconds <= 60:
        parser.error("--seconds must be 2..60")
    if args.child:
        if args.rom is None:
            parser.error("--child requires --rom")
        return _child(
            args.system, args.core.resolve(), args.rom.resolve(),
            args.seconds, args.report.resolve(),
        )
    return _parent(
        args.system, args.core.resolve(), args.report.resolve(), args.seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
