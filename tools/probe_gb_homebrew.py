"""Isolated real mGBA Game Boy / Game Boy Color video and audio diagnostic.

Test ROMs are assembled from original instructions at test time; no Nintendo
game, firmware or boot ROM is downloaded or redistributed.
The source-created cartridge includes the standard GB hardware header signature
required by mGBA's ROM detector.
"""
from __future__ import annotations
import argparse
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
from tools.gb_homebrew_fixture import SYSTEMS, write_gb_probe
from tools.probe_nes_homebrew import ObservedAudio

def _child(system, core, rom, report, seconds):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from anything_plays.gba_emulator import Emulator, CoreSession
    from PIL import Image
    emu=Emulator()
    emu.system=system
    emu.inputs.system=system
    emu.core_path=str(core)
    session=CoreSession(emu,system,rom,str(core))
    session.audio.close()
    session.audio=ObservedAudio()
    original=session.video
    frames=0
    nonblank=0
    hashes=set()
    def capture(pointer,width,height,pitch):
        nonlocal frames,nonblank
        prior=emu.frame_serial
        original(pointer,width,height,pitch)
        if emu.frame_serial==prior:
            return
        frames+=1
        if frames>60 and frames%11!=1:
            return
        with emu.lock:
            frame=emu.frame
            if frame is None:
                return
            low,high=int(frame.min()),int(frame.max())
            if high>8 and high!=low:
                nonblank+=1
                hashes.add(hashlib.sha256(frame.tobytes()).hexdigest()[:16])
                if nonblank==1:
                    Image.fromarray(frame).save(report.with_name(f"{system}-frame.png"))
    session.video=capture
    timer=threading.Timer(seconds,emu.stop_event.set)
    timer.daemon=True
    timer.start()
    started=time.monotonic()
    error=None
    try:
        session.run()
    except Exception as exc:
        error=f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        emu.stop_event.set()
        timer.cancel()
    elapsed=max(0.001,time.monotonic()-started)
    sound=session.audio
    passed=(
        error is None and frames>=30 and frames/elapsed>=20
        and nonblank>=2 and len(hashes)>=2
        and sound.samples>1000 and sound.nonzero>100
        and sound.peak>0 and sound.sample_rate is not None
    )
    data={
        "system":system, "source": (
            "original ARM7TDMI GBA ROM" if system == "gba"
            else "original LR35902 GB/GBC ROM"
        ),
        "native_video_frames":frames, "observed_fps":round(frames/elapsed,2),
        "sampled_nonblank_frames":nonblank,
        "distinct_rgb_frames":len(hashes),
        "native_audio_sample_frames":sound.samples,
        "native_nonzero_pcm_samples":sound.nonzero,
        "native_pcm_peak":sound.peak,
        "sample_rate":sound.sample_rate,
        "physical_speakers_verified":False,
        "real_game_compatibility_verified":False,
        "passed":passed, "error":error,
    }
    report.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data,indent=2),flush=True)
    return 0 if passed else 1

def _parent(system,core,report,seconds):
    data={"system":system,"passed":False,"native_exit_code":None,
          "timed_out":False,"details":None,"error":None}
    try:
        if not core.is_file():
            raise FileNotFoundError("Missing native mGBA test core")
        with tempfile.TemporaryDirectory(prefix="anything-plays-gb-original-") as folder:
            root=Path(folder)
            rom=root/("anythingplays-original."+system)
            data["fixture"]=write_gb_probe(rom,system)
            output=root/"child-report.json"
            command=[
                sys.executable,str(Path(__file__).resolve()),"--child",
                "--system",system,"--core",str(core),"--rom",str(rom),
                "--report",str(output),"--seconds",str(seconds),
            ]
            env=os.environ.copy()
            env["HOME"]=str(root)
            env["XDG_CONFIG_HOME"]=str(root/"config")
            try:
                result=subprocess.run(
                    command,capture_output=True,text=True,check=False,
                    env=env,timeout=seconds+22,
                )
                data["native_exit_code"]=result.returncode
                data["console_tail"]=(result.stdout+result.stderr)[-12000:]
            except subprocess.TimeoutExpired as exc:
                data["timed_out"]=True
                raw=exc.stdout or b""
                data["console_tail"]=(raw.decode("utf-8","replace")
                    if isinstance(raw,bytes) else raw)[-12000:]
            if output.is_file():
                data["details"]=json.loads(output.read_text("utf-8"))
            data["passed"]=(
                data["native_exit_code"]==0
                and isinstance(data["details"],dict)
                and data["details"].get("passed") is True
            )
            preview=output.with_name(f"{system}-frame.png")
            if preview.is_file():
                report.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(preview,report.with_name(preview.name))
    except Exception as exc:
        data["error"]=f"{type(exc).__name__}: {exc}"
    finally:
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(data,indent=2),flush=True)
    return 0 if data["passed"] else 1

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system",choices=SYSTEMS,required=True)
    parser.add_argument("--core",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    parser.add_argument("--seconds",type=int,default=8)
    parser.add_argument("--rom",type=Path)
    parser.add_argument("--child",action="store_true")
    args=parser.parse_args()
    if not 2<=args.seconds<=60:
        parser.error("seconds must be between 2 and 60")
    if args.child:
        if args.rom is None:
            parser.error("--child requires --rom")
        return _child(args.system,args.core.resolve(),args.rom.resolve(),
                      args.report.resolve(),args.seconds)
    return _parent(args.system,args.core.resolve(),args.report.resolve(),args.seconds)

if __name__=="__main__":
    raise SystemExit(main())
