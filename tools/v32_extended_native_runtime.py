"""3.2 private Linux runtime research for NGP, NGPC, N64 and GameCube.

This runner consumes the actual, verified 11-native-core Linux 3.2 QA
installation. NGP uses an original on-the-fly monochrome TLCS-900/H game.
NGPC, N64, and GameCube fetch ONLY their pre-existing hash-pinned, legally
testable MIT / Unlicense / zlib homebrew inside disposable GitHub CI.

Each native emulator runs inside an independently timed child process. No
failed probe is treated as passing. The strict 14-profile original-homebrew
runner remains entirely separate and unaffected by experimental 3D cores.

Never use this as a claim about commercial games, real camera/controller
hardware, production licensing, public deployment, or 18/18 compatibility.
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

from tools.v32_original_native_runtime import check_preflight
from tools.ngp_mit_fixtures import FIXTURES
from tools.n64_homebrew_fixture import ROM_SHA256
from tools.gamecube_homebrew_fixture import PINNED_SHA256

TARGETS = ("ngp", "ngpc", "n64", "gamecube")
CORES = {
    "ngp": "mednafen_ngp",
    "ngpc": "mednafen_ngp",
    "n64": "parallel_n64",
    "gamecube": "dolphin",
}
FIXTURE_ORIGIN = {
    "ngp": "source_generated_original_monochrome",
    "ngpc": "hash_pinned_mit_color_homebrew",
    "n64": "hash_pinned_public_domain_homebrew",
    "gamecube": "hash_pinned_zlib_homebrew",
}
STATUS = "PRIVATE_V32_EXTENDED_FOUR_NATIVE_SOFTWARE_RESEARCH_NOT_RELEASE"
ROOT = Path(__file__).resolve().parents[1]
SECONDS = {"ngp": 10, "ngpc": 10, "n64": 12, "gamecube": 18}
TIMEOUTS = {"ngp": 65, "ngpc": 100, "n64": 95, "gamecube": 115}
REPORT_NAME = "V32_FOUR_REMAINING_CONSOLES_RESEARCH_QA.json"


def check_sources(bundle, receipt, sha):
    """Verify exact preview, source receipt and entire original 11-core set."""
    root = check_preflight(bundle, receipt, sha, ("gb",))
    paths = {}
    for profile in TARGETS:
        core = root / (CORES[profile] + "_libretro.so")
        if (core.is_symlink() or not core.is_file()
                or not 1024 < core.stat().st_size <= 200 * 1024 * 1024):
            raise ValueError("Missing/unsafe original native for " + profile)
        paths[profile] = core
    return paths


def command_for(profile, core, report, seconds, temp):
    """Use the existing mature probe, never make up synthetic A/V evidence."""
    if profile == "ngp":
        destination = temp / "original-mono"
        return [
            sys.executable, "-m", "tools.probe_v30_ngp_mono_native_av",
            "--core", str(core), "--output", str(destination),
            "--seconds", str(seconds),
        ], destination / "NGP_ORIGINAL_MONO_K1GE_NATIVE_AV_UNAPPROVED.json"
    base = [sys.executable, "-m"]
    if profile == "ngpc":
        return [
            *base, "tools.probe_ngp_mit_homebrew",
            "--system", "ngpc", "--core", str(core),
            "--seconds", str(seconds), "--report", str(report),
        ], report
    if profile == "n64":
        return [
            *base, "tools.probe_n64_homebrew",
            "--core", str(core), "--seconds", str(seconds),
            "--report", str(report),
        ], report
    if profile == "gamecube":
        return [
            *base, "tools.probe_gamecube_homebrew",
            "--core", str(core), "--seconds", str(seconds),
            "--report", str(report), "--cpu-core", "5",
            "--single-core", "--exercise-controls",
        ], report
    raise ValueError("Unknown original-console research profile")


def _verified(profile, evidence, exit_code):
    if exit_code != 0 or not isinstance(evidence, dict):
        return False
    details = evidence.get("details")
    if profile == "ngp":
        metrics = evidence.get("native_metrics")
        return (
            evidence.get("mono_cartridge_header_value") == 0
            and evidence.get("full_native_audio_video_input_verified") is True
            and evidence.get("changing_monochrome_video_verified_in_native_test") is True
            and evidence.get("audio_verified_in_native_test") is True
            and evidence.get("native_manual_and_camera_input_query_verified") is True
            and isinstance(metrics, dict) and metrics.get("passed") is True
        )
    if profile == "ngpc":
        fixture = evidence.get("fixture")
        return (
            evidence.get("probe_passed") is True
            and isinstance(fixture, dict)
            and fixture.get("header_matches_test_target") is True
            and fixture.get("header_mode_byte") == 0x10
            and fixture.get("license") == "MIT"
            and fixture.get("git_blob_sha1") == FIXTURES["ngpc"]["blob_sha1"]
            and isinstance(details, dict)
            and details.get("passed") is True
            and details.get("video_gate_passed") is True
            and details.get("audio_gate_passed") is True
            and details.get("input_gate_passed") is True
        )
    if profile == "n64":
        fixture = evidence.get("source")
        return (
            evidence.get("probe_passed") is True
            and isinstance(fixture, dict)
            and fixture.get("sha256") == ROM_SHA256
            and isinstance(details, dict)
            and details.get("playback_probe_passed") is True
            and details.get("frames_valid") is True
            and type(details.get("video_callback_frames")) is int
            and details["video_callback_frames"] >= 3
        )
    if profile == "gamecube":
        return (
            evidence.get("probe_passed") is True
            and re.fullmatch(r"[a-f0-9]{64}",
                             str(evidence.get("fixture_sha256", ""))) is not None
            and isinstance(details, dict)
            and details.get("playback_probe_passed") is True
            and details.get("static_homebrew_interactive_passed") is True
            and details.get("controller_input_exercised") is True
            and type(details.get("video_callback_frames")) is int
            and details["video_callback_frames"] >= 3
        )
    return False


def safe_evidence(profile, raw, exit_code, timed_out):
    """Never emit log tails, URLs, local paths, ROM images or exception text."""
    raw = raw if isinstance(raw, dict) else {}
    details = raw.get("details")
    if not isinstance(details, dict):
        details = {}
    row = {
        "profile": profile,
        "native_core": CORES[profile],
        "fixture_source": FIXTURE_ORIGIN[profile],
        "fixture_fetched_only_for_private_CI": profile != "ngp",
        "native_process_exit_code": (
            exit_code if type(exit_code) is int and -255 <= exit_code <= 255
            else None
        ),
        "timed_out": bool(timed_out),
        "native_probe_verified": not timed_out and _verified(profile, raw, exit_code),
        "is_exploratory": True,
        "real_user_gameplay_tested": False,
        "physical_camera_tested": False,
        "physical_controller_tested": False,
        "physical_speakers_tested": False,
        "public_release_approved": False,
    }
    # Only known numeric metrics from actual native callbacks.
    metrics = (raw.get("native_metrics") if profile == "ngp" else details)
    if not isinstance(metrics, dict):
        metrics = {}
    for name in (
        "native_video_frames", "video_callback_frames",
        "sampled_nonblank_frames", "nonblank_samples",
        "distinct_nonblank_frames", "distinct_all_frames",
        "distinct_rgb_frames", "unique_nonblank_rgb_frames",
        "native_audio_frames", "native_nonzero_pcm_values",
        "sample_rate", "observed_fps", "nonblank_sampled_frames",
        "core_emulation_steps", "emulation_steps_per_second",
    ):
        val = metrics.get(name)
        if type(val) in (int, float) and 0 <= val < 1_000_000_000:
            row[name] = val
    return row


def run_case(profile, core, private_home):
    if profile not in TARGETS:
        raise ValueError("Unknown extended native profile")
    with tempfile.TemporaryDirectory(prefix="ap32-remaining-console-") as td:
        temp = Path(td)
        report = temp / (profile + "-native.json")
        cmd, expected = command_for(
            profile, core, report, SECONDS[profile], temp,
        )
        env = dict(os.environ)
        env.update({
            "HOME": str(private_home),
            "USERPROFILE": str(private_home),
            "APPDATA": str(private_home / "roaming"),
            "LOCALAPPDATA": str(private_home / "local"),
            "XDG_CONFIG_HOME": str(private_home / "config"),
            "XDG_DATA_HOME": str(private_home / "data"),
            "SDL_AUDIODRIVER": "dummy",
            "PYGAME_HIDE_SUPPORT_PROMPT": "1",
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "AP_V32_PREVIEW": "1",
        })
        # No display is opened by these probes; if a software GPU needs
        # X11, the CI job supplies an isolated Xvfb DISPLAY.
        try:
            proc = subprocess.run(
                cmd, cwd=ROOT, env=env, text=True, capture_output=True,
                check=False, timeout=TIMEOUTS[profile],
            )
            exit_code, timeout = proc.returncode, False
        except subprocess.TimeoutExpired:
            exit_code, timeout = None, True
        try:
            raw = json.loads(expected.read_text("utf-8"))
        except (OSError, ValueError):
            raw = {}
        return safe_evidence(profile, raw, exit_code, timeout)


def execute(bundle, receipt, sha, output, *, run=run_case):
    if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise ValueError("Exact 3.2 source commit required")
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Never overwrite research QA result")
    cores = check_sources(bundle, receipt, sha)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ap32-extended-private-home-") as td:
        home = Path(td)
        probes = [run(name, cores[name], home) for name in TARGETS]
    if (len(probes) != len(TARGETS)
            or [x.get("profile") for x in probes] != list(TARGETS)):
        raise ValueError("Extended native probe did not return all four profiles")
    passed = sum(x.get("native_probe_verified") is True for x in probes)
    result = {
        "schema_version": 1, "status": STATUS,
        "source_revision": sha,
        "installed_binary_checked": "exact-source full-native Linux 3.2 QA install",
        "profiles": list(TARGETS),
        "profiles_attempted": 4,
        "exploratory_profiles_verified": passed,
        "all_four_exploratory_verified": passed == 4,
        "probe_results": probes,
        "original_generated_monochrome_only": True,
        "remaining_three_fixtures_hash_pinned_in_repo": True,
        "fixture_network_only_during_private_CI": True,
        "all_18_consoles_gameplay_verified": False,
        "commercial_game_compatibility_verified": False,
        "physical_camera_tested": False,
        "physical_controller_tested": False,
        "physical_speakers_tested": False,
        "public_release_approved": False,
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", "utf-8")
    print(json.dumps({
        "status": STATUS, "source_revision": sha,
        "profiles_attempted": 4,
        "exploratory_profiles_verified": passed,
        "profile_results": [
            {"profile": x["profile"], "verified": x["native_probe_verified"]}
            for x in probes
        ],
        "public_release_approved": False,
    }, indent=2, sort_keys=True), flush=True)
    # This is optional diagnostic research: a crash or missing upstream
    # fixture is a reported failure, not a job failure or a successful game.
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--source-receipt", type=Path, required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    execute(a.bundle, a.source_receipt, a.source_sha, a.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
