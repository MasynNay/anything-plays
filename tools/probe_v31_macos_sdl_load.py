"""Test actual native SDL2 dynamic loading from readonly full 3.1 Mac RC1 DMG.

Inspect the existing signed-linkage report, authenticate each load candidate
to its exact audited SHA-256, then ask dyld to open both SDL2 versions in
one subprocess, in both orders. No camera/USB/gamepad or game is required.

Passing only proves this narrow ctypes/SDL_GetVersion native load probe.
It is NOT proof of real hardware coexistence or LGPL compliance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SOURCE_COMMIT = "26de1e1ad1b701d0735e085158347f8c213ce437"
EXPECTED = {"macos-arm64": {"cv2": "2.32.8", "pygame": "2.32.10"},
            "macos-x64": {"pygame": "2.32.10"}}
PYTHON_PROBE = r'''
import ctypes as C
import json
import sys
class SDLVersion(C.Structure):
    _fields_ = [("major", C.c_uint8), ("minor", C.c_uint8), ("patch", C.c_uint8)]
out=[]
loaded=[]
SDL_INIT_JOYSTICK=0x00000200
SDL_INIT_GAMECONTROLLER=0x00002000
flags=SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER
for path in sys.argv[1:]:
    lib=C.CDLL(path)
    func=lib.SDL_GetVersion
    func.argtypes=[C.POINTER(SDLVersion)]
    func.restype=None
    info=SDLVersion()
    func(C.byref(info))
    lib.SDL_InitSubSystem.argtypes=[C.c_uint32]
    lib.SDL_InitSubSystem.restype=C.c_int
    lib.SDL_NumJoysticks.argtypes=[]
    lib.SDL_NumJoysticks.restype=C.c_int
    lib.SDL_GetError.argtypes=[]
    lib.SDL_GetError.restype=C.c_char_p
    init_rc=lib.SDL_InitSubSystem(flags)
    if init_rc != 0:
        error=lib.SDL_GetError()
        raise RuntimeError(f"Cannot initialize SDL joystick/controller: {error!r}")
    count=lib.SDL_NumJoysticks()
    if count < 0:
        raise RuntimeError("SDL_NumJoysticks reported an error")
    loaded.append(lib)
    out.append({"path": path, "runtime_version":
                f"{info.major}.{info.minor}.{info.patch}",
                "joystick_controller_initialized": True,
                "enumerated_joystick_count": count})
for lib in reversed(loaded):
    lib.SDL_QuitSubSystem.argtypes=[C.c_uint32]
    lib.SDL_QuitSubSystem(flags)
print(json.dumps(out))
'''


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def select_libs(app, linkage, target):
    if target not in EXPECTED:
        raise ValueError("Unreviewed macOS SDL loader target")
    if (linkage.get("target") != target
            or linkage.get("status") != "UNRELEASED_3_1_MACOS_NATIVE_LINKAGE_REVIEW"
            or linkage.get("source_app_commit") != SOURCE_COMMIT
            or linkage.get("redistribution_approved") is not False):
        raise ValueError("Wrong or approved original signed Mac audit")
    app=Path(app)
    if not app.is_dir() or app.is_symlink():
        raise ValueError("No real mounted app")
    root=app.resolve()
    inventory=linkage.get("native_files")
    if not isinstance(inventory, list) or len(inventory) < 100:
        raise ValueError("Incomplete final native library report")
    matched={}
    for ent in inventory:
        path=ent.get("path") if isinstance(ent, dict) else None
        if (not isinstance(path,str) or path.startswith("/") or
                ".." in path.split("/") or "\\" in path):
            raise ValueError("Bad original native path")
        if not path.endswith("/libSDL2-2.0.0.dylib"):
            continue
        if "/pygame/__dot__dylibs/" in path:
            slot="pygame"
        elif "/cv2/__dot__dylibs/" in path:
            slot="cv2"
        else:
            continue
        absolute=(app/path).resolve(strict=True)
        if not absolute.is_file() or not absolute.is_relative_to(root):
            raise ValueError("SDL library escapes original mounted RC app")
        if sha256(absolute) != ent.get("sha256"):
            raise ValueError("Actual signed SDL bytes changed")
        current_version=ent.get("otool_dependencies", [{}])[0].get("current_version")
        reviewed = "3201.8.0" if slot=="cv2" else "3201.10.0"
        if current_version != reviewed:
            raise ValueError("SDL original Mach-O version changed")
        if slot in matched:
            raise ValueError("Duplicate source of target SDL slot")
        matched[slot]={"path": str(absolute), "audited_sha256": ent["sha256"],
                       "expected_runtime_version": EXPECTED[target].get(slot)}
    if set(matched) != set(EXPECTED[target]):
        raise ValueError("Original signed RC dylib variants missing")
    return matched


def run_load_order(paths, runner=subprocess.run):
    if not paths:
        raise ValueError("SDL load sequence cannot be empty")
    try:
        proc=runner([sys.executable, "-c", PYTHON_PROBE, *paths],
                    capture_output=True, text=True, check=False, timeout=30)
        parsed=json.loads(proc.stdout) if proc.returncode==0 else []
    except (subprocess.TimeoutExpired, ValueError) as error:
        return {"passed": False, "native_load_error": str(error)[:1000],
                "loaded": []}
    if not isinstance(parsed, list) or len(parsed)!=len(paths):
        return {"passed": False,
                "native_load_error": (proc.stderr or "Unstructured native SDL output")[-1000:],
                "loaded": []}
    return {"passed": True, "loaded": parsed, "native_load_error": None}


def probe(app, linkage, target, runner=subprocess.run):
    selected=select_libs(app, linkage, target)
    orders=[list(selected)] if len(selected)==1 else [
        list(selected), list(reversed(list(selected)))
    ]
    records=[]
    for order in orders:
        files=[selected[slot]["path"] for slot in order]
        result=run_load_order(files,runner)
        # The process could load a different dylib for the same install name:
        # treat that as a detected mismatch, not a successful coexistence test.
        valid = result["passed"] and all(
            ent.get("path")==selected[slot]["path"] and
            ent.get("runtime_version")==selected[slot]["expected_runtime_version"]
            and ent.get("joystick_controller_initialized") is True
            and isinstance(ent.get("enumerated_joystick_count"), int)
            and ent["enumerated_joystick_count"] >= 0
            for ent,slot in zip(result["loaded"],order)
        )
        records.append({"order":order, "reported":result["loaded"],
                        "probe_executed":result["passed"],
                        "both_runtime_versions_match_expected":valid,
                        "error":result["native_load_error"]})
    return {
        "schema_version":1,
        "status":"UNRELEASED_3_1_SIGNED_MACOS_SDL2_DYNAMIC_LOAD_EVIDENCE",
        "target":target,
        "selected_signed_libraries":selected,
        "load_orders":records,
        "all_native_load_orders_passed":all(x["both_runtime_versions_match_expected"]
                                            for x in records),
        "real_camera_controller_coexistence_tested":False,
        "hardware_free_joystick_and_controller_subsystems_exercised":True,
        "commercial_gameplay_tested":False,
        "original_source_correspondence_verified":False,
        "lgpl_relinking_reviewed":False,
        "redistribution_approved":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle",type=Path,required=True)
    p.add_argument("--linkage",type=Path,required=True)
    p.add_argument("--target",choices=sorted(EXPECTED),required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=probe(args.bundle,json.loads(args.linkage.read_text("utf-8")),args.target)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n","utf-8")
    for entry in result["load_orders"]:
        print(args.target, "load order",entry["order"],
              "version matched",entry["both_runtime_versions_match_expected"],
              "error",entry["error"])
    print("SDL2 native loading + hardware-free joystick/controller initialization only; "
          "camera/gameplay, original source and LGPL approval stay false.")
    # A recorded native-load mismatch is a real test failure, but retain
    # the diagnostic JSON in CI for analysis.
    if not result["all_native_load_orders_passed"]:
        raise SystemExit(1)


if __name__=="__main__":
    main()
