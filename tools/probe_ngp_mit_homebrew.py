"""Strict Neo Geo Pocket / Color native video and audio acceptance, CI-only.

MIT-licensed game/test authors retain rights. The app doesn't distribute or
download these ROMs. One isolated native CoreSession is required to produce
changing nonblank game frames, real PCM and no crash. No emulator API may
synthesize frames or audio to satisfy the gate.
"""
from __future__ import annotations
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ngp_mit_fixtures import FIXTURES, fetch_test_fixture
from tools.probe_nes_homebrew import ObservedAudio


def _native_save_state_roundtrip(native):
    """Exercise core serialize/unserialize on its own emulation thread.

    This is a diagnostic for the CI homebrew, not evidence that the app's
    cartridge SRAM persistence or a retail game's saves are verified.
    """
    evidence = {
        "supported": False, "serialized": False,
        "restored": False, "matching_roundtrip": False,
        "bytes": 0, "error": None,
    }
    try:
        library = native.library
        size_function = getattr(library, "retro_serialize_size", None)
        serialize = getattr(library, "retro_serialize", None)
        unserialize = getattr(library, "retro_unserialize", None)
        if any(function is None for function in
               (size_function, serialize, unserialize)):
            evidence["error"] = "Libretro save-state API not exported"
            return evidence
        size_function.argtypes = []
        size_function.restype = C.c_size_t
        serialize.argtypes = [C.c_void_p, C.c_size_t]
        serialize.restype = C.c_bool
        unserialize.argtypes = [C.c_void_p, C.c_size_t]
        unserialize.restype = C.c_bool
        count = int(size_function())
        evidence["bytes"] = count
        # A compromised core must not allocate an unbounded save-state buffer.
        if not 0 < count <= 64 * 1024 * 1024:
            evidence["error"] = "No save-state support or oversized native state"
            return evidence
        evidence["supported"] = True
        original = C.create_string_buffer(count)
        if not serialize(original, count):
            evidence["error"] = "Core rejected initial save-state snapshot"
            return evidence
        evidence["serialized"] = True
        if not unserialize(original, count):
            evidence["error"] = "Core rejected restore of its own snapshot"
            return evidence
        evidence["restored"] = True
        restored = C.create_string_buffer(count)
        if not serialize(restored, count):
            evidence["error"] = "Core rejected save-state snapshot after restore"
            return evidence
        evidence["matching_roundtrip"] = (
            hashlib.sha256(original.raw).digest()
            == hashlib.sha256(restored.raw).digest()
        )
        if not evidence["matching_roundtrip"]:
            evidence["error"] = "Serialized state changed after immediate restore"
    except Exception as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
    return evidence


