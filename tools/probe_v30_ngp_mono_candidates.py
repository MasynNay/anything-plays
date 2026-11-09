"""Isolated original monochrome NGP audio hunt across immutable MIT homebrew.

Research only: run the real native NeoPop CoreSession (including actual
native PCM callbacks) on ALL fourteen original .ngp-named calibration ROMs, which are ALL color-header 0x10.
No ROMs, native emulator libraries, music, BIOS or screenshots are committed,
attached, or included in the product. Never reinterpret silence as success.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "config/v3.0-ngp-mono-mit-candidates.json"
PROBE = ROOT / "tools/probe_ngp_mit_homebrew.py"
STATUS = "NGP-MONO-ALL-14-RESEARCH-CANDIDATES-UNAPPROVED"
MAX_ROM = 2 * 1024 * 1024
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")


def validate_index(index):
    if (not isinstance(index, dict)
            or index.get("schema_version") != 1
            or index.get("status") != "NGP-EXTENSION-COLOR-HEADER-CALIBRATION-RESEARCH-ONLY"
            or index.get("source_repository") != "Tixul/Ngpcraft_emulator"
            or index.get("source_license") != "MIT"
            or index.get("source_commit") != "93b1fd666ff375afcbb48079fbcf61dbb99b86b4"
            or index.get("tree_sha1") != index.get("source_commit")
            or index.get("total_ngp_extension_candidates") != 14
            or index.get("genuine_monochrome_header_candidates") != 0
            or index.get("header_examination") != "ALL-14-PINNED-UPSTREAM-GIT-BLOBS-HAVE-0x10-COLOR-COMPATIBILITY"
            or index.get("candidate_native_audio_verified") is not False
            or index.get("public_release_approved") is not False
            or index.get("distribution_in_app") is not False):
        raise ValueError("Unapproved mono MIT source registry changed unexpectedly")
    candidates = index.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 14:
        raise ValueError("Expected exactly 14 original mono source candidates")
    paths = []
    for entry in candidates:
        if not isinstance(entry, dict) or set(entry) != {
            "path", "git_blob_sha1", "size_bytes", "header_mode_byte",
            "genuine_monochrome_header"
        }:
            raise ValueError("Malformed source registry row")
        p = entry["path"]
        if (not isinstance(p, str)
                or not re.fullmatch(r"hw_calibration/a_[a-z0-9_]+\.ngp", p)
                or not GIT_SHA.fullmatch(str(entry["git_blob_sha1"]))
                or type(entry["size_bytes"]) is not int
                or not 1000 < entry["size_bytes"] < MAX_ROM
                or entry["header_mode_byte"] != 0x10
                or entry["genuine_monochrome_header"] is not False):
            raise ValueError("Unsafe/unspecified original NGP source candidate")
        paths.append(p)
    if paths != sorted(set(paths)):
        raise ValueError("Duplicate or unordered original NGP source candidates")
    if index.get("original_fixture") != "hw_calibration/a_align_calib_v12.ngp":
        raise ValueError("Previous native mono audio reference cannot be changed")
    if index["original_fixture"] not in paths:
        raise ValueError("Missing original mono calibration baseline")
    return candidates


def fetch_candidate(index, entry, destination, opener=urlopen):
    """Only fetch original pinned bytes, with exact Git blob and size checks."""
    validate_index(index)
    if entry not in index["candidates"]:
        raise ValueError("Candidate not in frozen upstream list")
    url = (f"https://raw.githubusercontent.com/{index['source_repository']}/"
           f"{index['source_commit']}/{entry['path']}")
    request = Request(url, headers={"User-Agent": "AnythingPlays-NGP-Mono-CI-Research"})
    with opener(request, timeout=35) as response:
        payload = response.read(MAX_ROM + 1)
    if len(payload) != entry["size_bytes"]:
        raise ValueError(f"{entry['path']}: immutable homebrew size changed")
    git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    if hashlib.sha1(git_blob).hexdigest() != entry["git_blob_sha1"]:
        raise ValueError(f"{entry['path']}: pinned Git blob SHA-1 mismatch")
    if len(payload) < 64 or payload[0x23] != entry["header_mode_byte"]:
        raise ValueError("Pinned .ngp-name source unexpectedly changed cartridge header")
    path = Path(destination)
    if path.is_symlink() or path.suffix != ".ngp":
        raise ValueError("Unsafe mono research fixture destination")
    path.write_bytes(payload)
    return {"url": url, "size_bytes": len(payload),
            "source_blob_sha1": entry["git_blob_sha1"],
            "candidate_sha256": hashlib.sha256(payload).hexdigest(),
            "header_mode_byte": payload[0x23]}


def _check_native_child(child):
    # Important: only the real CoreSession may return "audio_gate_passed".
    # This collector does not synthesize any PCM values or mark silence passed.
    if not isinstance(child, dict) or child.get("system") != "ngp":
        return None
    keys = ("native_audio_frames", "native_nonzero_pcm_values",
            "native_audio_peak", "sampled_nonblank_frames",
            "manual_a_native_positive_samples", "camera_b_native_positive_samples")
    if any(type(child.get(key)) is not int for key in keys):
        return None
    if any(child[key] < 0 for key in keys):
        return None
    if any(type(child.get(key)) is not bool for key in
           ("audio_gate_passed", "video_gate_passed", "input_gate_passed", "passed")):
        return None
    if child["audio_gate_passed"] and (
        child["native_nonzero_pcm_values"] <= 100
        or child["native_audio_peak"] <= 0 or child["native_audio_frames"] <= 1000
    ):
        raise ValueError("Impossible NGP PCM/audio gate combination")
    if child["passed"] and not all(child[k] for k in (
            "audio_gate_passed", "video_gate_passed", "input_gate_passed")):
        raise ValueError("Impossible native NGP complete-pass report")
    return {k: child[k] for k in (*keys,
             "audio_gate_passed", "video_gate_passed", "input_gate_passed", "passed")}


def scan(index, core, output, *, seconds=10, fetcher=fetch_candidate, runner=subprocess.run):
    candidates = validate_index(index)
    core, output = Path(core), Path(output)
    if not core.is_file() or core.is_symlink():
        raise ValueError("Native NGP core is missing or symlinked")
    if not 4 <= seconds <= 30:
        raise ValueError("Native NGP research seconds must be 4..30")
    if output.is_symlink() or (output.exists() and
                              (not output.is_dir() or any(output.iterdir()))):
        raise ValueError("Research-only output must be empty and not a symlink")
    output.mkdir(parents=True, exist_ok=True)
    core_digest = hashlib.sha256()
    with core.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            core_digest.update(chunk)
    report = {
        "schema_version": 1, "status": STATUS,
        "source_repo": index["source_repository"],
        "source_commit": index["source_commit"],
        "source_license": "MIT",
        "native_core_sha256": core_digest.hexdigest(),
        "attempted_original_mono_cartridges": 0,
        "total_pinned_original_mono_cartridges": 14,
        "source_downloads_integrity_verified": 0,
        "genuine_monochrome_header_candidates": 0,
        "all_pinned_files_color_header_despite_ngp_extension": True,
        "native_audio_pass_candidates": [],
        "full_native_av_input_pass_candidates": [],
        "all_source_candidate_downloads_verified": False,
        "real_game_compatibility_verified": False,
        "public_release_approved": False,
        "core_binary_corresponding_source_verified": False,
        "license_compatibility_approved": False,
        "per_cartridge": {},
    }
    for idx, entry in enumerate(candidates):
        with tempfile.TemporaryDirectory(prefix="ap-mono-audio-investigation-") as tmp:
            root = Path(tmp)
            rom = root / "original-mono.ngp"
            meta = fetcher(index, entry, rom)
            if (not isinstance(meta, dict)
                    or meta.get("source_blob_sha1") != entry["git_blob_sha1"]
                    or meta.get("header_mode_byte") != entry["header_mode_byte"]):
                raise ValueError("Original NGP test cartridge integrity not established")
            report["source_downloads_integrity_verified"] += 1
            child_path = root / "native-result.json"
            cmd = [
                sys.executable, str(PROBE), "--child", "--system", "ngp",
                "--core", str(core.resolve()), "--rom", str(rom),
                "--seconds", str(seconds), "--report", str(child_path),
            ]
            try:
                worker = runner(cmd, capture_output=True, text=True,
                                timeout=seconds + 40, check=False)
                exit_code = worker.returncode
                output_tail = (worker.stdout + worker.stderr)[-1400:]
            except subprocess.TimeoutExpired:
                exit_code = None
                output_tail = "native child exceeded strict bounded timeout"
            native = None
            if child_path.is_file() and not child_path.is_symlink():
                native = _check_native_child(json.loads(child_path.read_text("utf-8")))
            row = {
                "pinned_git_blob_sha1": meta["source_blob_sha1"],
                "original_rom_sha256": meta.get("candidate_sha256"),
                "source_size_bytes": meta.get("size_bytes"),
                "native_exit_code": exit_code,
                "native_report_available": native is not None,
                "declared_cartridge_header_mode": meta["header_mode_byte"],
                "genuine_monochrome_header": meta["header_mode_byte"] == 0x00,
                "native_audio_observed_but_color_header": bool(
                    meta["header_mode_byte"] == 0x10
                    and native and native["audio_gate_passed"]
                ),
                "native_measured_metrics": native,
                "diagnostic_tail": output_tail,
                "verified_audio": bool(
                    meta["header_mode_byte"] == 0x00 and native and native["audio_gate_passed"]
                ),
                "verified_full_native_av_input": bool(
                    meta["header_mode_byte"] == 0x00 and native and native["passed"] and exit_code == 0
                ),
            }
            report["per_cartridge"][entry["path"]] = row
            report["attempted_original_mono_cartridges"] += 1
            if row["genuine_monochrome_header"]:
                report["genuine_monochrome_header_candidates"] += 1
            if row["verified_audio"]:
                report["native_audio_pass_candidates"].append(entry["path"])
            if row["verified_full_native_av_input"]:
                report["full_native_av_input_pass_candidates"].append(entry["path"])
            print(f"{idx + 1}/14 {entry['path']}: "
                  f"native PCM={native['native_nonzero_pcm_values'] if native else 'no report'}; "
                  f"header=0x{row['declared_cartridge_header_mode']:02X} "
                  f"(not genuine mono); accepted mono audio={row['verified_audio']}; "
                  f"full={row['verified_full_native_av_input']}",
                  flush=True)
    report["all_source_candidate_downloads_verified"] = (
        report["attempted_original_mono_cartridges"] == 14
        and report["source_downloads_integrity_verified"] == 14
    )
    target = output / "NGP_MONO_NATIVE_AUDIO_RESEARCH_UNAPPROVED.json"
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {target.name}\n", "utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=INDEX)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=10)
    args = parser.parse_args(argv)
    try:
        index = json.loads(args.index.read_text("utf-8"))
        outcome = scan(index, args.core, args.output, seconds=args.seconds)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        parser.exit(1, f"NGP mono research incomplete: {error}\n")
    print(f"HEADER AUDIT: {outcome['genuine_monochrome_header_candidates']}/14 "
          "pinned .ngp-named sources actually declare mono mode 0x00. "
          "All fourteen declare color mode 0x10; none can certify real mono. "
          "Native audio observations remain research-only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
