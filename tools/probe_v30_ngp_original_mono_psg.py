"""Research authentic native audio from freshly built original mono NGP PSG code.

No ROM/BIOS/SDK files ever enter a repository, release, or Actions artifact.
Only the upstream-approved, actual native CoreSession's audio callbacks can
mark the test audible. Native crashes and silence remain explicitly unpassed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from tools.build_v30_ngp_original_mono_psg import (
    HEADER_BYTES, ENTRY, VARIANTS, create_original_mono_rom,
)
from tools.probe_v30_ngp_mono_candidates import _check_native_child

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tools/probe_ngp_mit_homebrew.py"
STATUS = "ORIGINAL-MONO-PSG-NATIVE-EXPERIMENT-NO-RELEASE-APPROVAL"


def measure_original_psg(core, out, *, seconds=10, runner=subprocess.run):
    core, out = Path(core), Path(out)
    if not core.is_file() or core.is_symlink() or core.stat().st_size <= 100:
        raise ValueError("A real native core library is required")
    if not 4 <= seconds <= 30:
        raise ValueError("NGP original PSG test seconds must be 4..30")
    if out.is_symlink() or (out.exists() and
                            (not out.is_dir() or any(out.iterdir()))):
        raise ValueError("Original PSG research output must be empty and not a symlink")
    out.mkdir(parents=True, exist_ok=True)
    core_hash = hashlib.sha256()
    with core.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            core_hash.update(block)
    report = {
        "schema_version": 1,
        "status": STATUS,
        "core_native_sha256": core_hash.hexdigest(),
        "generated_from_original_locally_auditable_source": True,
        "compiled_with_proprietary_toshiba_toolchain": False,
        "header_uses_actual_monochrome_system_byte": True,
        "native_pcm_pass_variants": [],
        "full_native_video_pcm_input_pass_variants": [],
        "physical_speakers_or_retail_games_verified": False,
        "binary_redistribution_approved": False,
        "combined_license_review_complete": False,
        "public_release_approved": False,
        "variants": {},
    }
    for variant in VARIANTS:
        with tempfile.TemporaryDirectory(prefix="ap-v30-original-mono-psg-") as td:
            tmp = Path(td)
            rom_path = tmp / "original-source-built-mono.ngp"
            rom = create_original_mono_rom(variant)
            if rom[0x23] != 0 or int.from_bytes(rom[0x1C:0x20], "little") != ENTRY:
                raise ValueError("Invalid original monochrome header")
            rom_path.write_bytes(rom)
            child_result = tmp / "actual-core-report.json"
            command = [
                sys.executable, str(PROBE), "--child", "--system", "ngp",
                "--core", str(core.resolve()), "--rom", str(rom_path),
                "--seconds", str(seconds), "--report", str(child_result),
            ]
            exit_code, output = None, ""
            try:
                process = runner(command, capture_output=True, text=True,
                                 timeout=seconds + 40, check=False)
                exit_code = process.returncode
                output = (process.stdout + process.stderr)[-1300:]
            except subprocess.TimeoutExpired:
                output = "Original ROM child timed out; no audio verified"
            native = None
            if child_result.is_file() and not child_result.is_symlink():
                native = _check_native_child(json.loads(child_result.read_text("utf-8")))
            audible = bool(native and native["audio_gate_passed"])
            full = bool(native and native["passed"] and exit_code == 0)
            row = {
                "rom_sha256": hashlib.sha256(rom).hexdigest(),
                "rom_size_bytes": len(rom),
                "source_generated_monochrome_compatibility_byte": 0,
                "real_native_audio_gate_passed": audible,
                "real_native_full_av_input_passed": full,
                "native_process_exit_code": exit_code,
                "real_native_metrics": native,
                "diagnostic_tail": output,
            }
            report["variants"][variant] = row
            if audible:
                report["native_pcm_pass_variants"].append(variant)
            if full:
                report["full_native_video_pcm_input_pass_variants"].append(variant)
            print(f"{variant}: actual native nonzero PCM="
                  f"{native['native_nonzero_pcm_values'] if native else 'none'}; "
                  f"native audio={audible}; full AV/input={full}", flush=True)
    if len(report["variants"]) != len(VARIANTS):
        raise ValueError("Original source-built research variants missing")
    doc = out / "NGP_ORIGINAL_MONO_PSG_UNAPPROVED.json"
    doc.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    (out / "SHA256SUMS.txt").write_text(
        f"{hashlib.sha256(doc.read_bytes()).hexdigest()}  {doc.name}\n", "utf-8")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--core", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seconds", type=int, default=10)
    args = p.parse_args(argv)
    try:
        result = measure_original_psg(args.core, args.output,
                                      seconds=args.seconds)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        p.exit(1, f"Real NGP original mono PSG research not complete: {error}\n")
    print(f"ORIGINAL MONO PSG: {len(result['native_pcm_pass_variants'])}/4 "
          "produced genuinely qualifying native PCM; "
          f"{len(result['full_native_video_pcm_input_pass_variants'])}/4 "
          "passed full native AV/input. Research ONLY, no 3.0 release approval.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
