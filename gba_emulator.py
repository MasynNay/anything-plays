"""Embedded multi-system gaming via bundled *libretro* cores. No OS keyboard injection.
The native mGBA core is downloaded and bundled by platform build scripts.
"""
import ctypes as C
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time

try:
    import sounddevice as sd
except ImportError:
    sd = None

import numpy as np
from systems import SYSTEMS

BUTTONS = ('Up','Down','Left','Right','A','B','Start','Select','X','Y','L','R')
IDS = {'B':0,'Y':1,'Select':2,'Start':3,'Up':4,'Down':5,'Left':6,'Right':7,'A':8,'X':9,'L':10,'R':11}
VIDEO = C.CFUNCTYPE(None, C.c_void_p,C.c_uint,C.c_uint,C.c_size_t)
AUDIO = C.CFUNCTYPE(None,C.c_int16,C.c_int16)
AUDIO_BATCH = C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
INPUT_POLL = C.CFUNCTYPE(None)
INPUT_STATE = C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint)
ENV = C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p)
class GameInfo(C.Structure):
    _fields_=[('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]
class CoreInfo(C.Structure):
    _fields_ = [("library_name", C.c_char_p), ("library_version", C.c_char_p),
                ("valid_extensions", C.c_char_p), ("need_fullpath", C.c_bool),
                ("block_extract", C.c_bool)]

class Geometry(C.Structure):
    _fields_=[('base_width',C.c_uint),('base_height',C.c_uint),('max_width',C.c_uint),('max_height',C.c_uint),('aspect_ratio',C.c_float)]
class Timing(C.Structure):
    _fields_=[('fps',C.c_double),('sample_rate',C.c_double)]
class AVInfo(C.Structure):
    _fields_=[('geometry',Geometry),('timing',Timing)]

def find_core(system="gba"):
    suffix = '.dll' if sys.platform == 'win32' else '.dylib' if sys.platform == 'darwin' else '.so'
    core = SYSTEMS[system].core
    names = [core+'_libretro'+suffix, 'libretro_'+core+suffix]
    dirs = [Path(__file__).resolve().parent/'cores', Path(sys.executable).resolve().parent/'cores', Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))/'cores', Path.home()/'.config'/'retroarch'/'cores',Path('/usr/lib/libretro'),Path('/usr/lib/x86_64-linux-gnu/libretro'),Path('/usr/local/lib/libretro')]
    if sys.platform == 'darwin':
        dirs += [Path.home()/'Library/Application Support/RetroArch/cores',Path('/Applications/RetroArch.app/Contents/Resources/cores')]
    return next((str(d/n) for d in dirs for n in names if (d/n).is_file()),None)

