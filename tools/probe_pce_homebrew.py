"""Run an original PC Engine video/PSG ROM in production Libretro CoreSession.

The parent writes a new temporary source-generated .pce cartridge and runs
native Mednafen PCE Fast in a crash-isolated process. Original ROM images
are NOT part of the installer's game assets.
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
from tools.pce_homebrew_fixture import write_pce_probe
from tools.probe_gb_homebrew import _child as run_core


def _parent(core, report, seconds):
    result = {"system": "pce", "passed": False, "native_exit_code": None,
              "details": None, "error": None, "timed_out": False}
    try:
        if not core.is_file():
            raise FileNotFoundError("PCE Fast native core unavailable")
        with tempfile.TemporaryDirectory(prefix="anythingplays-pce-original-") as d:
            folder = Path(d)
            rom = folder / "original-vdc-psg.pce"
            result["fixture"] = write_pce_probe(rom)
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
                p = subprocess.run(
                    command, capture_output=True, text=True,
                    check=False, timeout=seconds + 25, env=env,
                )
                result["native_exit_code"] = p.returncode
                result["console_tail"] = (p.stdout + p.stderr)[-14000:]
            except subprocess.TimeoutExpired as exc:
                result["timed_out"] = True
                raw = exc.stdout or b""
                result["console_tail"] = (
                    raw.decode("utf-8", "replace")
                    if isinstance(raw, bytes) else raw
                )[-14000:]
            if child.is_file():
                result["details"] = json.loads(child.read_text("utf-8"))
            result["passed"] = (
                result["native_exit_code"] == 0
                and isinstance(result["details"], dict)
                and result["details"].get("passed") is True
            )
            frame = folder / "pce-frame.png"
            if frame.is_file():
                report.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(frame, report.with_name(frame.name))
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
    return 0 if result["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=8)
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if not 2 <= args.seconds <= 60:
        parser.error("seconds must be 2..60")
    if args.child:
        if args.rom is None:
            parser.error("--child requires --rom")
        return run_core("pce", args.core.resolve(), args.rom.resolve(),
                        args.report.resolve(), args.seconds)
    return _parent(args.core.resolve(), args.report.resolve(), args.seconds)


if __name__ == "__main__":
    raise SystemExit(main())
