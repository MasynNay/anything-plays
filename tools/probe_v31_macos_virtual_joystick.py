"""Read-only native SDL virtual-joystick roundtrip on the signed Mac RC1.

Use immutable inspected SDL dylibs inside the original mounted DMG.
The SDL virtual joystick API exercises native attach/press/release/detach
without claiming any physical USB/Bluetooth controller was tested.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from tools.probe_v31_macos_sdl_load import select_libs, EXPECTED

# SDL_JOYSTICK_TYPE_GAMECONTROLLER=1 from SDL 2.32.10 SDL_joystick.h.
# 6 axes, 15 face/menu/dpad buttons and one hat are conventional defaults.
_NATIVE_PROBE = r'''
import ctypes as C
import json
import sys
FLAGS = 0x00000200 | 0x00002000
out = []
for path in sys.argv[1:]:
    lib = C.CDLL(path)
    def entry(name, result, *args):
        fn = getattr(lib, name)
        fn.restype = result
        fn.argtypes = list(args)
        return fn
    init = entry("SDL_InitSubSystem", C.c_int, C.c_uint32)
    quit_sub = entry("SDL_QuitSubSystem", None, C.c_uint32)
    get_version = entry("SDL_GetVersion", None, C.c_void_p)
    num = entry("SDL_NumJoysticks", C.c_int)
    attach = entry("SDL_JoystickAttachVirtual", C.c_int,
                   C.c_int, C.c_int, C.c_int, C.c_int)
    is_virtual = entry("SDL_JoystickIsVirtual", C.c_int, C.c_int)
    open_joy = entry("SDL_JoystickOpen", C.c_void_p, C.c_int)
    set_button = entry("SDL_JoystickSetVirtualButton", C.c_int,
                       C.c_void_p, C.c_int, C.c_uint8)
    update = entry("SDL_JoystickUpdate", None)
    get_button = entry("SDL_JoystickGetButton", C.c_uint8,
                       C.c_void_p, C.c_int)
    close = entry("SDL_JoystickClose", None, C.c_void_p)
    detach = entry("SDL_JoystickDetachVirtual", C.c_int, C.c_int)
    class Version(C.Structure):
        _fields_ = [("major",C.c_uint8),("minor",C.c_uint8),("patch",C.c_uint8)]
    ver=Version()
    get_version(C.byref(ver))
    if init(FLAGS) != 0:
        raise RuntimeError("SDL joystick+controller subsystem did not initialize")
    handle = None
    index = -1
    try:
        previous = num()
        if previous < 0:
            raise RuntimeError("SDL cannot enumerate native devices")
        index = attach(1, 6, 15, 1)
        if index < 0 or not is_virtual(index):
            raise RuntimeError("Virtual game controller attach failed")
        if num() != previous + 1:
            raise RuntimeError("SDL virtual joystick was not enumerated")
        handle = open_joy(index)
        if not handle:
            raise RuntimeError("SDL cannot open its own virtual controller")
        if set_button(handle, 0, 1) != 0:
            raise RuntimeError("Native virtual button press rejected")
        update()
        pressed = int(get_button(handle, 0))
        if set_button(handle, 0, 0) != 0:
            raise RuntimeError("Native virtual button release rejected")
        update()
        released = int(get_button(handle, 0))
        if pressed != 1 or released != 0:
            raise RuntimeError(f"SDL button roundtrip returned {pressed},{released}")
    finally:
        if handle:
            close(handle)
        if index >= 0:
            if detach(index) != 0:
                raise RuntimeError("SDL virtual controller detach rejected")
        restored = num()
        quit_sub(FLAGS)
        if restored != previous:
            raise RuntimeError("SDL leaked a virtual joystick after detach")
    out.append({
        "path": path,
        "runtime_version": f"{ver.major}.{ver.minor}.{ver.patch}",
        "virtual_joystick_added": True,
        "native_button_press_read": pressed,
        "native_button_release_read": released,
        "virtual_joystick_removed": True,
        "real_hid_hardware_tested": False,
    })
print(json.dumps(out))
'''


def evaluate_results(target, selected, process_output):
    """Fail closed on missing button changes, versions, or hardware claims."""
    records=[]
    for order in (list(selected), list(reversed(list(selected)))):
        if len(selected)==1 and records:
            break
        result=process_output(order)
        valid=(isinstance(result,list) and len(result)==len(order))
        if valid:
            for slot,record in zip(order,result):
                valid=valid and (
                    isinstance(record,dict)
                    and record.get("path")==selected[slot]["path"]
                    and record.get("runtime_version")==selected[slot]["expected_runtime_version"]
                    and record.get("virtual_joystick_added") is True
                    and record.get("native_button_press_read")==1
                    and record.get("native_button_release_read")==0
                    and record.get("virtual_joystick_removed") is True
                    and record.get("real_hid_hardware_tested") is False
                )
        records.append({
            "load_order": order,
            "passed_native_roundtrip": bool(valid),
            "observations": result,
        })
    return {
        "schema_version":1,
        "status":"UNRELEASED_3_1_SIGNED_MAC_SDL_VIRTUAL_JOYSTICK_EVIDENCE",
        "target":target,
        "signed_library_sources":selected,
        "native_button_roundtrips":records,
        "passed":all(r["passed_native_roundtrip"] for r in records),
        "physical_gamepad_verified":False,
        "camera_capture_verified":False,
        "real_gameplay_verified":False,
        "corresponding_source_complete":False,
        "lgpl_relinking_reviewed":False,
        "redistribution_approved":False,
    }


def probe(app, report, target, runner=subprocess.run):
    selected=select_libs(app,report,target)
    def output(order):
        paths=[selected[slot]["path"] for slot in order]
        try:
            env=os.environ.copy()
            env.setdefault("SDL_VIDEODRIVER","dummy")
            env.setdefault("SDL_AUDIODRIVER","dummy")
            process=runner([sys.executable,"-c",_NATIVE_PROBE,*paths],
                           capture_output=True,text=True,timeout=45,env=env)
            if process.returncode != 0:
                print("Native joystick probe failed:",
                      process.stderr[-1500:],file=sys.stderr)
                return []
            return json.loads(process.stdout)
        except (ValueError,subprocess.TimeoutExpired,OSError) as exc:
            print("Native joystick probe error:",str(exc)[:700],file=sys.stderr)
            return []
    return evaluate_results(target,selected,output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle",type=Path,required=True)
    parser.add_argument("--linkage",type=Path,required=True)
    parser.add_argument("--target",choices=sorted(EXPECTED),required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=probe(args.bundle,json.loads(args.linkage.read_text("utf-8")),args.target)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n","utf-8")
    for item in result["native_button_roundtrips"]:
        print(args.target,"SDL library order:",item["load_order"],
              "virtual button press/release:",item["passed_native_roundtrip"])
    print("Physical gamepad/camera/gameplay acceptance and source rights: NOT VERIFIED")
    if not result["passed"]:
        raise SystemExit(1)


if __name__=="__main__":
    main()
