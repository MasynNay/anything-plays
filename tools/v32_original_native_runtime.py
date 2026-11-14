"""Unreleased 3.2 native-gameplay smoke using ORIGINAL generated homebrew.

Run against the just-repacked, exact-head 18-profile Linux QA app. This
actually executes the installed native .so through production Libretro, and
checks decoded changing RGB and core-generated PCM with strict subprocess
timeouts. NO proprietary game assets, BIOS, devices or network are accessed.

Six native console profiles now gate this incremental runtime checkpoint,
including the proven Supafaust SNES alternative and BlastEm's original
non-TMSS Genesis diagnostic. Eight more source-generated console profiles
are investigated separately; failed exploratory results are never marked as
passing, nor are they required to pass the six proven baseline gates.
Do not relabel this as 18/18 real-game compatibility or public approval.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from anything_plays.v30_gpl_trial import validate_trial_core_directory
from tools.stage_v32_full_linux import FULL, STATUS as FULL_STATUS, no_links
from tools.verify_v31_rc import validate_staged_identity

REQUIRED = ("gb", "gbc", "gba", "nes", "snes", "genesis")
EXPLORATORY = (
    "mastersystem", "gamegear", "sg1000", "atari2600", "atari7800",
    "pce", "ws", "wsc",
)
CASES = {
    "gb": ("mgba", "tools.probe_gb_homebrew", ("--system", "gb")),
    "gbc": ("mgba", "tools.probe_gb_homebrew", ("--system", "gbc")),
    "gba": ("mgba", "tools.probe_gba_homebrew", ()),
    "nes": ("fceumm", "tools.probe_nes_homebrew", ()),
    "snes": ("mednafen_supafaust", "tools.probe_snes_homebrew", ()),
    # BlastEm emulates non-TMSS Genesis hardware. The project's original
    # variant retains its cartridge's video/audio program, replacing only
    # an unconditional TMSS register write with M68000 NOP instructions.
    "genesis": ("blastem", "tools.probe_v30_blastem_genesis_variant", ()),
    "mastersystem": ("blastem", "tools.probe_sega8_homebrew",
                     ("--system", "mastersystem")),
    "gamegear": ("blastem", "tools.probe_sega8_homebrew",
                 ("--system", "gamegear")),
    "sg1000": ("blastem", "tools.probe_sega8_homebrew",
               ("--system", "sg1000")),
    # This QA package intentionally uses the source-built GPL2+ Tia
    # alternative, NOT the older Stella2014 core from 3.1.
    "atari2600": ("tia", "tools.probe_atari_homebrew", ()),
    "atari7800": ("prosystem", "tools.probe_atari7800_homebrew", ()),
    "pce": ("mednafen_pce_fast", "tools.probe_pce_homebrew", ()),
    "ws": ("mednafen_wswan", "tools.probe_wonderswan_homebrew",
           ("--system", "ws")),
    "wsc": ("mednafen_wswan", "tools.probe_wonderswan_homebrew",
            ("--system", "wsc")),
}
STATUS = "PRIVATE_V32_FULL_NATIVE_ORIGINAL_HOMEBREW_RUNTIME_RESEARCH_NOT_RELEASE"
SOURCE_ROOT = Path(__file__).resolve().parents[1]


def check_preflight(bundle, receipt, sha, systems):
    """Reject non-3.2 or forged full-core QA before executing any ROM."""
    if (os.environ.get("AP_V32_PREVIEW_BUILD") != "1"
            or os.environ.get("AP_RELEASE_BUILD") == "1"
            or os.environ.get("AP_V30_APPROVED_RELEASE") == "1"):
        raise ValueError("Only unreleased 3.2 source-built QA may execute probes")
    if not isinstance(sha, str) or re.fullmatch(r"[a-f0-9]{40}", sha) is None:
        raise ValueError("Exact source commit required")
    if not systems or len(set(systems)) != len(systems) or any(
            name not in CASES for name in systems):
        raise ValueError("Unknown, duplicate or missing original-fixture system")
    bundle, receipt = Path(bundle), Path(receipt)
    if bundle.is_symlink() or not bundle.is_dir():
        raise ValueError("Missing or unsafe extracted 3.2 private application")
    if receipt.is_symlink() or not receipt.is_file() or receipt.stat().st_size > 32768:
        raise ValueError("Missing or unsafe 3.2 full-native source receipt")
    validate_staged_identity(bundle, channel="v32_preview")
    data = json.loads(receipt.read_text("utf-8"))
    required = {
        "status": FULL_STATUS,
        "source_revision": sha,
        "installer": FULL,
        "target": "linux-x64",
        "native_core_count": 11,
        "console_profiles": 18,
        "native_core_bytes_preserved": True,
        "settings_namespace": "anything-plays-32-preview",
        "public_release_approved": False,
        "all_18_consoles_gameplay_verified": False,
    }
    if not isinstance(data, dict) or any(
            type(data.get(k)) is not type(v) or data.get(k) != v
            for k, v in required.items()):
        raise ValueError("Full native 3.2 source receipt false or inconsistent")
    cores = bundle/"cores"
    no_links(cores)
    manifest = validate_trial_core_directory(cores, ".so")
    if manifest.get("native_core_count") != 11 or manifest.get("all_console_profiles") != 18:
        raise ValueError("Original installed source-built core inventory incomplete")
    for name in systems:
        candidate = cores/(CASES[name][0] + "_libretro.so")
        if not candidate.is_file() or candidate.is_symlink():
            raise ValueError("Actual source-built core for original homebrew is absent")
    return cores


def safe_summary(system, raw, exit_code, timed_out):
    """Allowlist native evidence fields, discard traceback/paths/ROM details."""
    if not isinstance(raw, dict):
        raw = {}
    details = raw.get("details") if isinstance(raw.get("details"), dict) else {}
    value = {
        "system": system,
        "core_name": CASES[system][0],
        "required_gate": system in REQUIRED,
        "native_child_exit_zero": exit_code == 0,
        # Numeric native exit status only; never retain stderr, stack
        # traces, raw ROM paths, machine usernames or private directories.
        "native_process_exit_code": (
            raw.get("native_exit_code")
            if type(raw.get("native_exit_code")) is int
            and -255 <= raw["native_exit_code"] <= 255 else None
        ),
        "timed_out": bool(timed_out),
        "probe_passed": not timed_out and exit_code == 0 and raw.get("passed") is True,
    }
    # Each original program has different names for equivalent counters.
    for key in (
        "native_video_frames", "video_callback_frames", "real_video_frames",
        "sampled_nonblank_frames", "nonblank_samples", "nonblank_sampled_frames",
        "distinct_rgb_frames", "unique_nonblank_frame_hashes",
        "native_pcm_frames", "native_audio_sample_frames",
        "apu_audio_sample_frames", "psg_pcm_frames",
        "native_nonzero_pcm_values", "native_nonzero_pcm_samples",
        "apu_nonzero_sample_values", "nonzero_audio_values",
        "sample_rate", "native_pcm_sample_rate", "observed_fps",
    ):
        number = details.get(key)
        if type(number) in (int, float) and 0 <= number < 1_000_000_000:
            value[key] = number
    return value


def run_case(core_dir, system, seconds, home):
    core, module, arguments = CASES[system]
    with tempfile.TemporaryDirectory(prefix="ap32-original-game-") as td:
        report = Path(td)/"native-result.json"
        env = dict(os.environ)
        env.update({
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home/"config"),
            "XDG_DATA_HOME": str(home/"data"),
            "SDL_AUDIODRIVER": "dummy",
            "SDL_VIDEODRIVER": "dummy",
            "PYGAME_HIDE_SUPPORT_PROMPT": "1",
        })
        command = [
            sys.executable, "-m", module,
            "--core", str(core_dir/(core + "_libretro.so")),
            "--report", str(report),
            "--seconds", str(seconds),
            *arguments,
        ]
        try:
            executed = subprocess.run(
                command, cwd=SOURCE_ROOT, env=env, text=True,
                capture_output=True, check=False,
                timeout=seconds + 38,
            )
        except subprocess.TimeoutExpired:
            return safe_summary(system, {}, -1, True)
        try:
            raw = json.loads(report.read_text("utf-8"))
        except (ValueError, OSError):
            raw = {}
        return safe_summary(system, raw, executed.returncode, False)


def analyze_results(probes, systems):
    indexed = {item["system"]: item for item in probes}
    required_tested = tuple(system for system in systems if system in REQUIRED)
    explored = tuple(system for system in systems if system in EXPLORATORY)
    passed = (all(name in indexed for name in REQUIRED)
              and all(indexed[system]["probe_passed"] for system in REQUIRED))
    return {
        "schema_version": 1,
        "status": STATUS,
        "original_source_generated_homebrew_only": True,
        "binary_tested": "installed full-native 3.2 Linux core payload",
        "profiles_in_native_inventory": 18,
        "native_core_families_in_inventory": 11,
        "required_profiles_tested": list(required_tested),
        "required_profiles_passed": sum(
            indexed[system]["probe_passed"] for system in required_tested
        ),
        "exploratory_profiles_tested": list(explored),
        "exploratory_profiles_passed": sum(
            indexed[system]["probe_passed"] for system in explored
        ),
        "probes": probes,
        "passed": passed,
        "all_18_consoles_gameplay_verified": False,
        "commercial_game_compatibility_verified": False,
        "physical_camera_verified": False,
        "physical_controller_verified": False,
        "physical_speaker_verified": False,
        "public_release_approved": False,
    }


def execute(bundle, receipt, sha, output, systems, seconds):
    if not 2 <= seconds <= 15:
        raise ValueError("Bounded per-system original-game duration required")
    if not all(name in systems for name in REQUIRED):
        raise ValueError("Required original homebrew runtime systems must be included")
    cores = check_preflight(bundle, receipt, sha, systems)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Do not overwrite original-game runtime QA evidence")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ap32-homebrew-private-") as td:
        home = Path(td)
        checks = [run_case(cores, system, seconds, home)
                  for system in systems]
    record = analyze_results(checks, systems)
    record["source_revision"] = sha
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps({
        "status": record["status"], "passed": record["passed"],
        "required_profiles_passed": record["required_profiles_passed"],
        "required_profiles_tested": record["required_profiles_tested"],
        "exploratory_profiles_passed": record["exploratory_profiles_passed"],
        "exploratory_profiles_tested": record["exploratory_profiles_tested"],
    }, indent=2), flush=True)
    return 0 if record["passed"] else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--source-receipt", type=Path, required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--seconds", type=int, default=4)
    a = p.parse_args()
    return execute(a.bundle, a.source_receipt, a.source_sha, a.report,
                   tuple(CASES), a.seconds)


if __name__ == "__main__":
    raise SystemExit(main())
