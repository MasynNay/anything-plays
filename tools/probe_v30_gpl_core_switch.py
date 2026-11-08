"""Research-only sequential switching between GPL SNES and Sega Libretro cores.

Tests original source-generated SNES (SPC), Master System, Game Gear,
SG-1000 and non-TMSS Genesis cartridges using the SAME native CoreSession
frontend in one child OS process, twice for the SNES/SMS cores. This catches
same-process native global state or callback leaks, not just solo emulation.

Never ships native libraries or any BIOS/retail ROM. NEVER establishes
combined-work license permission or authorizes production substitution.
"""
from __future__ import annotations

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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.snes_homebrew_fixture import write_snes_probe
from tools.sega8_homebrew_fixture import write_sega8_probe
from tools.sg1000_homebrew_fixture import write_sg1000_probe
from tools.probe_v30_blastem_genesis_variant import original_without_unconditional_tmss

PLAT_SUFFIX = ".dll" if sys.platform == "win32" else (
    ".dylib" if sys.platform == "darwin" else ".so")
CYCLES = (
    "snes", "mastersystem", "gamegear", "sg1000",
    "genesis", "snes", "mastersystem",
)
STATUS = "UNAPPROVED-TWO-GPL-CORE-REPEAT-SWITCH-RESEARCH"
PINS = {
    "snes": "642d1d1b6684aa7e306a02a89885f3f5456a5157",
    "sega": "2230addc4dd74dd094fd264987fd808abba32d0e",
}
FLAG_KEYS = (
    "same_process_combined_license_review_complete",
    "native_installer_substitution_approved",
    "public_binary_redistribution_approved",
    "physical_speaker_camera_saves_verified",
)

def validate_original_source_artifact(folder, system, target):
    """Verify every original downloaded Actions member and exact native SHA."""
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Original research artifact directory is missing/unsafe")
    checksum = folder / "SHA256SUMS.txt"
    if checksum.is_symlink() or not checksum.is_file():
        raise ValueError("Original source artifact checksum file missing")
    names = {}
    for raw in checksum.read_text("ascii").splitlines():
        digest, sep, name = raw.partition("  ")
        if sep != "  " or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Malformed original research SHA256SUMS")
        if not name or "/" in name or "\\" in name or name in names:
            raise ValueError("Unsafe source artifact member")
        names[name] = digest
    # The original preserved research checksums were captured BEFORE the
    # native A/V probes. Those workflows then appended a known, finite set
    # of test reports and original homebrew frame screenshots. Do not demand
    # that original reports be retroactively in their older checksum file;
    # neither read nor execute unchecksummed diagnostics as binary inputs.
    allowed_diagnostics = (
        {"SUPAFAUST_NATIVE_AV_UNAPPROVED.json", "snes-original-frame.png"}
        if system == "snes" else {
            "GENESIS_AV_UNAPPROVED.json", "ISOLATED_SEGA_PROCESS_UNAPPROVED.json",
            "mastersystem-AV_UNAPPROVED.json", "gamegear-AV_UNAPPROVED.json",
            "sg1000-AV_UNAPPROVED.json",
            "mastersystem-test-frame.png", "gamegear-test-frame.png",
            "sg1000-test-frame.png",
        }
    )
    members = list(folder.iterdir())
    if any(p.is_symlink() or not p.is_file() for p in members):
        raise ValueError("Original source artifact contains unsafe entries")
    files = {p.name for p in members}
    required = set(names) | {"SHA256SUMS.txt"}
    if len(names) < 4 or not required.issubset(files) or files - required - allowed_diagnostics:
        raise ValueError("Original source artifact has missing or unexpected entries")
    for name, expected in names.items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Original artifact checksum mismatch: {name}")
    manifest_name = ("SUPAFAUST_SOURCE_BUILD_UNAPPROVED.json"
                     if system == "snes" else "PINNED_GPL_ALTERNATIVE_SOURCE_BUILD_UNAPPROVED.json")
    row = json.loads((folder / manifest_name).read_text("utf-8"))
    if row.get("target") != target or row.get("source_commit") != PINS[system]:
        raise ValueError("Original pinned source commit or OS target changed")
    native_name = row.get("native_name" if system == "snes" else "native_filename")
    if not isinstance(native_name, str) or not native_name.endswith(PLAT_SUFFIX):
        raise ValueError("Original source-built native filename has incorrect platform suffix")
    native = folder / native_name
    if native.name not in names or row.get("native_sha256") != names[native.name]:
        raise ValueError("Original compiled native image has wrong reported SHA")
    if system == "snes":
        if (row.get("compiled_from_exact_upstream_checkout") is not True
                or row.get("replaces_current_snes9x_in_app") is not False
                or row.get("public_binary_redistribution_approved") is not False):
            raise ValueError("SNES candidate is not the unapproved original")
    else:
        if (row.get("candidate") != "blastem"
                or row.get("compiled_from_exact_pinned_source_checkout") is not True
                or row.get("matches_current_3_0_shipped_libretro_library") is not False
                or row.get("public_binary_distribution_approved") is not False):
            raise ValueError("Sega candidate is not the unapproved original")
    return native.resolve(), names[native.name]

