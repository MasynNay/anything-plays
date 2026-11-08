"""Opt-in, actual native Sega 8-bit child-process playback feasibility check.

This is NOT the application default, a legal-compliance decision, an audio
speaker test, or proof that commercial games work. The original Z80 homebrew
runs against a separately source-built experimental Libretro core inside the
existing bounded shared-memory process bridge, twice in one parent process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from anything_plays.libretro_input import InputBuffer
from anything_plays.n64_process import ExperimentalSoftwareCoreProcessSession
from tools.sega8_homebrew_fixture import write_sega8_probe

STATUS = "UNAPPROVED-ISOLATED-SEGA-SOFTWARE-CORE-RESEARCH"
EXT = {"win32": ".dll", "darwin": ".dylib"}
SYSTEM = "mastersystem"


class ProbeEmulator:
    """Only the publicly used process-bridge facade, with no Tk UI."""

    def __init__(self):
        self.inputs = InputBuffer()
        self.inputs.system = SYSTEM
        self.system = SYSTEM
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.armed = True
        self.running = False
        self.launching = True
        self.volume = 0.0  # Keep CI's real speaker outputs muted.
        self.audio_warning = None
        self.save_warning = None
        self.last_error = None
        self.frame = None
        self.frame_serial = 0


def one_playback(core: Path, rom: Path, seconds: int) -> dict:
    emu = ProbeEmulator()
    session = ExperimentalSoftwareCoreProcessSession(emu, SYSTEM, rom, core)
    errors = []
    def work():
        try:
            session.run()
        except BaseException as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    thread = threading.Thread(target=work, name="v30-2d-process-lab", daemon=True)
    thread.start()
    deadline = time.monotonic() + seconds
    seen_serial = -1
    captured = 0
    colored = 0
    hashes = set()
    started = False
    try:
        while time.monotonic() < deadline and thread.is_alive():
            if emu.running:
                started = True
            with emu.lock:
                serial = emu.frame_serial
                frame = emu.frame.copy() if emu.frame is not None and serial != seen_serial else None
            if frame is not None:
                seen_serial = serial
                captured += 1
                if frame.ndim == 3 and frame.shape[2] == 3 and frame.size:
                    if int(frame.max()) > 8 and int(frame.max()) != int(frame.min()):
                        colored += 1
                        hashes.add(hashlib.sha256(frame.tobytes()).hexdigest()[:16])
            # Exercise the same manual button-to-2-port control snapshot path.
            # This is NOT proof that a retail game reacts to every button.
            emu.inputs.set_manual("Start", (captured // 7) % 2 == 0)
            time.sleep(0.025)
    finally:
        emu.stop_event.set()
        thread.join(timeout=15)
        emu.inputs.release_manual()

    return {
        "worker_terminated": not thread.is_alive(),
        "gameplay_started": started,
        "captured_rgb_frames": captured,
        "nonblank_rgb_frames": colored,
        "distinct_rgb_frames": len(hashes),
        "worker_errors": errors[:2],
        "passed": (not thread.is_alive() and started and not errors
                   and captured >= 12 and colored >= 8 and len(hashes) >= 2),
        "physical_audio_verified": False,
        "retail_controller_compatibility_verified": False,
    }


def probe(core: Path, seconds: int = 6) -> dict:
    expected = EXT.get(sys.platform, ".so")
    core = Path(core)
    if core.is_symlink() or not core.is_file() or core.suffix.lower() != expected:
        raise ValueError(f"Expected a regular host-native experimental core ({expected})")
    if not 5 <= seconds <= 15:
        raise ValueError("Each original playback must last 5 to 15 seconds")
    with tempfile.TemporaryDirectory(prefix="anything-plays-isolated-sega-") as tmp:
        rom = Path(tmp) / "original-process-test.sms"
        write_sega8_probe(rom, SYSTEM)
        cycles = [one_playback(core.resolve(), rom, seconds) for _ in range(2)]
    return {
        "schema_version": 1,
        "status": STATUS,
        "tested_system": SYSTEM,
        "real_libretro_core_sha256": hashlib.sha256(core.read_bytes()).hexdigest(),
        "process_cycles": 2,
        "cycles": cycles,
        "passed": all(c["passed"] for c in cycles),
        "uses_original_source_generated_homebrew": True,
        "core_isolated_in_fresh_process_per_cycle": True,
        "rom_downloaded": False,
        "physical_camera_controls_verified": False,
        "physical_speaker_audio_verified": False,
        "save_reload_verified": False,
        "legal_separation_or_aggregation_approved": False,
        "combined_license_review_complete": False,
        "public_binary_distribution_approved": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=6)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.report.is_symlink() or args.report.exists():
        parser.error("Report output must be a new regular path, not a symlink")
    try:
        result = probe(args.core, args.seconds)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_bytes((json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Isolated research failed: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
