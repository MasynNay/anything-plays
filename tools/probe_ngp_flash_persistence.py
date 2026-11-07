"""Experimental real Neo Geo Pocket Color flash-save restart acceptance.

Uses the MIT-licensed, immutable StarGunner demo (the same fixture pinned
for native NGP/NGPC A/V CI). Its Options menu persists the 'CONTINUES' value
through actual NGPC cartridge flash. The three sessions run in separate
subprocesses with the SAME ROM and user-owned save directory:
1. Baseline, no modifications.
2. Increase CONTINUES through in-game controls and exit Options to save.
3. Cold reboot, do not modify options, inspect the loaded number.

Never bundle the fixture, copy ROMs into release artifacts, or report the
physical-hardware compatibility of commercial games from this lab.
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
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ngp_mit_fixtures import fetch_test_fixture

# Frame-indexed *physical* NGPC buttons using the production InputBuffer.
# Screen shows CONTINUES (two digits) at x=15 tiles, y=6 tiles, 8x8 each.
# A skips intro, Down selects Options, A enters, Right increments, B exits.
COMMON_SEQUENCE = ((55, "A"), (100, "Down"), (145, "A"))
MODIFY_SEQUENCE = ((230, "Right"), (305, "B"))
ROI = (120, 48, 136, 56)
SNAPSHOT_FRAME = 275
STOP_FRAME = 410


def _flash_entries(folder):
    result = []
    if not folder.is_dir():
        return result
    for item in sorted(folder.glob("*.flash"))[:16]:
        if item.is_symlink() or not item.is_file():
            continue
        size = item.stat().st_size
        result.append({
            "name": item.name,
            "bytes": size,
            "sha256": (
                hashlib.sha256(item.read_bytes()).hexdigest()
                if 0 < size <= 8 * 1024 * 1024 else None
            ),
        })
    return result


def child(phase, core, rom, report, timeout, mode="flash"):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from anything_plays.gba_emulator import CoreSession, Emulator
    from tools.probe_nes_homebrew import ObservedAudio

    emulator = Emulator()
    emulator.system = emulator.inputs.system = "ngpc"
    emulator.core_path = str(core)
    session = CoreSession(emulator, "ngpc", rom, str(core))
    # Prove raw cartridge flash without allowing the new last-session
    # recovery layer to conceal a native core flash-load failure.
    if mode == "flash":
        session.enable_state_resume = False
    session.audio.close()
    session.audio = ObservedAudio()

    # A fresh session and a real cartridge are mandatory. Do not synthesize
    # any images, state, or battery backup data for this experiment.
    if mode == "state":
        # State experiment: stop while Options is still visible, never exit
        # the menu to flush cartridge flash. The following fresh process
        # must recover the changed screen from an actual native save-state.
        sequence = (
            COMMON_SEQUENCE + ((230, "Right"),)
            if phase == "modified" else ()
        )
        snapshot_after = 255 if phase == "modified" else 25
        stop_after = 285 if phase == "modified" else 100
    else:
        sequence = COMMON_SEQUENCE + (
            MODIFY_SEQUENCE if phase == "modified" else ()
        )
        snapshot_after = SNAPSHOT_FRAME
        stop_after = STOP_FRAME
    input_actions = {
        number: (button, True) for number, button in sequence
    }
    input_actions.update({
        number + 7: (button, False) for number, button in sequence
    })

    count = 0
    snapshot = None
    snapshot_shape = None
    frames = 0
    native_poll_count = 0
    nonzero_poll_count = 0

    original_before = emulator.inputs.before_frame
    original_video = session.video
    original_state = emulator.inputs.state

    def sample_state(port, device, index, identity):
        nonlocal native_poll_count, nonzero_poll_count
        value = original_state(port, device, index, identity)
        native_poll_count += 1
        nonzero_poll_count += int(value != 0)
        return value

    def before_frame(armed):
        nonlocal count
        count += 1
        action = input_actions.get(count)
        if action:
            emulator.set_manual(*action)
        # Camera is deliberately disarmed, manual input must still function.
        original_before(False)
        if count >= stop_after:
            emulator.stop_event.set()

    def observe_video(pointer, width, height, pitch):
        nonlocal snapshot, snapshot_shape, frames
        previous = emulator.frame_serial
        original_video(pointer, width, height, pitch)
        if emulator.frame_serial == previous:
            return
        frames += 1
        if count >= snapshot_after and snapshot is None:
            with emulator.lock:
                picture = emulator.frame
                if picture is None:
                    return
                x0, y0, x1, y1 = ROI
                if picture.shape[0] < y1 or picture.shape[1] < x1:
                    return
                cropped = picture[y0:y1, x0:x1, :3].copy()
                snapshot = hashlib.sha256(cropped.tobytes()).hexdigest()
                snapshot_shape = list(cropped.shape)

    emulator.inputs.state = sample_state
    emulator.inputs.before_frame = before_frame
    session.video = observe_video
    timer = threading.Timer(timeout, emulator.stop_event.set)
    timer.daemon = True
    timer.start()
    error = None
    elapsed_start = time.monotonic()
    try:
        session.run()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        emulator.stop_event.set()
        timer.cancel()
        emulator.release_manual()

    save_dir = Path(os.fsdecode(session._save_dir_buffer.value))
    data = {
        "phase": phase,
        "mode": mode,
        "success": error is None and count >= stop_after and snapshot is not None,
        "elapsed_seconds": round(time.monotonic() - elapsed_start, 2),
        "emulated_frames": count,
        "actual_video_callbacks": frames,
        "sampled_number_roi": list(ROI),
        "number_rgb_shape": snapshot_shape,
        "number_roi_sha256": snapshot,
        "native_input_polls": native_poll_count,
        "native_nonzero_input_polls": nonzero_poll_count,
        "real_pcm_nonzero_values": session.audio.nonzero,
        "flash_files_after_unload": _flash_entries(save_dir),
        "native_state_resume_applied": bool(emulator.resume_info),
        "checkpoint_file_created": bool(
            session.recovery_state is not None
            and session.recovery_state.path.is_file()
        ),
        "error": error,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data, indent=2), flush=True)
    return 0 if data["success"] else 1


def parent(core, report, timeout, mode="flash"):
    outcome = {
        "passed": False, "experiment": (
            "actual StarGunner native-state cold-resume"
            if mode == "state" else "actual StarGunner cartridge flash"
        ),
        "source": "immutable MIT-licensed CI-only homebrew",
        "phases": {}, "fixture": None, "error": None,
        "physical_device_save_tested": False,
        "commercial_rom_compatibility_tested": False,
    }
    try:
        if not core.is_file():
            raise FileNotFoundError("No native Mednafen NeoPop Libretro core")
        with tempfile.TemporaryDirectory(prefix="ap-v30-ngpc-flash-") as tmp:
            root = Path(tmp)
            rom = root / "StarGunner.ngc"
            outcome["fixture"] = fetch_test_fixture("ngpc", rom)
            env = os.environ.copy()
            # Preserve one portable save root across all THREE separate core
            # processes while never touching a GitHub runner's real profile.
            env.update({
                "HOME": str(root / "home"),
                "USERPROFILE": str(root / "home"),
                "APPDATA": str(root / "roaming"),
                "LOCALAPPDATA": str(root / "local"),
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_DATA_HOME": str(root / "user-data"),
            })
            (root / "home").mkdir()
            phases = (
                ("modified", "restored") if mode == "state"
                else ("baseline", "modified", "restored")
            )
            for phase in phases:
                phase_report = root / (phase + ".json")
                command = [
                    sys.executable, str(Path(__file__).resolve()),
                    "--child", "--phase", phase, "--mode", mode,
                    "--core", str(core), "--rom", str(rom),
                    "--report", str(phase_report),
                    "--seconds", str(timeout),
                ]
                try:
                    completed = subprocess.run(
                        command, env=env, check=False, capture_output=True,
                        text=True, timeout=timeout + 30,
                    )
                    output = (completed.stdout + completed.stderr)[-9000:]
                    exit_code = completed.returncode
                except subprocess.TimeoutExpired as exc:
                    output = str(exc)
                    exit_code = -1
                details = (
                    json.loads(phase_report.read_text(encoding="utf-8"))
                    if phase_report.is_file() else None
                )
                outcome["phases"][phase] = {
                    "exit_code": exit_code, "details": details,
                    "log_tail": output,
                }
                if exit_code != 0 or not details or not details["success"]:
                    raise RuntimeError(f"Native {mode} phase {phase} failed")

            changed = outcome["phases"]["modified"]["details"]
            restored = outcome["phases"]["restored"]["details"]
            if mode == "state":
                # A new Libretro process must receive the previous in-game
                # state: raw flash is deliberately never written here.
                outcome["actual_state_resume_applied"] = (
                    restored["native_state_resume_applied"]
                    and changed["checkpoint_file_created"]
                    and restored["checkpoint_file_created"]
                )
                outcome["native_options_number_restored"] = (
                    changed["number_roi_sha256"]
                    == restored["number_roi_sha256"]
                )
                outcome["flash_was_not_used_to_restore"] = (
                    not changed["flash_files_after_unload"]
                    and not restored["flash_files_after_unload"]
                )
                outcome["passed"] = (
                    outcome["actual_state_resume_applied"]
                    and outcome["native_options_number_restored"]
                    and outcome["flash_was_not_used_to_restore"]
                    and changed["native_nonzero_input_polls"] > 0
                    and restored["native_input_polls"] > 100
                )
            else:
                baseline = outcome["phases"]["baseline"]["details"]
                # Nonzero input and a modified number must be real pixel evidence.
                visual_change = (
                baseline["number_roi_sha256"] != changed["number_roi_sha256"]
                and changed["number_roi_sha256"] == restored["number_roi_sha256"]
            )
                prior_flash = changed["flash_files_after_unload"]
                restored_flash = restored["flash_files_after_unload"]
                flash_exists = (
                    bool(prior_flash)
                    and any(x["bytes"] > 0 and x["sha256"] is not None
                            for x in prior_flash)
                    and prior_flash == restored_flash
                )
                outcome["actual_options_pixel_change_verified"] = visual_change
                outcome["actual_flash_file_survives_relaunch"] = flash_exists
                outcome["passed"] = (
                    visual_change and flash_exists
                    and changed["native_nonzero_input_polls"] > 0
                    and restored["native_input_polls"] > 100
                )
    except Exception as exc:
        outcome["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(outcome, indent=2), flush=True)
    return 0 if outcome["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=12)
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--phase", choices=("baseline", "modified", "restored"))
    parser.add_argument("--mode", choices=("flash", "state"), default="flash")
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if not 8 <= args.seconds <= 35:
        parser.error("Session timeout must be 8–35 seconds")
    if args.child:
        if args.rom is None or args.phase is None:
            parser.error("Child requires --rom and --phase")
        return child(args.phase, args.core.resolve(), args.rom.resolve(),
                     args.report.resolve(), args.seconds, mode=args.mode)
    return parent(args.core.resolve(), args.report.resolve(), args.seconds,
                  mode=args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
