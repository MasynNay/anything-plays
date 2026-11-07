"""Isolate a native Genesis crash without testing or distributing a commercial ROM.

Each ROM variant is assembled from our original 68000 opcodes. The native
Libretro core runs in its own child process so SIGSEGV cannot kill this
diagnostic runner. Report all phases, never silently label smoke as gameplay.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
from tools.genesis_homebrew_fixture import PHASES


def diagnose(core, report, seconds=3):
    results = {}
    report.parent.mkdir(parents=True, exist_ok=True)
    for phase in PHASES:
        child_report = report.with_name(f"genesis-{phase}.json")
        cmd = [
            sys.executable, str(ROOT / "tools/probe_genesis_homebrew.py"),
            "--core", str(core), "--report", str(child_report),
            "--phase", phase, "--seconds", str(seconds),
            "--smoke-only",
        ]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=seconds + 12,
                check=False,
            )
            result = json.loads(child_report.read_text("utf-8"))
            results[phase] = {
                "exited": proc.returncode,
                "native_exit_code": result.get("native_exit_code"),
                "passed_smoke": bool(result.get("passed")),
                "details": result.get("details"),
                "native_log_tail": result.get("console_tail", "")[-900:],
            }
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            results[phase] = {"passed_smoke": False,
                              "error": f"{type(exc).__name__}: {exc}"[:400]}
        child_report.unlink(missing_ok=True)
        print(f"Genesis {phase}: {'live' if results[phase]['passed_smoke'] else 'FAILED'}", flush=True)
    first_failed = next((p for p in PHASES if not results[p]["passed_smoke"]), None)
    output = {
        "schema_version": 1,
        "kind": "native Genesis init crash isolation; NOT gameplay certification",
        "first_failed_phase": first_failed,
        "phases": results,
        "all_passed": first_failed is None,
    }
    report.write_text(json.dumps(output, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"first_failed_phase": first_failed,
                      "all_passed": output["all_passed"]}, indent=2))
    return 0 if output["all_passed"] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=3)
    args=parser.parse_args()
    if not 1 <= args.seconds <= 10:
        parser.error("Expected 1-10 seconds per phase")
    return diagnose(args.core.resolve(), args.report.resolve(), args.seconds)


if __name__ == "__main__":
    raise SystemExit(main())
