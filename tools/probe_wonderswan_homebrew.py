"""Isolated WonderSwan mono/color game A/V through production Mednafen core.

Original V30MZ ROM is generated only at CI runtime; no BIOS, game download or
external emulator is required. Fail-closed native video/PCM acceptance.
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
from tools.wonderswan_homebrew_fixture import SYSTEMS, write_wonderswan_probe
from tools.probe_gb_homebrew import _child as run_native_core


def _parent(system, core, report, seconds):
    result = {"system": system, "passed": False, "native_exit_code": None,
              "timed_out": False, "details": None, "error": None}
    try:
        if not core.is_file():
            raise FileNotFoundError("Missing Mednafen WonderSwan native core")
        with tempfile.TemporaryDirectory(prefix="ap-original-wonderswan-") as d:
            root = Path(d)
            rom = root / ("original-wonderswan." + system)
            result["fixture"] = write_wonderswan_probe(rom, system)
            child = root / "child.json"
            env = os.environ.copy()
            env["HOME"] = str(root)
            env["XDG_CONFIG_HOME"] = str(root / "config")
            command = [
                sys.executable, str(Path(__file__).resolve()), "--child",
                "--system", system, "--core", str(core), "--rom", str(rom),
                "--report", str(child), "--seconds", str(seconds),
            ]
            try:
                process = subprocess.run(
                    command, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True,
                    check=False, timeout=seconds + 25,
                )
                result["native_exit_code"] = process.returncode
                result["console_tail"] = process.stdout[-13000:]
            except subprocess.TimeoutExpired as exc:
                result["timed_out"] = True
                raw = exc.stdout or b""
                result["console_tail"] = (
                    raw.decode("utf-8", "replace") if isinstance(raw, bytes)
                    else raw
                )[-13000:]
            if child.is_file():
                result["details"] = json.loads(child.read_text("utf-8"))
            image = child.with_name(f"{system}-frame.png")
            if image.is_file():
                shutil.copyfile(image, report.with_name(image.name))
            result["passed"] = (
                result["native_exit_code"] == 0
                and isinstance(result["details"], dict)
                and result["details"].get("passed") is True
            )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2) + "\n",
                          encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
    return 0 if result["passed"] else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--system", choices=SYSTEMS, required=True)
    p.add_argument("--core", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--seconds", type=int, default=8)
    p.add_argument("--rom", type=Path)
    p.add_argument("--child", action="store_true")
    args=p.parse_args()
    if not 2<=args.seconds<=60:
        p.error("Seconds must be 2..60")
    if args.child:
        if args.rom is None:
            p.error("--child requires --rom")
        return run_native_core(args.system,args.core.resolve(),
                               args.rom.resolve(),args.report.resolve(),
                               args.seconds)
    return _parent(args.system,args.core.resolve(),args.report.resolve(),
                   args.seconds)


if __name__=="__main__":
    raise SystemExit(main())
