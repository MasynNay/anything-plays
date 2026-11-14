"""Private 3.2 GameCube native SOUND research using ORIGINAL source-built DOL.

The existing pinned zlib controller program is silent by design. Measuring
zero nonzero PCM from that program does not diagnose Dolphin's DSP output.
Build the repository's original GX + ASND tone generator with devkitPPC in
an isolated offline Docker build, then run it through the same frozen-app
Dolphin native core and actual production GameCubeHardwareSession.

This optional research is NOT a commercial-game test, speaker test, public
permission, or a hard 3.2 release gate. Never retain DOL, screenshots,
Docker logs, subprocess logs, ROM paths, user identifiers or error traces.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from tools.v32_extended_native_runtime import check_sources

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/gamecube-3d-homebrew"
DOL_NAME = "anythingplays-gc-gx-gamecube.dol"
FIXTURE_PROGRAMS = {
    "gx3d": (SOURCE, DOL_NAME),
    "console_av": (
        ROOT / "tools/gamecube-av-homebrew",
        "anythingplays-gc-av-gamecube.dol",
    ),
}
STATUS = "PRIVATE_V32_ORIGINAL_GC_AUDIO_AND_GPU_RESEARCH_NOT_RELEASE"
BUILD_LIMIT = 300
PROBE_LIMIT = 140


def digest(file):
    h = hashlib.sha256()
    with Path(file).open("rb") as fp:
        for part in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def check_source_program(kind="gx3d"):
    """Verify source-authored ASND tone and video before any compiler run."""
    if kind not in FIXTURE_PROGRAMS:
        raise ValueError("Unrecognized owned GameCube audio program")
    folder, _ = FIXTURE_PROGRAMS[kind]
    main = folder/"source/main.c"
    make = folder/"Makefile"
    if any(not f.is_file() or f.is_symlink() for f in (main, make)):
        raise ValueError("Original GameCube AV source missing or symlinked")
    src = main.read_text("utf-8")
    options = make.read_text("utf-8")
    essentials = ("#include <asndlib.h>", "ASND_Init();",
                  "ASND_SetInfiniteVoice(", "ASND_Pause(0);")
    video_and_tone = (
        ("DCFlushRange(audio_tone", "GX_Begin(GX_QUADS")
        if kind == "gx3d"
        else ("DCFlushRange(tone", "console_init(", "VIDEO_WaitVSync()")
    )
    for needle in essentials + video_and_tone:
        if needle not in src:
            raise ValueError("Original GameCube source AV code missing: " + needle)
    if "-lasnd" not in options:
        raise ValueError("Original GX/ASND linker rule missing")
    return {"main_c_sha256": digest(main), "makefile_sha256": digest(make)}


def evaluate_evidence(raw, child_exit, dol_digest, source_sha, built,
                      reason=None, *, source_kind="gx3d"):
    """Retain only bounded numeric native A/V facts, no raw subprocess data."""
    raw = raw if isinstance(raw, dict) else {}
    details = raw.get("details") if isinstance(raw.get("details"), dict) else {}
    native_exit = raw.get("native_exit_code")
    rendered = (
        child_exit == 0 and raw.get("passed") is True
        and type(native_exit) is int and native_exit == 0
        and raw.get("original_av_dol_sha256") == dol_digest
        and raw.get("fixture_sha256") == dol_digest
        and details.get("backend")
        == "production GameCubeHardwareSession + platform GPU host"
        and details.get("passes_in_app_frame_queue") is True
        and type(details.get("gamecube_rgb_callback_frames")) is int
        and details["gamecube_rgb_callback_frames"] >= 12
    )
    pcm = details.get("native_pcm_nonzero_values")
    pcm_samples = details.get("native_pcm_frame_samples")
    audio = (
        rendered and details.get("native_nonzero_pcm_requirement_met") is True
        and type(pcm) is int and pcm >= 200
        and type(pcm_samples) is int and pcm_samples >= 1000
        and type(details.get("native_pcm_sample_rate")) in (float, int)
        and 8000 <= details["native_pcm_sample_rate"] <= 192000
    )
    # A failed *optional* sound test must still explain which stage failed
    # without uploading stdout, ROM paths, native stack traces or personal
    # device names from upstream error strings.
    reason_code = reason
    child_code = raw.get("native_exit_code")
    if not reason_code and not audio:
        if not raw:
            reason_code = "native_parent_report_absent"
        elif raw.get("timed_out") is True:
            reason_code = "native_child_timed_out"
        elif not isinstance(raw.get("details"), dict):
            reason_code = "native_child_details_absent"
        elif type(child_code) is int and child_code != 0:
            reason_code = "native_child_nonzero_exit"
        elif not rendered:
            reason_code = "native_gpu_video_conditions_not_met"
        else:
            reason_code = "nonzero_pcm_conditions_not_met"
    if source_kind not in FIXTURE_PROGRAMS:
        raise ValueError("Original GameCube AV fixture kind not recognized")
    # Only emit a strict allowlist of exception CLASS names, never text
    # containing a path, device label, game title or native backtrace.
    exception = details.get("error")
    if isinstance(exception, str):
        exception = exception.partition(":")[0].strip()
        if exception not in {
            "RuntimeError", "OSError", "ValueError", "MemoryError",
            "FileNotFoundError", "SystemError", "TypeError", "AssertionError",
        }:
            exception = "other_native_exception"
    else:
        exception = None
    result = {
        "schema_version": 1,
        "status": STATUS,
        "source_revision": source_sha,
        "fixture": (
            "original_source_generated_gx_3d_and_asnd_stereo_pcm"
            if source_kind == "gx3d"
            else "original_source_generated_console_video_and_asnd_stereo_pcm"
        ),
        "source_program_kind": source_kind,
        "native_child_exception_class": exception,
        "original_program_compiled_in_private_ci": built,
        "program_sha256": dol_digest if built else None,
        "parent_report_received": bool(raw),
        "native_child_details_received": bool(details),
        "native_child_exit_code": (
            child_code if type(child_code) is int and -255 <= child_code <= 255
            else None
        ),
        "native_subprocess_timed_out": raw.get("timed_out") is True,
        "native_gpu_homebrew_rendering_verified": rendered,
        "core_generated_nonzero_pcm_verified": audio,
        "core_generated_pcm_sample_frames": (
            pcm_samples if type(pcm_samples) is int and 0 <= pcm_samples < 1e9 else 0
        ),
        "core_generated_nonzero_pcm_values": (
            pcm if type(pcm) is int and 0 <= pcm < 1e9 else 0
        ),
        "native_rgb_callback_frames": (
            details.get("gamecube_rgb_callback_frames")
            if type(details.get("gamecube_rgb_callback_frames")) is int
            and 0 <= details["gamecube_rgb_callback_frames"] < 1e8 else 0
        ),
        "headless_20fps_threshold_met": (
            type(details.get("continuous_render_fps")) in (int, float)
            and details["continuous_render_fps"] >= 20
        ),
        "experiment_outcome": (
            "observed_original_tone_pcm" if audio else reason_code
        ),
        "speaker_hardware_tested": False,
        "physical_gamepad_tested": False,
        "physical_camera_tested": False,
        "sustained_gameplay_tested": False,
        "retail_game_compatibility_verified": False,
        "macos_notarized": False,
        "public_release_approved": False,
        "ready_for_release": False,
    }
    return result


def execute(bundle, receipt, sha, report, *, source_kind="gx3d"):
    report = Path(report)
    if report.exists() or report.is_symlink():
        raise ValueError("Cannot overwrite or follow a research report")
    if type(sha) is not str or re.fullmatch(r"[a-f0-9]{40}", sha) is None:
        raise ValueError("Exact 3.2 Git SHA required")
    # No Docker, compiled ROM, or native library is opened before the
    # original 11-core preview identity + native source receipt is checked.
    if source_kind not in FIXTURE_PROGRAMS:
        raise ValueError("Original audio research fixture not recognized")
    core = check_sources(bundle, receipt, sha)["gamecube"]
    source_folder, dol_name = FIXTURE_PROGRAMS[source_kind]
    source_digests = check_source_program(source_kind)
    with tempfile.TemporaryDirectory(prefix="ap32-gc-audio-research-") as td:
        tmp = Path(td)
        # Compile ONLY copies of the repository-owned original source.
        project = tmp/"project"
        shutil.copytree(source_folder, project, ignore=shutil.ignore_patterns(
            "build_*", "*.dol", "*.elf", "*.map"
        ), symlinks=False)
        dol = project/dol_name
        result = {}
        report_path = tmp/"probe.json"
        try:
            uid_args = (
                ["-u", f"{os.getuid()}:{os.getgid()}"]
                if hasattr(os, "getuid") else []
            )
            build = subprocess.run(
                ["docker", "run", "--rm", "--network", "none",
                 "-v", f"{project}:/project", "-w", "/project",
                 "-e", "TARGET_CONSOLE=gamecube",
                 *uid_args, "devkitpro/devkitppc", "make"],
                cwd=ROOT, capture_output=True, text=True,
                check=False, timeout=BUILD_LIMIT,
            )
            if build.returncode or not dol.is_file() or dol.is_symlink():
                result = evaluate_evidence({}, -1, None, sha, False,
                                           "original_source_compiler_unavailable",
                                           source_kind=source_kind)
            elif not 100 <= dol.stat().st_size <= 4 * 1024 * 1024:
                result = evaluate_evidence({}, -1, None, sha, False,
                                           "original_source_binary_invalid",
                                           source_kind=source_kind)
            else:
                sh = digest(dol)
                env = dict(os.environ)
                env.update({
                    "HOME": str(tmp/"home"),
                    "XDG_CONFIG_HOME": str(tmp/"home"/".config"),
                    "SDL_AUDIODRIVER": "dummy",
                    "PYGAME_HIDE_SUPPORT_PROMPT": "1",
                    "AP_V32_PREVIEW": "1",
                })
                (tmp/"home").mkdir()
                executed = subprocess.run(
                    [sys.executable, "-m", "tools.probe_gamecube_app",
                     "--core", str(core), "--rom", str(dol),
                     "--require-audio", "--seconds", "25",
                     "--report", str(report_path)],
                    cwd=ROOT, env=env, capture_output=True,
                    text=True, check=False, timeout=PROBE_LIMIT,
                )
                try:
                    raw = json.loads(report_path.read_text("utf-8"))
                except (OSError, ValueError):
                    raw = {}
                result = evaluate_evidence(
                    raw, executed.returncode, sh, sha, True,
                    source_kind=source_kind,
                )
        except FileNotFoundError:
            result = evaluate_evidence({}, -1, None, sha, False,
                                       "source_compiler_not_installed",
                                       source_kind=source_kind)
        except subprocess.TimeoutExpired:
            result = evaluate_evidence({}, -1, None, sha, False,
                                       "research_compile_or_native_timeout",
                                       source_kind=source_kind)
    result["original_program_source_sha256"] = source_digests
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", "utf-8")
    print(json.dumps({
        "status": result["status"],
        "native_gpu_homebrew_rendering_verified":
            result["native_gpu_homebrew_rendering_verified"],
        "core_generated_nonzero_pcm_verified":
            result["core_generated_nonzero_pcm_verified"],
        "experiment_outcome": result["experiment_outcome"],
        "ready_for_release": False,
    }, indent=2, sort_keys=True))
    # This is separate exploratory research. A missing compiler or failure
    # is visible in the receipt and can NEVER masquerade as sound working.
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--source-receipt", type=Path, required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--source-kind", choices=tuple(FIXTURE_PROGRAMS),
                   default="gx3d")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    execute(a.bundle, a.source_receipt, a.source_sha, a.output,
            source_kind=a.source_kind)


if __name__ == "__main__":
    main()
