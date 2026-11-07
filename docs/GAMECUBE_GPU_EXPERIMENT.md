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
