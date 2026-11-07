"""N64: three REAL start/unload/restart cycles in one app process.

Uses the exact production Emulator facade and a pinned public-domain N64
homebrew ROM, never commercial games. Outer process quarantines a native
segfault/hang and preserves a JSON report; no passing if only the first
cycle works. Each iteration demands real nonblank video, not just dlopen.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.n64_homebrew_fixture import verified_homebrew


def repeated_launches(rom, core, report):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from anything_plays.gba_emulator import Emulator
    from anything_plays.core_locator import find_core
    emu = Emulator()
    emu.system = "n64"
    emu.inputs.system = "n64"
    emu.core_path = str(core)
    results = []
    for idx in range(3):
        cycle = {"index": idx + 1, "started": False,
                 "nonblank_video": False, "worker_stopped": False}
        try:
            emu.start(str(rom))
            deadline = time.monotonic() + 13.0
            while time.monotonic() < deadline:
                if emu.error or emu.last_error:
                    break
                if emu.running and emu.frame_serial > 1:
                    with emu.lock:
                        frame = emu.frame
                        cycle["frame_serial"] = emu.frame_serial
                        if frame is not None and frame.size:
                            cycle["nonblank_video"] = bool(
                                int(frame.max()) > 4
                                and int(frame.max()) != int(frame.min())
                            )
                    if cycle["nonblank_video"]:
                        cycle["started"] = True
                        break
                time.sleep(.075)
            cycle["error_before_stop"] = emu.error or emu.last_error
            cycle["launching"] = emu.launching
        except Exception as exc:
            cycle["exception"] = f"{type(exc).__name__}: {exc}"
            traceback.print_exc()
        finally:
            emu.stop()
            cycle["worker_stopped"] = emu.thread is None or not emu.thread.is_alive()
            cycle["error_after_stop"] = emu.error or emu.last_error
            cycle["passed"] = (
                cycle["started"] and cycle["nonblank_video"]
                and cycle["worker_stopped"] and not cycle["error_after_stop"]
            )
            results.append(cycle)
            print("N64-NATIVE-RESTART", json.dumps(cycle), flush=True)
        if not cycle["passed"]:
            break
    outcome = {"system": "n64", "cycles_expected": 3,
               "cycles_completed": len(results), "cycles": results,
               "real_native_core_used": True,
               "passed": len(results) == 3 and all(x["passed"] for x in results),
               "physical_mac_tested": False}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(outcome, indent=2), flush=True)
    return 0 if outcome["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--rom", type=Path)
    args = parser.parse_args()
    core = args.core.resolve()
    report = args.report.resolve()
    if args.child:
        if not args.rom:
            parser.error("--rom required for child")
        return repeated_launches(args.rom.resolve(), core, report)
    result = {"passed": False, "core": str(core)}
    try:
        with tempfile.TemporaryDirectory(prefix="anything-plays-n64-cycles-") as tmp:
            home = Path(tmp)
            rom = home / "verified-public-domain.z64"
            result["fixture"] = verified_homebrew(rom)
            evidence = home / "child-results.json"
            env = os.environ.copy()
            env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / "config"))
            cmd = [sys.executable, "-X", "faulthandler", str(Path(__file__).resolve()),
                   "--child", "--core", str(core), "--rom", str(rom),
                   "--report", str(evidence)]
            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True,
                                      env=env, check=False, timeout=62)
                result["returncode"] = proc.returncode
                result["console_tail"] = proc.stdout[-12000:]
            except subprocess.TimeoutExpired as exc:
                result["timed_out"] = True
                raw = exc.stdout or b""
                result["console_tail"] = (raw.decode("utf-8", "replace")
                    if isinstance(raw, bytes) else raw)[-12000:]
            if evidence.is_file():
                result["child"] = json.loads(evidence.read_text("utf-8"))
            result["passed"] = (
                result.get("returncode") == 0
                and result.get("child", {}).get("passed") is True
            )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
