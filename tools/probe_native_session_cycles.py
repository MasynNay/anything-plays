"""Repeat native Libretro start/stop/switch on source-created legal ROMs.

This exercises the REAL production Emulator worker, core initialize/deinit,
manual/camera pulses, frame queue and audio teardown. All ten console
profiles below must repeatedly boot in ONE process. Crash containment is via
a parent subprocess; no ROM assets are shipped to application users.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


# System, Libretro core, extension. Every fixture is authored in this repo.
CASES = (
    ("gb", "mgba", ".gb"),
    ("gbc", "mgba", ".gbc"),
    ("gba", "mgba", ".gba"),
    ("snes", "snes9x", ".sfc"),
    ("nes", "fceumm", ".nes"),
    ("genesis", "genesis_plus_gx", ".md"),
    ("mastersystem", "genesis_plus_gx", ".sms"),
    ("gamegear", "genesis_plus_gx", ".gg"),
    ("sg1000", "genesis_plus_gx", ".sg"),
    ("atari2600", "stella2014", ".a26"),
    ("atari7800", "prosystem", ".a78"),
)
CORES = tuple(dict.fromkeys(core for _, core, _ in CASES))


def write_original_fixtures(folder):
    from tools.gb_homebrew_fixture import write_gb_probe
    from tools.gba_homebrew_fixture import write_gba_probe
    from tools.snes_homebrew_fixture import write_snes_probe
    from tools.nes_homebrew_fixture import write_nes_probe
    from tools.genesis_homebrew_fixture import write_genesis_probe
    from tools.sega8_homebrew_fixture import write_sega8_probe
    from tools.sg1000_homebrew_fixture import write_sg1000_probe
    from tools.atari_homebrew_fixture import write_atari_probe
    from tools.atari7800_homebrew_fixture import write_atari7800_probe
    files = {}
    for system, _, extension in CASES:
        rom = folder / ("original-" + system + extension)
        if system in ("gb", "gbc"):
            write_gb_probe(rom, system)
        elif system == "gba":
            write_gba_probe(rom)
        elif system == "snes":
            write_snes_probe(rom)
        elif system == "nes":
            write_nes_probe(rom)
        elif system == "genesis":
            write_genesis_probe(rom)
        elif system in ("mastersystem", "gamegear"):
            write_sega8_probe(rom, system)
        elif system == "sg1000":
            write_sg1000_probe(rom)
        elif system == "atari2600":
            write_atari_probe(rom)
        elif system == "atari7800":
            write_atari7800_probe(rom)
        files[system] = rom
    return files


def process_rss_mb():
    if sys.platform.startswith("linux"):
        try:
            pages = int(Path("/proc/self/statm").read_text("ascii").split()[1])
            return pages * os.sysconf("SC_PAGE_SIZE") / (1024 * 1024)
        except (OSError, ValueError, IndexError):
            return None
    return None


def _child(cores, originals, cycles, max_growth_mb, report):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from anything_plays.gba_emulator import Emulator

    emu = Emulator()
    initial_threads = threading.active_count()
    peak_threads = initial_threads
    sessions = 0
    samples = []
    errors = []
    started = time.monotonic()
    for round_number in range(cycles):
        if errors:
            break
        for system, core, _ in CASES:
            rom = originals[system]
            emu.system = system
            emu.inputs.system = system
            emu.core_path = str(cores[core])
            try:
                emu.start(rom)
                deadline = time.monotonic() + 4.0
                displayed = False
                while time.monotonic() < deadline:
                    if emu.error:
                        break
                    with emu.lock:
                        displayed = emu.frame is not None
                    if displayed and emu.running:
                        break
                    time.sleep(0.02)
                if not displayed or not emu.running or emu.error:
                    raise RuntimeError(
                        f"Emulator failed during original {system} ROM startup: "
                        f"{emu.error or 'no decoded game frame'}"
                    )
                emu.armed = True
                emu.press("B", frames=4)
                emu.set_manual("A", True)
                time.sleep(0.06)
                emu.set_manual("A", False)
            except Exception as exc:
                errors.append(
                    f"{system} round {round_number + 1}: "
                    f"{type(exc).__name__}: {exc}"
                )
            finally:
                emu.stop()
            if (emu.thread is not None or emu.running
                    or not emu.stop_event.is_set()
                    or emu.manual_buttons
                    or emu.inputs.remaining):
                errors.append(
                    f"{system} round {round_number + 1}: native worker "
                    "or controller state remained after Stop"
                )
            peak_threads = max(peak_threads, threading.active_count())
            if threading.active_count() > initial_threads + 2:
                errors.append(
                    f"{system} round {round_number + 1}: Python worker thread leak"
                )
            sessions += 1
            if errors:
                break
        resident = process_rss_mb()
        samples.append(resident)
        print(
            f"Cycle {round_number + 1}/{cycles}: "
            f"{sessions} original native game starts, "
            f"resident {resident} MiB", flush=True,
        )
    # Allow one full cycle for library/module/audio initialization
    # before measuring any sustained growth.
    stable = [x for x in samples[1:] if x is not None]
    growth = max(0.0, max(stable) - stable[0]) if stable else None
    if growth is None or growth > max_growth_mb:
        errors.append(
            f"Native RSS after warm-up grew {growth} MiB "
            f"(limit {max_growth_mb})"
        )
    passed = sessions == cycles * len(CASES) and not errors
    evidence = {
        "kind": "production native Libretro multi-core lifecycle endurance",
        "native_core_switches": sessions,
        "requested_switches": cycles * len(CASES),
        "systems": [case[0] for case in CASES],
        "core_libraries": list(CORES),
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "rss_per_full_cycle_mb": samples,
        "rss_growth_after_first_cycle_mb": growth,
        "memory_growth_limit_mb": max_growth_mb,
        "python_threads_baseline": initial_threads,
        "python_threads_peak": peak_threads,
        "emulator_worker_stopped_cleanly": emu.thread is None,
        "original_legal_homebrew_only": True,
        "physical_camera_and_speakers_tested": False,
        "passed": passed, "errors": errors,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: evidence[k] for k in (
        "passed", "native_core_switches", "rss_growth_after_first_cycle_mb",
        "errors",
    )}, indent=2), flush=True)
    return 0 if passed else 1


def _parent(core_dir, report, cycles, max_growth_mb):
    result = {
        "passed": False, "native_exit_code": None,
        "timed_out": False, "error": None, "details": None,
    }
    try:
        cores = {core: core_dir / (core + "_libretro.so") for core in CORES}
        missing = [str(x) for x in cores.values() if not x.is_file()]
        if missing:
            raise FileNotFoundError("Missing native cores: " + ", ".join(missing))
        with tempfile.TemporaryDirectory(prefix="ap-v30-native-cycle-") as d:
            root = Path(d)
            originals = write_original_fixtures(root)
            child_report = root / "worker.json"
            args = [
                sys.executable, str(Path(__file__).resolve()), "--child",
                "--core-dir", str(core_dir),
                "--cycles", str(cycles),
                "--max-growth-mb", str(max_growth_mb),
                "--report", str(child_report),
                "--rom-folder", str(root),
            ]
            environment = os.environ.copy()
            environment["HOME"] = str(root)
            environment["XDG_CONFIG_HOME"] = str(root / "config")
            try:
                completed = subprocess.run(
                    args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, env=environment, check=False,
                    timeout=max(180, cycles * len(CASES) * 5),
                )
                result["native_exit_code"] = completed.returncode
                result["console_tail"] = completed.stdout[-16000:]
            except subprocess.TimeoutExpired as exc:
                result["timed_out"] = True
                raw = exc.stdout or b""
                result["console_tail"] = (
                    raw.decode("utf-8", "replace")
                    if isinstance(raw, bytes) else raw
                )[-16000:]
            if child_report.is_file():
                result["details"] = json.loads(child_report.read_text("utf-8"))
            result["passed"] = (
                result["native_exit_code"] == 0
                and isinstance(result["details"], dict)
                and result["details"].get("passed") is True
            )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
    return 0 if result["passed"] else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--core-dir", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--cycles", type=int, default=12)
    p.add_argument("--max-growth-mb", type=float, default=128.0)
    p.add_argument("--rom-folder", type=Path)
    p.add_argument("--child", action="store_true")
    args = p.parse_args()
    if not 3 <= args.cycles <= 100:
        p.error("Expected 3..100 full console-switch cycles")
    if not 0 <= args.max_growth_mb <= 4096:
        p.error("Expected memory budget 0..4096 MiB")
    if args.child:
        if args.rom_folder is None:
            p.error("Child requires --rom-folder")
        cores = {c: args.core_dir.resolve() /
                 (c + "_libretro.so") for c in CORES}
        originals = {system: args.rom_folder.resolve() /
                     ("original-" + system + suffix)
                     for system, _, suffix in CASES}
        return _child(cores, originals, args.cycles, args.max_growth_mb,
                      args.report.resolve())
    return _parent(args.core_dir.resolve(), args.report.resolve(),
                   args.cycles, args.max_growth_mb)


if __name__ == "__main__":
    raise SystemExit(main())
