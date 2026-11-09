# Architecture · Anything Plays 2.0–3.0

Anything Plays is a desktop UI wrapped around a deliberately small emulator
integration layer. The application uses camera tracking as *gamepad input* and
does not send global keyboard events to the operating system.

## Source layout

| Area | Modules | Responsibility |
| :-- | :-- | :-- |
| Application | `app.py`, `anything_plays/settings_defaults.py` | Startup, state ownership, lifecycle, legacy defaults |
| Desktop UI | `anything_plays/ui_layout.py`, `anything_plays/ui_theme.py` | Layout construction, scrolling, 16 themes |
| Camera and zones | `anything_plays/ui_camera.py`, `anything_plays/tracking.py`, `anything_plays/ui_zones.py`, `anything_plays/zone_rendering.py` | Capture, HSV detection, hit testing, editor and preview |
| Profiles | `anything_plays/ui_profiles.py`, `anything_plays/system_profiles.py` | Console switching, migration, validation, atomic JSON writes |
| ROM library | `anything_plays/ui_library.py`, `anything_plays/rom_library.py`, `anything_plays/cartridge_art.py` | Bounded scanning, shelf interactions, local cartridge rendering |
| Emulator facade | `anything_plays/gba_emulator.py` | Worker lifecycle and native core initialization |
| Libretro adapters | `anything_plays/libretro_abi.py`, `anything_plays/core_locator.py`, `anything_plays/libretro_input.py`, `anything_plays/libretro_audio.py`, `anything_plays/libretro_video.py`, `anything_plays/libretro_save.py` | Native API, isolation, bounded queues, frame and save conversions |
| Console map | `anything_plays/systems.py` | One source of truth for core IDs and ROM extensions |
| Build and verification | `fetch_mgba_core.py`, `packaging/build_*`, `.github/workflows/`, `tools/`, `tests/` | Native packaging, provenance, regression and release acceptance |

## Why UI mixins?

The original UI's callbacks share a single group of Tk variables and widget
references. Separating their source into narrowly named *mixins* preserves that
working state model and user-visible behavior without a risky rewrite of the
Tkinter screen hierarchy. `App` is the composition root and owns state; no
mixin creates its own window or has an independent event loop.

`LayoutMixin.build` creates the screen in four sections, while the other mixins
provide the corresponding commands. This is an intentional incremental
architecture rather than claiming the UI is already a fully decoupled MVC app.

## Thread and memory ownership

1. **Main Tk thread:** owns all widgets, Tk variables, camera preview frames,
   and user actions. Camera discovery runs in a short-lived daemon thread and
   passes results through a thread-safe queue, which the Tk loop polls.
2. **Libretro worker:** opens and initializes the core, loads a user-selected
   ROM, owns `retro_run`, schedules frames, and persists battery-backed SRAM.
   The UI accesses the latest RGB frame only while holding `Emulator.lock`.
3. **Native callback lifetime:** `NativeCore` retains `CFUNCTYPE` references
   until *after* unloading the game and deinitializing the core. ROM memory
   buffers and system-directory strings are retained for the whole session.
4. **Game input:** camera presses enter a bounded queue, expiring after a
   configured number of emulator frames. Manually held buttons use their own
   synchronized set and still work when object tracking is disarmed.
5. **Game audio:** callbacks enqueue copied stereo samples. PortAudio consumes
   them asynchronously. An unavailable output device never stops the emulator;
   empty buffers are filled with silence, and overloaded queues drop old audio.
6. **Shutdown:** stop requests are signaled to the worker; the UI cannot safely
   start a new core while the previous worker is still shutting down.

## Tracking algorithm

The preview frame is converted from BGR to HSV and compared with the sampled
target color. Hue difference wraps at the red boundary. Saturation/value
thresholds tolerate moderate lighting variation; a 3×3 morphological opening
removes single-pixel noise. The largest contour exceeding the configured
minimum area provides the center point.

That center is tested against normalized rectangles in profile order. Disabled
mappings and a disabled Shuffle zone are excluded. The overlay renderer works
on a **copy** of the frame, so strokes and labels never affect detection.

## Persistence and compatibility

The historic `~/.config/fish-plays-pokemon-studio/preferences.json` location is
preserved. Profiles live beside it in `system_profiles.json`. `normalize`
merges valid values into console-specific defaults, drops malformed rectangles,
and preserves unrelated top-level preferences. Per-console writes use a
temporary file and `Path.replace` to avoid leaving half-written JSON behind.

The ROM shelf never downloads games. It walks at most 2,500 directories or
2,000 matching files, never follows directory symlinks, and accepts optional
cover art from the ROM's own folder. SRAM saves remain next to ROMs as `.sav`.

## Build integrity and release gates

`fetch_mgba_core.py` downloads the matching Libretro nightly binaries and
writes `cores/CORE_PROVENANCE.json` containing the URL, filename, size and
SHA-256 for each. That manifest is copied into each packaged app. It provides
provenance, **not** pinned, reproducible builds or a license grant.

The automated suite includes pure tests for pixel formats, button timing,
tracking, audio, ROM browsing, and migration. On Linux it also compiles a
synthetic Libretro C core to exercise native callbacks and SRAM writes. The
optional Xvfb test exercises Tk startup, theme changes, console switching,
and shutdown. Real cameras, real Libretro cores on each OS, and installer
behavior must still be checked manually.
