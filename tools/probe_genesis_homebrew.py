"""Real Genesis Plus GX video and PSG audio using original cartridge opcodes."""
import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.genesis_homebrew_fixture import write_genesis_probe
from tools.probe_nes_homebrew import ObservedAudio


def _child(core, rom, seconds, report, *, smoke_only=False):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from anything_plays.gba_emulator import Emulator, CoreSession
    from PIL import Image

    emu = Emulator()
    emu.system = "genesis"
    emu.inputs.system = "genesis"
    emu.core_path = str(core)
    session = CoreSession(emu, "genesis", rom, str(core))
    session.audio.close()
    session.audio = ObservedAudio()
    original_video = session.video
    frames, nonblank, fingerprints = 0, 0, set()
    preview = report.with_name("genesis-homebrew-frame.png")

    def observe(pointer, width, height, pitch):
        nonlocal frames, nonblank
        previous = emu.frame_serial
        original_video(pointer, width, height, pitch)
        if emu.frame_serial == previous:
            return
        frames += 1
        if frames > 50 and frames % 11 != 1:
            return
        with emu.lock:
            frame = emu.frame
            if frame is not None and int(frame.max()) > 4 and int(frame.min()) != int(frame.max()):
                nonblank += 1
                fingerprints.add(hashlib.sha256(frame.tobytes()).hexdigest()[:16])
                if nonblank == 1:
                    Image.fromarray(frame).save(preview)
    session.video = observe

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
    elapsed = max(time.monotonic() - started, 0.001)
    audio = session.audio
    # Early cartridge phases deliberately have no VDP output or PSG tone.
    # Smoke means the native core can execute the exact phase without crashing
    # while continuing to invoke frames; full production A/V requires much more.
    passed = (
        error is None and frames >= 10 and frames / elapsed >= 5
        if smoke_only else
        error is None and frames >= 30 and frames / elapsed >= 20
        and nonblank >= 2 and len(fingerprints) >= 2
        and audio.samples > 1000 and audio.nonzero > 100
        and audio.sample_rate is not None and audio.peak > 0
    )
    data = {
        "system": "genesis", "source": "original M68000 homebrew",
        "real_video_frames": frames,
        "observed_fps": round(frames / elapsed, 2),
        "nonblank_samples": nonblank, "distinct_rgb_frames": len(fingerprints),
        "psg_pcm_frames": audio.samples, "nonzero_audio_values": audio.nonzero,
        "audio_peak": audio.peak, "sample_rate": audio.sample_rate,
        "real_speakers_tested": False, "smoke_only": smoke_only,
        "passed": passed, "error": error,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(data, indent=2), flush=True)
    return 0 if passed else 1


def _parent(core, report, seconds, *, debugger=False, phase="full", smoke_only=False):
    result = {"system": "genesis", "passed": False, "timed_out": False,
              "native_exit_code": None, "details": None, "error": None}
    try:
        if not core.is_file():
            raise FileNotFoundError("Missing Genesis Plus GX native core")
        with tempfile.TemporaryDirectory(prefix="anything-plays-genesis-test-") as path:
            folder = Path(path)
            rom = folder / "original-genesis-demo.md"
            result["fixture"] = write_genesis_probe(rom, phase=phase)
            result["smoke_only"] = bool(smoke_only)
            report_child = folder / "child.json"
            env = os.environ.copy()
            env["HOME"] = str(folder)
            env["XDG_CONFIG_HOME"] = str(folder / "config")
            command = [
                sys.executable, str(Path(__file__).resolve()), "--child",
                "--core", str(core), "--rom", str(rom),
                "--seconds", str(seconds), "--report", str(report_child)
            ]
            if smoke_only:
                command.append("--smoke-only")
            if debugger:
                gdb = shutil.which("gdb")
                if gdb is None:
                    raise RuntimeError("GNU debugger required for native Genesis crash diagnosis")
                command = [
                    gdb, "--batch", "--quiet",
                    "-ex", "set pagination off",
                    "-ex", "run",
                    "-ex", "bt 24",
                    "-ex", "info registers pc sp",
                    "--args", *command,
                ]
            try:
                completed = subprocess.run(
                    command, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True, check=False,
                    timeout=seconds + 25, env=env,
                )
                result["native_exit_code"] = completed.returncode
                result["console_tail"] = completed.stdout[-14000:]
                if debugger:
                    # GDB can exit zero even after its debuggee SIGSEGVs.
                    # Never record that process exit as a passing native run.
                    result["native_faulted"] = bool(
                        "received signal SIGSEGV" in completed.stdout
                        or "received signal SIGABRT" in completed.stdout
                    )
                    result["debugger_exit_code"] = completed.returncode
                    # GDB exits nonzero when the later 'bt'/'info registers'
                    # commands run after a CLEAN child exit (no stack exists).
                    # Accept the child-exit evidence, not GDB's postmortem
                    # command status; never accept a signaled native process.
                    clean_child_exit = bool(re.search(
                        r"\[Inferior 1 \(process \d+\) exited normally\]",
                        completed.stdout,
                    ))
                    if clean_child_exit and not result["native_faulted"]:
                        result["native_exit_code"] = 0
                    result["debugger_clean_child_exit"] = clean_child_exit
                    marker = completed.stdout.find("received signal")
                    result["native_fault_trace"] = (
                        completed.stdout[max(0, marker - 15):marker + 9500]
                        if marker >= 0 else completed.stdout[-9500:]
                    )
            except subprocess.TimeoutExpired as exc:
                result["timed_out"] = True
                raw = exc.stdout or b""
                result["console_tail"] = (
                    raw.decode("utf-8", "replace") if isinstance(raw, bytes)
                    else raw
                )[-14000:]
            if report_child.is_file():
                result["details"] = json.loads(report_child.read_text())
            result["passed"] = (
                result["native_exit_code"] == 0
                and not result.get("native_faulted", False)
                and isinstance(result["details"], dict)
                and result["details"].get("passed") is True
            )
            preview = report_child.with_name("genesis-homebrew-frame.png")
            if preview.is_file():
                shutil.copyfile(preview, report.with_name(preview.name))
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2), flush=True)
    return 0 if result["passed"] else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--core", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--rom", type=Path)
    p.add_argument("--seconds", type=int, default=8)
    p.add_argument("--child", action="store_true")
    p.add_argument("--phase", choices=__import__(
        "tools.genesis_homebrew_fixture", fromlist=["PHASES"]
    ).PHASES, default="full")
    p.add_argument("--smoke-only", action="store_true",
                   help="Stage isolation only: allow blank frames and silent PCM")
    p.add_argument("--debugger", action="store_true",
                   help="Capture the native Genesis Plus GX SIGSEGV stack with gdb")
    args = p.parse_args()
    if args.child:
        if args.rom is None:
            p.error("--child requires --rom")
        return _child(args.core.resolve(), args.rom.resolve(), args.seconds,
                      args.report.resolve(), smoke_only=args.smoke_only)
    return _parent(args.core.resolve(), args.report.resolve(), args.seconds,
                   debugger=args.debugger, phase=args.phase,
                   smoke_only=args.smoke_only)


if __name__ == "__main__":
    raise SystemExit(main())
