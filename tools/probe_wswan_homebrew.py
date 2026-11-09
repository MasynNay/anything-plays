"""Embedded Beetle WonderSwan real video and native wavetable PCM diagnostics.

A temporary original V30MZ game is generated in each parent process.
A native crash remains isolated in the child. Requiring nonblank changing
RGB and nonzero core-generated stereo PCM prevents optimistic false passes.
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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.wswan_homebrew_fixture import SYSTEMS,write_wonder_probe
from tools.probe_nes_homebrew import ObservedAudio


def _child(system,core,rom,seconds,report):
    import faulthandler
    faulthandler.enable(all_threads=True)
    from PIL import Image
    from anything_plays.gba_emulator import Emulator,CoreSession

    emu=Emulator()
    emu.system=emu.inputs.system=system
    emu.core_path=str(core)
    session=CoreSession(emu,system,rom,str(core))
    session.audio.close()
    session.audio=ObservedAudio()
    original=session.video
    frames=nonblank=0
    hashes=set()
    total_hashes=set()
    low,high=255,0
    def video(ptr,width,height,pitch):
        nonlocal frames,nonblank,low,high
        prior=emu.frame_serial
        original(ptr,width,height,pitch)
        if emu.frame_serial==prior:
            return
        frames+=1
        if frames>70 and frames%11!=1:
            return
        with emu.lock:
            sample=emu.frame
            if sample is None:
                return
            minimum,maximum=int(sample.min()),int(sample.max())
            low=min(low,minimum)
            high=max(high,maximum)
            digest=hashlib.sha256(sample.tobytes()).hexdigest()[:16]
            total_hashes.add(digest)
            if maximum>8 and minimum!=maximum:
                nonblank+=1
                hashes.add(digest)
                if nonblank==1:
                    Image.fromarray(sample).save(
                        report.with_name(f"{system}-original-frame.png")
                    )
    session.video=video
    timer=threading.Timer(seconds,emu.stop_event.set)
    timer.daemon=True
    timer.start()
    start=time.monotonic()
    error=None
    try:
        session.run()
    except Exception as exc:
        error=f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        emu.stop_event.set()
        timer.cancel()
    duration=max(0.001,time.monotonic()-start)
    sound=session.audio
    passed=(
        error is None and frames>=30 and frames/duration>=20
        and nonblank>=3 and len(hashes)>=2
        and sound.samples>1000 and sound.nonzero>100
        and sound.peak>0 and 8000<=(sound.sample_rate or 0)<=192000
    )
    result={
        "system":system,"source":"original V30MZ cartridge",
        "native_video_frames":frames,
        "native_video_fps":round(frames/duration,2),
        "nonblank_sampled_frames":nonblank,
        "distinct_nonblank_frames":len(hashes),
        "all_distinct_frame_hashes":len(total_hashes),
        "observed_rgb_range":[low,high],
        "native_audio_frames":sound.samples,
        "nonzero_pcm_values":sound.nonzero,
        "sample_rate":sound.sample_rate,
        "native_audio_peak":sound.peak,
        "physical_speakers_tested":False,
        "passed":passed,"error":error,
    }
    report.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2),flush=True)
    return 0 if passed else 1


def _parent(system,core,report,seconds):
    outcome={"system":system,"passed":False,"native_exit_code":None,
             "timed_out":False,"error":None,"details":None}
    try:
        if not core.is_file():
            raise FileNotFoundError("Missing Mednafen WonderSwan native core")
        with tempfile.TemporaryDirectory(prefix="ap-wswan-original-") as tmp:
            folder=Path(tmp)
            rom=folder/("original-"+system+"."+system)
            outcome["fixture"]=write_wonder_probe(rom,system)
            child=folder/"result.json"
            env=os.environ.copy()
            env["HOME"]=str(folder)
            env["XDG_CONFIG_HOME"]=str(folder/"config")
            cmd=[sys.executable,str(Path(__file__).resolve()),"--child",
                 "--system",system,"--core",str(core),"--rom",str(rom),
                 "--seconds",str(seconds),"--report",str(child)]
            try:
                process=subprocess.run(
                    cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                    text=True,check=False,env=env,timeout=seconds+25)
                outcome["native_exit_code"]=process.returncode
                outcome["console_tail"]=process.stdout[-12000:]
            except subprocess.TimeoutExpired as exc:
                outcome["timed_out"]=True
                raw=exc.stdout or b""
                outcome["console_tail"]=(
                    raw.decode("utf-8","replace") if isinstance(raw,bytes)
                    else raw
                )[-12000:]
            if child.is_file():
                outcome["details"]=json.loads(child.read_text("utf-8"))
            outcome["passed"]=(
                outcome["native_exit_code"]==0
                and isinstance(outcome["details"],dict)
                and outcome["details"].get("passed") is True
            )
            frame=child.with_name(system+"-original-frame.png")
            if frame.is_file():
                report.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(frame,report.with_name(frame.name))
    except Exception as exc:
        outcome["error"]=f"{type(exc).__name__}: {exc}"
    finally:
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(json.dumps(outcome,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(outcome,indent=2),flush=True)
    return 0 if outcome["passed"] else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--system",choices=SYSTEMS,required=True)
    p.add_argument("--core",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--seconds",type=int,default=8)
    p.add_argument("--rom",type=Path)
    p.add_argument("--child",action="store_true")
    args=p.parse_args()
    if not 2<=args.seconds<=60:
        p.error("Seconds must be 2..60")
    if args.child:
        if args.rom is None:
            p.error("--child requires --rom")
        return _child(args.system,args.core.resolve(),args.rom.resolve(),
                      args.seconds,args.report.resolve())
    return _parent(args.system,args.core.resolve(),args.report.resolve(),
                   args.seconds)


if __name__=="__main__":
    raise SystemExit(main())
