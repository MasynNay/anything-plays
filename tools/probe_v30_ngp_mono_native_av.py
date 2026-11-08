"""Execute a real original monochrome K1GE + PSG cartridge in native NeoPop.

No Game ROM, BIOS, screenshots, generated sound waveforms or native libraries
are committed or uploaded. The only acceptance evidence is from real Libretro
callbacks recorded by the existing strict NeoPop video/audio/input test child.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from tools.build_v30_ngp_mono_native_av import (
    STATUS, create_original_mono_av_rom,
)
from tools.probe_v30_ngp_mono_candidates import _check_native_child

PROBE = Path(__file__).resolve().parents[1] / "tools/probe_ngp_mit_homebrew.py"


def native_monochrome_av(core, output, *, seconds=12, runner=subprocess.run):
    core = Path(core)
    output = Path(output)
    if not core.is_file() or core.is_symlink() or core.stat().st_size < 100:
        raise ValueError("True NeoPop native core required")
    if not 5 <= seconds <= 30:
        raise ValueError("Duration outside bounded original AV test")
    if output.is_symlink() or (output.exists() and
                               (not output.is_dir() or any(output.iterdir()))):
        raise ValueError("Research output must be empty, not a symlink")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ap-ngp-k1ge-native-") as folder:
        root = Path(folder)
        rom = root / "fully-original-mono-audio-video.ngp"
        payload = create_original_mono_av_rom()
        if payload[0x23] != 0:
            raise ValueError("ROM is not an authentic monochrome cartridge")
        rom.write_bytes(payload)
        child_output = root / "actual-native-report.json"
        command = [
            sys.executable, str(PROBE), "--child", "--system", "ngp",
            "--rom", str(rom), "--core", str(core.resolve()),
            "--seconds", str(seconds), "--report", str(child_output),
        ]
        native_exit = None
        tail = ""
        try:
            result = runner(command, capture_output=True, text=True, check=False,
                            timeout=seconds + 45)
            native_exit = result.returncode
            tail = (result.stdout + result.stderr)[-1200:]
        except subprocess.TimeoutExpired:
            tail = "Real native child exceeded per-ROM timeout"
        metrics = None
        verified = None
        if child_output.is_file() and not child_output.is_symlink():
            report = json.loads(child_output.read_text("utf-8"))
            verified = _check_native_child(report)
            if verified is not None:
                fields = [
                    "system", "native_video_frames", "observed_fps",
                    "sampled_nonblank_frames", "distinct_nonblank_frames",
                    "distinct_all_frames", "rgb_min_max",
                    "native_audio_frames", "native_nonzero_pcm_values",
                    "native_audio_peak", "sample_rate",
                    "video_gate_passed", "audio_gate_passed", "input_gate_passed",
                    "manual_a_native_positive_samples", "camera_b_native_positive_samples",
                    "save_state_roundtrip", "passed",
                ]
                metrics = {key: report.get(key) for key in fields}
        audio = bool(metrics and metrics["audio_gate_passed"])
        video = bool(metrics and metrics["video_gate_passed"])
        input_ok = bool(metrics and metrics["input_gate_passed"])
        complete = bool(audio and video and input_ok
                        and metrics and metrics["passed"]
                        and native_exit == 0)
        h = hashlib.sha256()
        with core.open("rb") as stream:
            for part in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(part)
        evidence = {
            "schema_version": 1,
            "status": STATUS,
            "mono_cartridge_header_value": 0,
            "generator": "tools/build_v30_ngp_mono_native_av.py",
            "generator_incorporates_upstream_source_verified_psg_enable": True,
            "generated_rom_sha256": hashlib.sha256(payload).hexdigest(),
            "native_core_sha256": h.hexdigest(),
            "actual_native_exit": native_exit,
            "native_metrics": metrics,
            "audio_verified_in_native_test": audio,
            "changing_monochrome_video_verified_in_native_test": video,
            "native_manual_and_camera_input_query_verified": input_ok,
            "full_native_audio_video_input_verified": complete,
            "physical_speaker_or_retail_gameplay_verified": False,
            "all_four_platforms_verified": False,
            "cartridge_flash_save_verified": False,
            "license_compatibility_reviewed": False,
            "public_distribution_approved": False,
            "public_release_approved": False,
            "diagnostic_tail": tail,
            "generated_game_or_bios_in_release": False,
        }
    report = output / "NGP_ORIGINAL_MONO_K1GE_NATIVE_AV_UNAPPROVED.json"
    report.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    # GNU sha256sum -c under Git Bash treats Windows CRLF's carriage
    # return as part of the filename. Always emit an exact LF checksum file,
    # while hashing the actual report bytes present on this native platform.
    checksum = f"{hashlib.sha256(report.read_bytes()).hexdigest()}  {report.name}\n"
    (output / "SHA256SUMS.txt").write_bytes(checksum.encode("ascii"))
    return evidence


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--core", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seconds", type=int, default=12)
    a = p.parse_args(argv)
    try:
        result = native_monochrome_av(a.core, a.output, seconds=a.seconds)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as e:
        p.exit(1, f"Real original monochrome K1GE/PSG research incomplete: {e}\n")
    print(f"REAL NATIVE: MONO PSG audio={result['audio_verified_in_native_test']} "
          f"CHANGING K1GE video={result['changing_monochrome_video_verified_in_native_test']} "
          f"manual and camera inputs={result['native_manual_and_camera_input_query_verified']} "
          f"full A/V/input={result['full_native_audio_video_input_verified']}; "
          "PUBLIC RELEASE UNAPPROVED", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
