# GameCube accelerated in-app renderer — isolated Linux experiment

Anything Plays 2.1 must include GameCube **inside its game panel**, with
camera controls, no separate Dolphin installation, and no external game window.

## Verified so far

- Linux pinned-source Dolphin Libretro now compiles and links successfully.
- The patched CPU software framebuffer can return a real nonblank
  640×576 GameCube homebrew frame.
- The default Dolphin JIT currently segfaults in generated CPU code.
- Cached interpreter avoids that native crash but reaches only 0.05
  decoded frames per second in a 20-second homebrew experiment.
- The *unmodified* bundled Dolphin Libretro library is available in
  all four 2.1 test installers; this does not establish playable gameplay.

Native evidence: [CI #294](https://github.com/MasynNay/anything-plays/actions/runs/42335345233).
The software-only renderer is not an acceptable final backend.

## Current research: hidden OpenGL FBO

The Linux-only test modules `tools/libretro_gpu_egl.py`,
`tools/probe_gamecube_gl.py` and `tools/smoke_gamecube_opengl.py`
attempt to use a **hidden EGL pbuffer OpenGL 3.3+ context**. The test
frontend negotiates `RETRO_ENVIRONMENT_SET_HW_RENDER`, fills the exact
`retro_hw_render_callback` layout, gives Dolphin a color/depth/stencil
FBO, and reads owned RGB pixels back from that FBO on its emulator
thread. Frames are passed to the same `CoreSession` shared frame queue
used by the Tk game canvas.

There is NO exposed Dolphin window, NO RetroArch dependency, and NO
runtime emulator download. The test uses pinned zlib-licensed homebrew
and a bundled Libretro library acquired only by the CI builder.

**The code is experimental, not the current player's default.**
First require a real valid EGL FBO, confirm the hardware callback
lifecycles, and successfully boot/produce nonblank frames in CI.
Then establish sustainable FPS, audio, analog/camera controls, memory
cards/saves and hours-long uptime. Finally implement real GPU hosts for
Windows, macOS Intel, and macOS Apple Silicon. EGL/Linux validation
alone cannot qualify a cross-platform GameCube release.

Never mark `config/v2.1-release-acceptance.json` requirements true
without their evidence. Do not overwrite released 2.0.


## CI #295: Offscreen context works, gameplay still blocked

[Run #295](https://github.com/MasynNay/anything-plays/actions/runs/42336215058)
verified an offscreen OpenGL 4.5 pbuffer and its RGB framebuffer readback,
then negotiated the bundled nightly Dolphin hardware renderer. The first
**20-second game runs did not pass**: both JIT and cached interpreter emitted
two blank frames, 0 nonblank samples, and approximately 0.1 FPS. The
probe steps intentionally continued on error so both modes could run;
**the final evidence gate failed**. A green continue-on-error *step*
is NOT a passed gameplay probe.

The runner uses `LIBGL_ALWAYS_SOFTWARE=1` Mesa llvmpipe, so this is
a software GPU-driver result, not a hardware-accelerated performance
measurement. A follow-up records the GL vendor/renderer, actual
`retro_run()` timings, RGB ranges and first blank frames, and runs
the engine for longer to distinguish shader startup cost from incorrect
video submission. Do not switch the default player to this backend yet.


## CI #296: frame submission/synchronization is the blocker

[Run #296](https://github.com/MasynNay/anything-plays/actions/runs/42336417071):
Mesa llvmpipe/OpenGL 4.5, no GL errors, 3,739 successful native `retro_run()`
invocations in 75.3 seconds (JIT), but only **two blank frame callbacks**.
Cached interpreter similarly returned 2 blank frames in 35.6 seconds.
The longest native `retro_run()` call was 73 ms; simply waiting longer
will not restore gameplay. The observed video failure is not evidence
that a real GPU is merely too slow.

The next isolated run tests `dolphin_main_cpu_thread=disabled` in both
JIT and cached-interpreter modes. Dolphin's Libretro `retro_run` calls
`Core::DoFrameStep` and `FifoManager::RunGpuLoop` in dual-core mode;
with one emulated CPU thread it instead executes `RunSingleFrame`.
This can narrow down whether frontend frame stepping and GPU thread
synchronization are preventing presentation. Neither option is applied to
installed apps without usable frames and full QA.


## CI #297: single-core also fails, so measure emulated progress

[Run #297](https://github.com/MasynNay/anything-plays/actions/runs/42336706577)
returned exactly two blank framebuffer callbacks in *all four* configurations:
dual/single core × JIT/cached interpreter. A 25-second single-core JIT
run issued 1,238 successful native calls and no OpenGL errors but generated
zero nonblack samples. Disabling dual-core alone does not address the root
cause.

New isolated probes count audio sample batches and safely sample up to 8 MiB
of Libretro-exposed emulated RAM at regular intervals. The bounded RAM digest
is a **diagnostic only**: change means the CPU/memory system is advancing;
unchanged data does not conclusively prove a stall. Audio sample batches
can independently indicate whether emulated video field boundaries occur.
No native memory pointers are held between calls and samples are short-lived.
As previous 75-second probes showed no improvement, short targeted CI tests
are used in this diagnostic instead of repeated long waits.