class Emulator:
    """Run a libretro core in a worker thread and expose frame-safe controls."""

    def __init__(self):
        self.commands=queue.Queue(maxsize=32)
        self.manual_buttons=set()
        self.manual_lock=threading.Lock()
        self.stop_event=threading.Event()
        self.thread=None
        self.running=False
        self.armed=False
        self.error=None
        self.frame=None
        self.lock=threading.Lock()
        self.system="gba"
        self.core_path=find_core(self.system)
        self.rom=None
    def find_system_core(self):
        return find_core(self.system)
    def start(self,rom):
        self.stop()
        self.rom=str(rom)
        self.error=None
        self.stop_event.clear()
        self.thread=threading.Thread(target=self._run,daemon=True)
        self.thread.start()
    def press(self,button,frames=8):
        if not self.running or not self.armed or button not in BUTTONS: return
        try:self.commands.put_nowait((button,max(1,min(60,int(frames)))))
        except queue.Full:pass
    def set_manual(self, button, down):
        if button not in BUTTONS:
            return
        with self.manual_lock:
            if down: self.manual_buttons.add(button)
            else: self.manual_buttons.discard(button)

    def release_manual(self):
        with self.manual_lock:
            self.manual_buttons.clear()

    def disarm(self):
        self.armed=False
        while True:
            try:self.commands.get_nowait()
            except queue.Empty:break
    def stop(self):
        self.release_manual()
        self.disarm()
        self.stop_event.set()
        if self.thread and self.thread.is_alive():self.thread.join(timeout=4)
        self.thread=None
        self.running=False
    def _run(self):
        core=None; initialized=False; loaded=False; audio_stream=None
        try:
            if not self.core_path or not Path(self.core_path).is_file():
                raise RuntimeError(f'{SYSTEMS[self.system].title} bundled emulator core not found. Please reinstall Anything Plays.')
            core=C.CDLL(self.core_path)
            def fn(name,restype,args):
                f=getattr(core,name);f.restype=restype;f.argtypes=args;return f
            set_env=fn('retro_set_environment',None,[ENV])
            set_video=fn('retro_set_video_refresh',None,[VIDEO])
            set_audio=fn('retro_set_audio_sample',None,[AUDIO])
            set_audio_batch=fn('retro_set_audio_sample_batch',None,[AUDIO_BATCH])
            set_poll=fn('retro_set_input_poll',None,[INPUT_POLL])
            set_state=fn('retro_set_input_state',None,[INPUT_STATE])
            init=fn('retro_init',None,[]);deinit=fn('retro_deinit',None,[])
            load=fn('retro_load_game',C.c_bool,[C.POINTER(GameInfo)])
            system_info=fn('retro_get_system_info',None,[C.POINTER(CoreInfo)])
            unload=fn('retro_unload_game',None,[])
            run=fn('retro_run',None,[])
            avinfo=fn('retro_get_system_av_info',None,[C.POINTER(AVInfo)])
            get_memory_data=fn('retro_get_memory_data',C.c_void_p,[C.c_uint])
            get_memory_size=fn('retro_get_memory_size',C.c_size_t,[C.c_uint])
            pressed=set();remaining={};pixel_format=0
            system_dir=os.fsencode(str(Path.home() / 'Library' / 'Application Support' / 'AnythingPlays')) if sys.platform=='darwin' else os.fsencode(str(Path.home() / '.config' / 'anything-plays'))
            Path(os.fsdecode(system_dir)).mkdir(parents=True,exist_ok=True)
            system_dir_buffer=C.create_string_buffer(system_dir)
            # libretro cores may require a filesystem path rather than an in-memory buffer.
            core_info=CoreInfo()
            system_info(C.byref(core_info))
            audio_lock=threading.Lock()
            audio_chunks=queue.Queue(maxsize=32)
            audio_pending=np.empty((0,2), dtype=np.int16)
            audio_pos=0
            def audio_sample(left,right):
                push_audio(np.array([[left,right]],dtype=np.int16))
            def push_audio(samples):
                if not len(samples): return
                try: audio_chunks.put_nowait(samples.copy())
                except queue.Full:
                    try: audio_chunks.get_nowait()
                    except queue.Empty: pass
                    try: audio_chunks.put_nowait(samples.copy())
                    except queue.Full: pass
            def audio_batch(ptr,frames):
                if ptr and frames:
                    samples=np.ctypeslib.as_array(C.cast(ptr,C.POINTER(C.c_int16)),shape=(int(frames)*2,))
                    push_audio(samples.reshape(-1,2))
                return frames
            def audio_callback(outdata,frames,time_info,status):
                nonlocal audio_pending,audio_pos
                outdata.fill(0)
                written=0
                while written<frames:
                    if audio_pos>=len(audio_pending):
                        try: audio_pending=audio_chunks.get_nowait()
                        except queue.Empty: break
                        audio_pos=0
                    n=min(frames-written,len(audio_pending)-audio_pos)
                    outdata[written:written+n]=audio_pending[audio_pos:audio_pos+n]
                    written+=n;audio_pos+=n
            def environment(cmd,data):
                nonlocal pixel_format
                if cmd==10 and data: # SET_PIXEL_FORMAT: 0 RGB1555, 1 XRGB8888, 2 RGB565
                    pixel_format=C.cast(data,C.POINTER(C.c_int))[0]
                    return pixel_format in (0,1,2)
                if cmd in (9, 31) and data: # GET_SYSTEM_DIRECTORY / GET_SAVE_DIRECTORY
                    C.cast(data,C.POINTER(C.c_char_p))[0]=C.cast(system_dir_buffer,C.c_char_p)
                    return True
                if cmd==3 and data: # GET_CAN_DUPE: support repeat-last-frame
                    C.cast(data,C.POINTER(C.c_bool))[0]=True
                    return True
                if cmd==18: return True # SET_SUPPORT_NO_GAME (ignored)
                return False
            def video(data,width,height,pitch):
                if not data or width==0 or height==0:return
                raw=C.string_at(data,int(pitch)*int(height))
                if pixel_format==1:
                    pixels=np.ndarray((height,width),dtype='<u4',buffer=raw,strides=(pitch,4))
                    rgb=np.stack(((pixels>>16)&255,(pixels>>8)&255,pixels&255),axis=-1).astype('uint8')
                else:
                    pixels=np.ndarray((height,width),dtype='<u2',buffer=raw,strides=(pitch,2))
                    if pixel_format==2:
                        r=(pixels>>11)&31;g=(pixels>>5)&63;b=pixels&31
                        rgb=np.stack((r*255//31,g*255//63,b*255//31),axis=-1).astype('uint8')
                    else:
                        r=(pixels>>10)&31;g=(pixels>>5)&31;b=pixels&31
                        rgb=np.stack((r*255//31,g*255//31,b*255//31),axis=-1).astype('uint8')
                with self.lock:self.frame=rgb
            def input_state(port,device,index,button):
                return int(port==0 and device==1 and button in pressed)
            callbacks=[ENV(environment),VIDEO(video),AUDIO(audio_sample),AUDIO_BATCH(audio_batch),INPUT_POLL(lambda:None),INPUT_STATE(input_state)]
            set_env(callbacks[0]);set_video(callbacks[1]);set_audio(callbacks[2]);set_audio_batch(callbacks[3]);set_poll(callbacks[4]);set_state(callbacks[5])
            init();initialized=True
            rom_path=Path(self.rom).resolve()
            if not rom_path.is_file(): raise FileNotFoundError(f'ROM not found: {rom_path}')
            path_bytes=os.fsencode(str(rom_path))
            rom_buffer=None
            if core_info.need_fullpath:
                game=GameInfo(path_bytes,None,0,None)
            else:
                rom_bytes=rom_path.read_bytes()
                rom_buffer=C.create_string_buffer(rom_bytes)
                game=GameInfo(path_bytes,C.cast(rom_buffer,C.c_void_p),len(rom_bytes),None)
            load_ok=bool(load(C.byref(game)))
            # Some libretro builds differ in how they accept game data. If the
            # advertised loading mode fails, retry once using the other form.
            if not load_ok and self.system in ('gb','gbc'):
                print(f'[AnythingPlays] Gambatte rejected {rom_path.name} using '
                      f'{"path" if core_info.need_fullpath else "memory"}; retrying alternate mode.',
                      file=sys.stderr,flush=True)
                if core_info.need_fullpath:
                    rom_bytes=rom_path.read_bytes()
                    rom_buffer=C.create_string_buffer(rom_bytes)
                    alternate=GameInfo(path_bytes,C.cast(rom_buffer,C.c_void_p),len(rom_bytes),None)
                else:
                    alternate=GameInfo(path_bytes,None,0,None)
                load_ok=bool(load(C.byref(alternate)))
            if not load_ok:
                name=(core_info.library_name or b'unknown').decode(errors='replace')
                raise RuntimeError(f'{SYSTEMS[self.system].title} core ({name}) rejected '
                    f'{rom_path.name} in both loading modes (need_fullpath={bool(core_info.need_fullpath)}). '
                    'Check the Terminal for Gambatte messages.')
            loaded=True
            info=AVInfo();avinfo(C.byref(info))
            fps=info.timing.fps if 20 < info.timing.fps < 240 else 59.7275
            sample_rate=info.timing.sample_rate
            if sd is not None and 8000 <= sample_rate <= 192000:
                try:
                    audio_stream=sd.OutputStream(samplerate=int(round(sample_rate)),channels=2,
                        dtype='int16',blocksize=1024,callback=audio_callback)
                    audio_stream.start()
                except Exception as audio_exc:
                    print(f'Audio output unavailable: {audio_exc}',file=sys.stderr)
                    audio_stream=None
            elif sd is None:
                print('Audio output unavailable: sounddevice not installed',file=sys.stderr)
            save=Path(self.rom).with_suffix('.sav')
            def restore():
                p=get_memory_data(0);n=get_memory_size(0)
                if p and n and save.exists():
                    data=save.read_bytes()
                    C.memmove(p,data,min(n,len(data)))
            def persist():
                p=get_memory_data(0);n=get_memory_size(0)
                if p and n:save.write_bytes(C.string_at(p,n))
            restore()
            self.running=True
            counter=0;next_tick=time.monotonic()
            while not self.stop_event.is_set():
                if not self.armed:
                    pressed.clear();remaining.clear()
                    while True:
                        try:self.commands.get_nowait()
                        except queue.Empty:break
                else:
                    for _ in range(8):
                        try:button,duration=self.commands.get_nowait()
                        except queue.Empty:break
                        remaining[IDS[button]]=duration
                    pressed=set(remaining)
                with self.manual_lock:
                    pressed.update(IDS[b] for b in self.manual_buttons)
                run();counter+=1
                for key in list(remaining):
                    remaining[key]-=1
                    if remaining[key]<=0:del remaining[key]
                if counter%300==0:persist()
                next_tick+=1/fps
                wait=next_tick-time.monotonic()
                if wait>0:self.stop_event.wait(wait)
                elif wait < -.25:next_tick=time.monotonic()
            pressed.clear()
            self.release_manual()
            persist()
        except Exception as exc:
            self.error=f'{type(exc).__name__}: {exc}'
        finally:
            self.armed=False;self.running=False
            if audio_stream is not None:
                try: audio_stream.stop(); audio_stream.close()
                except Exception: pass
            if core is not None:
                try:
                    if loaded:unload()
                    if initialized:deinit()
                except Exception:pass