def _write_roms(root):
    roms = {}
    roms["snes"] = root / "source-authored-snes.sfc"
    write_snes_probe(roms["snes"])
    for system in ("mastersystem", "gamegear"):
        roms[system] = root / ("source-authored-" + system +
                               (".gg" if system == "gamegear" else ".sms"))
        write_sega8_probe(roms[system], system)
    roms["sg1000"] = root / "source-authored-sg1000.sg"
    write_sg1000_probe(roms["sg1000"])
    roms["genesis"] = root / "source-authored-non-tmss-genesis.md"
    _, patched = original_without_unconditional_tmss()
    roms["genesis"].write_bytes(patched)
    return roms

def _play_one(system, rom, core, seconds):
    from anything_plays.gba_emulator import Emulator, CoreSession
    from tools.probe_nes_homebrew import ObservedAudio
    emu = Emulator()
    emu.system = system
    emu.inputs.system = system
    emu.core_path = str(core)
    session = CoreSession(emu, system, rom, str(core))
    session.audio.close()
    session.audio = ObservedAudio()
    original_video = session.video
    counts = {"frames": 0, "nonblank": 0}
    fingerprints = set()
    def capture(data, width, height, pitch):
        before = emu.frame_serial
        original_video(data, width, height, pitch)
        if emu.frame_serial == before:
            return
        counts["frames"] += 1
        if counts["frames"] > 45 and counts["frames"] % 11 != 1:
            return
        with emu.lock:
            frame = emu.frame
            if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
                return
            high, low = int(frame.max()), int(frame.min())
            if high <= 8 or high == low:
                return
            counts["nonblank"] += 1
            fingerprints.add(hashlib.sha256(frame.tobytes()).hexdigest()[:16])
    session.video = capture
    timer = threading.Timer(seconds, emu.stop_event.set)
    timer.daemon = True
    timer.start()
    error = None
    start = time.monotonic()
    try:
        session.run()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        emu.stop_event.set()
        timer.cancel()
    elapsed = max(0.001, time.monotonic() - start)
    audio = session.audio
    result = {
        "system": system, "source_rom_sha256": hashlib.sha256(Path(rom).read_bytes()).hexdigest(),
        "frames": counts["frames"], "nonblank_sampled": counts["nonblank"],
        "distinct_rgb_frames": len(fingerprints),
        "core_pcm_frames": audio.samples,
        "core_nonzero_pcm_values": audio.nonzero,
        "reported_sample_rate": audio.sample_rate,
        "error": error, "elapsed_seconds": round(elapsed, 2),
        "passed": (error is None and counts["frames"] >= 45
                   and counts["nonblank"] >= 3 and len(fingerprints) >= 2
                   and counts["frames"] / elapsed >= 20
                   and audio.samples > 1000 and audio.nonzero > 100),
    }
    session = None
    emu = None
    return result