def _child(system, core, rom, seconds, report):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from PIL import Image
    from anything_plays.gba_emulator import Emulator, CoreSession
    from anything_plays.libretro_input import IDS
    emulator = Emulator()
    emulator.system = emulator.inputs.system = system
    emulator.core_path = str(core)
    session = CoreSession(emulator, system, rom, str(core))
    session.audio.close()
    session.audio = ObservedAudio()

    # Real input evidence must originate in the native core's Libretro
    # input_state callback, not merely from queued GUI button presses.
    native_input = {
        "queries": 0, "manual_a_positive": 0, "camera_b_positive": 0,
    }
    stimulus_phase = "idle"
    original_input = emulator.inputs.state

    def observe_input(port, device, index, identity):
        value = original_input(port, device, index, identity)
        if port == 0 and device == 1 and index == 0:
            native_input["queries"] += 1
            # Physical NeoPop A maps to RetroPad B; physical B maps to
            # RetroPad A. Verify the actual native callback identifiers.
            if stimulus_phase == "manual" and identity == IDS["B"] and value:
                native_input["manual_a_positive"] += 1
            if stimulus_phase == "camera" and identity == IDS["A"] and value:
                native_input["camera_b_positive"] += 1
        return value

    emulator.inputs.state = observe_input

    # Test Libretro save-state ABI only from the emulator thread, between
    # retro_run calls. This cannot establish actual SRAM persistence.
    save_state = {"attempted": False, "result": None}
    original_before_frame = emulator.inputs.before_frame
    session_started = time.monotonic()

    def before_frame(armed):
        original_before_frame(armed)
        if not save_state["attempted"] and time.monotonic() - session_started > 2:
            save_state["attempted"] = True
            save_state["result"] = _native_save_state_roundtrip(session.native)

    emulator.inputs.before_frame = before_frame

    def exercise_controls():
        nonlocal stimulus_phase
        # A is held manually while camera control is disarmed. B is then
        # triggered as a finite camera pulse while armed, repeatedly.
        # The emulated core must actually poll both nonzero buttons.
        deadline = time.monotonic() + seconds - 0.25
        while not emulator.running and not emulator.stop_event.is_set():
            if time.monotonic() >= deadline:
                return
            emulator.stop_event.wait(0.01)
        try:
            while not emulator.stop_event.is_set() and time.monotonic() < deadline:
                emulator.armed = False
                stimulus_phase = "manual"
                emulator.set_manual("A", True)
                if emulator.stop_event.wait(0.16):
                    break
                emulator.set_manual("A", False)
                emulator.armed = True
                stimulus_phase = "camera"
                emulator.press("B", frames=14)
                if emulator.stop_event.wait(0.16):
                    break
        finally:
            stimulus_phase = "idle"
            emulator.release_manual()
            emulator.armed = False

    stimulus = threading.Thread(
        target=exercise_controls, daemon=True, name="ngp-ci-input"
    )

    original_video = session.video
    callbacks = nonblank = 0
    hashes = set()
    all_hashes = set()
    rgb_bounds = [255, 0]
    first_shape = None
    def observe_video(pointer, width, height, pitch):
        nonlocal callbacks, nonblank, first_shape
        before = emulator.frame_serial
        original_video(pointer, width, height, pitch)
        if emulator.frame_serial == before:
            return
        callbacks += 1
        if callbacks > 90 and callbacks % 11 != 1:
            return
        with emulator.lock:
            frame = emulator.frame
            if frame is None:
                return
            low, high = int(frame.min()), int(frame.max())
            rgb_bounds[0] = min(low, rgb_bounds[0])
            rgb_bounds[1] = max(high, rgb_bounds[1])
            digest = hashlib.sha256(frame.tobytes()).hexdigest()[:16]
            all_hashes.add(digest)
            if first_shape is None:
                first_shape = list(frame.shape)
                Image.fromarray(frame).save(
                    report.with_name(system + "-first-frame.png")
                )
            if high > 8 and low != high:
                nonblank += 1
                hashes.add(digest)
    session.video = observe_video
    timer = threading.Timer(seconds, emulator.stop_event.set)
    timer.daemon = True
    timer.start()
    start = time.monotonic()
    exception = None
    try:
        stimulus.start()
        session.run()
    except Exception as exc:
        exception = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        emulator.stop_event.set()
        timer.cancel()
        stimulus.join(timeout=1)
    elapsed = max(0.001, time.monotonic() - start)
    pcm = session.audio
    video_ok = (
        callbacks >= 30 and callbacks / elapsed >= 20
        and nonblank >= 3 and len(hashes) >= 2
    )
    audio_ok = (
        pcm.samples > 1000 and pcm.nonzero > 100 and pcm.peak > 0
        and 8000 <= (pcm.sample_rate or 0) <= 192000
    )
    # NeoPop writes cartridge flash during retro_unload_game(), not
    # through RETRO_MEMORY_SAVE_RAM. Observe only after session.run()
    # finishes and the native core has been unloaded. A homebrew demo
    # that creates no flash is not proof that retail saves work.
    flash_folder = Path(os.fsdecode(session._save_dir_buffer.value))
    flash_artifacts = []
    if flash_folder.is_dir():
        for candidate in sorted(flash_folder.glob("*.flash"))[:16]:
            if not candidate.is_file() or candidate.is_symlink():
                continue
            size = candidate.stat().st_size
            flash_artifacts.append({
                "name": candidate.name, "bytes": size,
                "sha256": (
                    hashlib.sha256(candidate.read_bytes()).hexdigest()
                    if 0 <= size <= 8 * 1024 * 1024 else None
                ),
            })
    input_ok = (
        native_input["queries"] >= 30
        and native_input["manual_a_positive"] > 0
        and native_input["camera_b_positive"] > 0
    )
    passed = exception is None and video_ok and audio_ok and input_ok
    evidence = {
        "system": system,
        "source": "pinned MIT homebrew, no proprietary game",
        "native_video_frames": callbacks,
        "observed_fps": round(callbacks / elapsed, 2),
        "sampled_nonblank_frames": nonblank,
        "distinct_nonblank_frames": len(hashes),
        "distinct_all_frames": len(all_hashes),
        "frame_shape": first_shape,
        "rgb_min_max": rgb_bounds,
        "native_audio_frames": pcm.samples,
        "native_nonzero_pcm_values": pcm.nonzero,
        "native_audio_peak": pcm.peak,
        "sample_rate": pcm.sample_rate,
        "video_gate_passed": video_ok,
        "audio_gate_passed": audio_ok,
        "native_input_callback_queries": native_input["queries"],
        "manual_a_native_positive_samples": native_input["manual_a_positive"],
        "camera_b_native_positive_samples": native_input["camera_b_positive"],
        "input_gate_passed": input_ok,
        "save_state_roundtrip": save_state["result"],
        "native_flash_files_after_core_unload": flash_artifacts,
        "native_flash_save_directory_exists": flash_folder.is_dir(),
        "cartridge_flash_roundtrip_verified": False,
        "cartridge_sram_persistence_verified": False,
        "physical_speakers_verified": False,
        "real_user_game_compatibility_verified": False,
        "passed": passed, "error": exception,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(evidence, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2), flush=True)
    return 0 if passed else 1


