"""Original, source-only Genesis diagnostic with non-TMSS model-safe startup.

BlastEm freezes on the ORIGINAL homebrew's unconditional write to
$A14000 when the emulated Genesis has no TMSS hardware. Preserve the
same original PPU/PSG program exactly except replace that 10-byte
optional unlock with five M68000 NOPs at the immutable original offset.
This is a controlled candidate test, NOT a patch of retail games, a
replacement for the original test, or proof of broad Genesis compatibility.
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

ROOT = Path(__file__).resolve().parents[1]
# Standalone script invocations in the Linux CI runner must import the
# project's existing fixture package without a user-specific PYTHONPATH.
sys.path.insert(0, str(ROOT))
from tools.genesis_homebrew_fixture import ENTRY, build_genesis_probe_rom
TMSS = bytes.fromhex("23fc 53454741 00a14000")
NOP = bytes.fromhex("4e71") * 5
OFFSET = ENTRY + 4


def original_without_unconditional_tmss():
    original = build_genesis_probe_rom(phase="full")
    if original[OFFSET:OFFSET + len(TMSS)] != TMSS:
        raise ValueError("Original Genesis startup instruction changed unexpectedly")
    candidate = bytearray(original)
    candidate[OFFSET:OFFSET + len(TMSS)] = NOP
    assert len(candidate) == len(original)
    return original, bytes(candidate)


def run_native(core, report, seconds=12):
    core, report = Path(core), Path(report)
    if seconds < 2 or seconds > 60:
        raise ValueError("Diagnostic playback must last 2..60 seconds")
    # Retain a strict per-host native library suffix. The original research
    # started on Linux; this same source-authored cartridge now runs on
    # Windows x64 and both macOS architectures without copying ELF binaries.
    expected = ".dll" if sys.platform == "win32" else (
        ".dylib" if sys.platform == "darwin" else ".so")
    if core.suffix.lower() != expected or not core.is_file() or core.is_symlink():
        raise ValueError(
            f"Expected ephemeral platform-native BlastEm core ending in {expected}"
        )
    if report.is_symlink():
        raise ValueError("Never write a reviewer report via symlink")
    original, candidate = original_without_unconditional_tmss()
    output = {
        "status": "UNAPPROVED-BLASTEM-GENESIS-NON-TMSS-HOMEBREW-DIAGNOSTIC",
        "original_homebrew_sha256": hashlib.sha256(original).hexdigest(),
        "non_tmss_variant_sha256": hashlib.sha256(candidate).hexdigest(),
        "exact_bytes_changed": len(TMSS),
        "skips_unconditional_tmss_register_write": True,
        "original_unmodified_fixture_still_separately_tested": True,
        "physical_gameplay_verified": False,
        "retail_genesis_compatibility_verified": False,
        "license_source_binary_review_complete": False,
        "public_release_approved": False,
        "passed": False, "native_exit_code": None, "timed_out": False,
        "details": None,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="anything-plays-tmss-research-") as tmp:
        folder = Path(tmp)
        rom = folder / "original-non-tmss-genesis.md"
        rom.write_bytes(candidate)
        child = folder / "child.json"
        env = os.environ.copy()
        env["HOME"] = str(folder)
        env["XDG_CONFIG_HOME"] = str(folder / "config")
        cmd = [
            sys.executable, str(ROOT / "tools/probe_genesis_homebrew.py"),
            "--child", "--core", str(core.resolve()), "--rom", str(rom),
            "--seconds", str(seconds), "--report", str(child),
        ]
        try:
            done = subprocess.run(cmd, cwd=ROOT, capture_output=True,
                                  text=True, env=env, timeout=seconds+25,
                                  check=False)
            output["native_exit_code"] = done.returncode
            output["console_tail"] = (done.stdout + done.stderr)[-6000:]
        except subprocess.TimeoutExpired:
            output["timed_out"] = True
        if child.is_file():
            output["details"] = json.loads(child.read_text("utf-8"))
        d = output["details"]
        output["passed"] = bool(
            output["native_exit_code"] == 0 and isinstance(d, dict)
            and d.get("passed") is True
            and d.get("real_video_frames", 0) >= 30
            and d.get("distinct_rgb_frames", 0) >= 2
            and d.get("nonzero_audio_values", 0) > 100
        )
    report.write_bytes((json.dumps(output, indent=2, sort_keys=True)+"\n").encode("utf-8"))
    return output

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--core", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--seconds", type=int, default=12)
    args=p.parse_args(argv)
    data=run_native(args.core, args.report, args.seconds)
    print(json.dumps({k: data[k] for k in ("passed","native_exit_code","timed_out",
                                         "status","original_homebrew_sha256",
                                         "non_tmss_variant_sha256")}, indent=2))
    return 0 if data["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