def _child(snes, sega, report, seconds):
    import faulthandler
    faulthandler.enable(all_threads=True)
    with tempfile.TemporaryDirectory(prefix="ap-v30-gpl-switch-homebrew-") as tmp:
        roms = _write_roms(Path(tmp))
        result = []
        for system in CYCLES:
            core = snes if system == "snes" else sega
            result.append(_play_one(system, roms[system], core, seconds))
            if not result[-1]["passed"]:
                break
    output = {
        "status": STATUS,
        "cycles_expected": len(CYCLES), "cycles_completed": len(result),
        "same_python_process_for_all_cycles": True,
        "source_generated_roms_only": True,
        "cycles": result, "all_cycles_passed": len(result) == len(CYCLES)
                                             and all(x["passed"] for x in result),
        **{k: False for k in FLAG_KEYS},
    }
    report.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", "utf-8")
    print(json.dumps(output, indent=2, sort_keys=True), flush=True)
    return 0 if output["all_cycles_passed"] else 1

def probe(snes_dir, sega_dir, target, seconds, report):
    import re
    targets = ("windows-x64", "linux-x64", "macos-arm64", "macos-x64")
    if target not in targets:
        raise ValueError("Unexpected native target")
    if not 3 <= seconds <= 12:
        raise ValueError("Each actual native cycle must last 3..12 seconds")
    snes, snes_sha = validate_original_source_artifact(snes_dir, "snes", target)
    sega, sega_sha = validate_original_source_artifact(sega_dir, "sega", target)
    if report.exists() or report.is_symlink():
        raise ValueError("Research evidence destination must be new")
    report.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ap-v30-gpl-switch-parent-") as tmp:
        child = Path(tmp) / "child.json"
        env = os.environ.copy()
        env["HOME"] = tmp
        env["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
        cmd = [sys.executable, str(Path(__file__).resolve()), "--child",
               "--snes-core", str(snes), "--sega-core", str(sega),
               "--seconds", str(seconds), "--report", str(child)]
        timed_out = False
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, env=env,
                                  timeout=len(CYCLES) * seconds + 65, check=False)
            code, tail = proc.returncode, (proc.stdout + proc.stderr)[-8000:]
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            code = None
            raw = exc.stdout or b""
            tail = raw.decode("utf-8", "replace")[-8000:] if isinstance(raw, bytes) else raw[-8000:]
        child_result = json.loads(child.read_text("utf-8")) if child.is_file() else None
        passed = (not timed_out and code == 0 and isinstance(child_result, dict)
                  and child_result.get("all_cycles_passed") is True
                  and child_result.get("cycles_completed") == len(CYCLES)
                  and all(child_result.get(k) is False for k in FLAG_KEYS))
        summary = {
            "status": STATUS, "target": target,
            "snes_upstream_commit": PINS["snes"], "sega_upstream_commit": PINS["sega"],
            "snes_original_native_sha256": snes_sha, "sega_original_native_sha256": sega_sha,
            "original_native_source_hashes_checked": True,
            "child_exit_code": code, "timed_out": timed_out, "passed": passed,
            "details": child_result, "console_tail": tail,
            **{k: False for k in FLAG_KEYS},
        }
    report.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", "utf-8")
    return summary

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snes-dir", type=Path)
    parser.add_argument("--sega-dir", type=Path)
    parser.add_argument("--target", choices=("windows-x64", "linux-x64", "macos-arm64", "macos-x64"))
    parser.add_argument("--snes-core", type=Path)
    parser.add_argument("--sega-core", type=Path)
    parser.add_argument("--seconds", type=int, default=5)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args(argv)
    if args.child:
        if not args.snes_core or not args.sega_core:
            parser.error("Child requires both real original cores")
        return _child(args.snes_core, args.sega_core, args.report, args.seconds)
    if not args.snes_dir or not args.sega_dir or not args.target:
        parser.error("Research parent requires original SNES/Sega artifact folders and OS target")
    try:
        row = probe(args.snes_dir, args.sega_dir, args.target, args.seconds, args.report)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(1, f"GPL ALTERNATIVE REPEATED SWITCH RESEARCH BLOCKED: {exc}\n")
    print(json.dumps({k: row[k] for k in ("target","passed","child_exit_code","timed_out","status")}, indent=2))
    return 0 if row["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