def _parent(system, core, report, seconds):
    outcome = {
        "system": system, "passed": False, "native_exit_code": None,
        "timed_out": False, "fixture": None, "details": None, "error": None,
    }
    try:
        if not core.is_file():
            raise FileNotFoundError("Missing embedded Mednafen NeoPop core")
        with tempfile.TemporaryDirectory(prefix="ap-v30-ngp-ci-") as tmp:
            root = Path(tmp)
            rom = root / ("pinned-mit-test" + FIXTURES[system]["ext"])
            outcome["fixture"] = fetch_test_fixture(system, rom)
            child_report = root / "child-result.json"
            env = os.environ.copy()
            env["HOME"] = str(root)
            env["USERPROFILE"] = str(root)
            env["APPDATA"] = str(root / "roaming")
            env["LOCALAPPDATA"] = str(root / "local")
            env["XDG_CONFIG_HOME"] = str(root / "config")
            env["XDG_DATA_HOME"] = str(root / "user-data")
            command = [
                sys.executable, str(Path(__file__).resolve()), "--child",
                "--system", system, "--core", str(core), "--rom", str(rom),
                "--seconds", str(seconds), "--report", str(child_report),
            ]
            try:
                worker = subprocess.run(
                    command, capture_output=True, text=True, check=False,
                    timeout=seconds + 30, env=env,
                )
                outcome["native_exit_code"] = worker.returncode
                outcome["console_tail"] = (worker.stdout + worker.stderr)[-14000:]
            except subprocess.TimeoutExpired as exc:
                outcome["timed_out"] = True
                raw = exc.stdout or b""
                outcome["console_tail"] = (
                    raw.decode("utf-8", "replace") if isinstance(raw, bytes)
                    else raw
                )[-14000:]
            if child_report.is_file():
                outcome["details"] = json.loads(
                    child_report.read_text(encoding="utf-8")
                )
            frame = child_report.with_name(system + "-first-frame.png")
            if frame.is_file():
                report.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(frame, report.with_name(frame.name))
            outcome["passed"] = (
                outcome["native_exit_code"] == 0
                and isinstance(outcome["details"], dict)
                and outcome["details"].get("passed") is True
                # A .ngp extension is insufficient: the previous pinned
                # upstream .ngp fixture declares 0x10 COLOR in header[0x23].
                # Native sound/video/input from a color-header cartridge
                # must never satisfy MONO console release acceptance.
                and outcome["fixture"].get("header_matches_test_target") is True
            )
    except Exception as exc:
        outcome["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(outcome, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(outcome, indent=2), flush=True)
    return 0 if outcome["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", choices=tuple(FIXTURES), required=True)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--seconds", type=int, default=12)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if not 2 <= args.seconds <= 60:
        parser.error("--seconds must be 2..60")
    if args.child:
        if args.rom is None:
            parser.error("--child requires --rom")
        return _child(
            args.system, args.core.resolve(), args.rom.resolve(),
            args.seconds, args.report.resolve(),
        )
    return _parent(
        args.system, args.core.resolve(), args.report.resolve(), args.seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
