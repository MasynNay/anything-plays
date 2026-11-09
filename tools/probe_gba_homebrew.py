"""Run the original GBA Mode-3/PSG program in production mGBA CoreSession.

Child process isolates native crashes; strict nonblank, changing RGB frames
and nonzero native audio PCM are required. Test ROM is temporary and is not
published or included with app installers.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.gba_homebrew_fixture import write_gba_probe
from tools.probe_gb_homebrew import _child as run_embedded_child


def _parent(core, report, seconds):
    outcome = {"system": "gba", "passed": False, "native_exit_code": None,
               "timed_out": False, "details": None, "error": None}
    report.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not core.is_file():
            raise FileNotFoundError("mGBA native core missing")
        with tempfile.TemporaryDirectory(prefix="ap-gba-original-") as tmp:
            root = Path(tmp)
            rom = root / "original-gba-audio-video.gba"
            outcome["fixture"] = write_gba_probe(rom)
            child_report = root / "report.json"
            cmd = [
                sys.executable, str(Path(__file__).resolve()),
                "--core", str(core), "--rom", str(rom),
                "--report", str(child_report), "--seconds", str(seconds),
                "--child",
            ]
            env = os.environ.copy()
            env["HOME"] = str(root)
            env["XDG_CONFIG_HOME"] = str(root / "config")
            try:
                result = subprocess.run(
                    cmd, check=False, capture_output=True, text=True,
                    env=env, timeout=seconds + 22,
                )
                outcome["native_exit_code"] = result.returncode
                outcome["console_tail"] = (result.stdout + result.stderr)[-13000:]
            except subprocess.TimeoutExpired as exc:
                outcome["timed_out"] = True
                raw = exc.stdout or b""
                outcome["console_tail"] = (
                    raw.decode("utf-8", "replace") if isinstance(raw, bytes)
                    else raw
                )[-13000:]
            if child_report.is_file():
                outcome["details"] = json.loads(child_report.read_text("utf-8"))
            outcome["passed"] = (
                outcome["native_exit_code"] == 0
                and isinstance(outcome["details"], dict)
                and outcome["details"].get("passed") is True
            )
            preview = child_report.with_name("gba-frame.png")
            if preview.is_file():
                shutil.copyfile(preview, report.with_name(preview.name))
    except Exception as exc:
        outcome["error"] = f"{type(exc).__name__}: {exc}"
    report.write_text(json.dumps(outcome, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(outcome, indent=2), flush=True)
    return 0 if outcome["passed"] else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--core",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--rom",type=Path)
    p.add_argument("--seconds",type=int,default=8)
    p.add_argument("--child",action="store_true")
    args=p.parse_args()
    if not 2<=args.seconds<=60:
        p.error("Seconds must be 2..60")
    if args.child:
        if args.rom is None:
            p.error("--child requires --rom")
        return run_embedded_child("gba",args.core.resolve(),args.rom.resolve(),
                                  args.report.resolve(),args.seconds)
    return _parent(args.core.resolve(),args.report.resolve(),args.seconds)


if __name__=="__main__":
    raise SystemExit(main())
