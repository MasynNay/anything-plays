# Embedded 3D emulator architecture — Anything Plays 2.1

**Release target:** One installer; one Anything Plays window; select a
user-provided ROM/disc, select a camera, and play. No separately installed
RetroArch or Dolphin, no detached 3D window. Do not promote an external
launcher or a controller bridge as though it satisfies this requirement.

## Current implementation

- GB/GBC/GBA (mGBA), SNES (Snes9x), NES (FCEUmm) and Genesis (Genesis Plus GX)
  provide software video buffers through the Libretro frontend and display
  within the Tk game panel.
- N64 has an experimental in-panel ParaLLEl-N64 + Angrylion software path.
  Source, UI and synthetic tests pass. Real ROM startup, Apple Silicon
  compatibility, save integrity, latency and FPS are **not yet verified**.
  The external RetroArch launcher is a temporary fallback.
- GameCube now has an experimental **in-panel Dolphin Libretro software
  renderer**. The alpha downloader, build scripts and bundle verifier require
  the Dolphin native core and its `dolphin-emu/Sys` data on each platform.
  Its camera/keyboard inputs are routed through Libretro without a second
  emulator process. **This proves integration code and package presence,
  not real-game playability or acceptable frame rate.** The external
  controller pipe is an optional developer fallback, not a release feature.

## GPU frontend required for hardware-rendered Libretro cores

A core requesting `RETRO_ENVIRONMENT_SET_HW_RENDER` cannot be run by
treating `retro_video_refresh_t` data as a CPU framebuffer. The frontend
must provide an actual graphics context with a lifetime spanning core
initialization, game load, frame execution, and shutdown.

1. **Platform surface adapter:** create a native GPU rendering surface
   *inside* Anything Plays' game panel, with suitable integration for
   macOS (native NSView, Apple Silicon and Intel), Windows (native HWND),
   and Linux (X11/Wayland as supported). A separate top-level emulator
   window does not pass acceptance.
2. **Libretro hardware environment:** implement and validate
   `SET_HW_RENDER`, context negotiation, `get_current_framebuffer`,
   `get_proc_address`, `context_reset` and `context_destroy` according
   to the selected core and graphics API. Hardware video uses
   `RETRO_HW_FRAME_BUFFER_VALID` rather than a CPU pixel pointer.
3. **Thread and context ownership:** call core GPU functions only on a
   thread where the selected GPU context is current. Serialize resize,
   fullscreen switching, context loss, save/unload and shutdown.
4. **In-panel presentation:** transfer or present the GPU framebuffer in
   the existing game region. The camera UI and zone overlays remain
   functional independently. Exiting Game only must restore the ordinary
   in-panel surface without creating a second application window.
5. **Input/audio:** reuse the existing camera zone and manual-button
   mappings through the Libretro input callbacks. Test N64 analog axes,
   GameCube main stick/C-stick/triggers, release-on-stop, latency, and
   audio underrun handling.
6. **Distribution:** bundle *pinned, checksum-verified* core binaries and
   required data (including Dolphin `Sys` resources where applicable)
   for every supported OS/architecture. Review GPL and other notices,
   publisher requirements, bundle signing, and native dependency closure.
   Update via a validated whole-app release, with rollback; never
   overwrite a running signed native library.
7. **Isolation:** native core faults can crash a shared process even if
   Python/Tk allocations are bounded. Define a tested failure-isolation
   strategy before claiming unattended multi-day native-3D reliability.

## Release acceptance, per platform

- A fresh system with **no** RetroArch or Dolphin installed runs an
  owned/homebrew N64 test ROM and GameCube test image from inside the same
  Anything Plays game panel.
- No emulator path picker, external installer, detached window, or manual
  graphics core download is needed.
- Camera and manual controls work; all releases correctly neutralize
  held buttons, analog axes and triggers.
- Windowed, borderless, fullscreen and Game only all render correctly.
- Battery/memory-card saves survive restart; audio/video remain in sync.
- A minimum four-hour real-game/camera soak and overnight idle test record
  memory, CPU, process count, native handles, save integrity, frame rate,
  reconnection behavior and crash reports.
- SHA-256 provenance, licensing documentation, release bundle verification,
  and Windows/macOS/Linux test installers all pass.
- Public 2.0 artifacts, tag and branch are unchanged.

## References

- Libretro hardware rendering design:
  https://raw.githubusercontent.com/libretro/libretro.github.com/master/documents/libretro-gl.pdf
- Dolphin Libretro core requirements:
  https://docs.libretro.com/library/dolphin/
- Dolphin project licensing and current platforms:
  https://dolphin-emu.org/docs/faq/

**Status:** Both 3D consoles have experimental CPU-rendered in-panel
Libretro paths. Software rendering may be prohibitively slow for GameCube.
A native GPU host remains the required next architecture if performance or
compatibility tests fail. No system is marked release-ready based only on
source tests, native core downloads or successful installer checks.
