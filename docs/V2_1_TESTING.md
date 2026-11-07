# Anything Plays 2.1 — unified testing build

This branch combines the requested features **in one engineering test version**.
Do not request end-user testing or publish 2.1 until all 18 listed consoles are
playable inside the bundled application without third-party downloads.
It does not modify the public [2.0.0 release](https://github.com/MasynNay/anything-plays/releases/tag/v2.0.0).

## How to test

Open the most recent successful
[2.1 unified test workflow](https://github.com/MasynNay/anything-plays/actions/workflows/v21-test-build.yml),
select its run, and download the **TEST** artifact for your OS under Artifacts.

These are temporary CI test artifacts, **not a public stable release**.
They have distinct installation identities so stable 2.0 can remain installed:

- Windows installs to **Anything Plays 2.1 Test** under a separate Inno Setup
  AppId and folder.
- macOS creates **AnythingPlays21Test.app** in its own
  `AnythingPlays-2.1.0-alpha.1.dmg`.
- Linux installs `anything-plays-test` in
  `/opt/anything-plays-21-test` and launches as `anything-plays-21-test`.
- User settings live in `~/.config/anything-plays-21-test/`.
  On the first launch the test version copies existing 2.0 preferences and
  profiles **without writing changes back into the 2.0 profile**.

The app never provides or downloads commercial game ROMs or BIOS images.

## What's in 2.1

### Display, controls and overlays

- Windowed, borderless, fullscreen and game-only fullscreen modes.
- F11 toggles fullscreen, F10 toggles borderless and Escape exits a
  fullscreen view and stops object controls.
- Keyboard shortcuts can be changed **per embedded console** in the game panel by
  capturing keys; conflicting or reserved shortcuts are rejected, including uppercase/lowercase collisions. Keys stay
  app-local and do not inject operating-system input.
- Bolder camera control zones: new **Bold** style, centered label option,
  border thickness 2–16 px and stronger readable button labels. Existing
  Outline, High contrast, Minimal, opacity and image overlays remain.
- **Shuffle snaps into the same grid** as other enabled buttons when using
  Fit buttons to grid. Hidden Shuffle and disabled controls retain their
  saved positions, and the default layouts remain horizontally symmetric.
- Legacy 2.0 profiles, separate ROM shelves, live camera color tracking,
  fit-to-grid controls, manual keyboard play, themes and saves remain.
- **Corrected 2.1 fish artwork:** The handheld now shows its plain back,
  without the front-face buttons. The reviewable source image is
  `assets/anything_plays_v21.webp`; `tools/render_v21_icon.py` produces
  Windows ICO, macOS iconset source PNG and Linux app PNG inside `build/`.
  Stable 2.0 PNG/ICO files are never overwritten.

### Embedded native cores

| Console | Engine | Inputs |
| --- | --- | --- |
| Game Boy / Game Boy Color / Game Boy Advance | mGBA | D-pad / A/B / L/R as appropriate |
| Super Nintendo | Snes9x | D-pad / A/B/X/Y/L/R |
| Nintendo Entertainment System | FCEUmm | D-pad / A/B / Start / Select |
| Sega Genesis / Mega Drive | Genesis Plus GX | D-pad / A/B/C/X/Y/Z / Mode / Start |

The NES and Genesis cores are downloaded **only during 2.1 testing builds**
when `AP_V21_TEST_CORES=1`; their exact binary fingerprints, version strings
and source URLs are captured in the test bundle's
`cores/CORE_PROVENANCE.json`. The full upstream FCEUmm GPLv2 and Genesis
Plus GX noncommercial license notices are included in the test packages.
New core binaries are **not yet approved for a public release** and require
pinned source and independent native gameplay verification first.

### Experimental Nintendo 64 built-in software video

2.1's testing branch now includes a user-selectable **Play N64 in the app**
mode, using the **bundled ParaLLEl-N64 software renderer (Angrylion)** instead
of an external RetroArch GPU window. This is the default in the alpha UI.
It uses the same game canvas, keyboard mapping, audio and camera input path as
the other Libretro consoles. Press **Game only** for a fullscreen game view.

**Important:** This option has passed source and UI smoke tests, but real
N64 ROM compatibility, native macOS Apple Silicon startup, frame rate, saves
and audio still require validation on physical hardware. The software path
can be significantly slower than an accelerated renderer. Uncheck the option
to use the existing RetroArch fallback if the bundled core is unsuitable.

### Experimental GameCube built-in software video

The GameCube backend now has an **experimental in-app Dolphin Libretro path**.
The alpha build fetches the native Dolphin core and the required
`dolphin-emu/Sys` files at build time, verifies their hashes, and packages
them with Anything Plays. It uses Dolphin's CPU-based Software Renderer to
attempt to draw directly into the same Tk game panel, and sends keyboard and
camera controls to the Libretro input callbacks. The previous external Dolphin
launcher remains an optional developer fallback; it is **not** considered an
acceptable public-release user workflow.

**Not yet release-ready:** no GameCube disc/homebrew image has passed real-game
startup, audio/video performance, camera latency, save and multi-hour runtime
tests on the supported OSes. CPU rendering may be too slow; if so, a native
in-panel GPU surface will be required. CI build success alone does not
satisfy the release acceptance checklist.

### Expanded 18-console libraries (2.1 alpha)

The integrated selector now includes ten additional systems in their own
ROM shelves: Master System, Game Gear, SG-1000, Atari 2600/7800,
TurboGrafx-16 HuCard, Neo Geo Pocket/Color, and WonderSwan/Color.
Genesis, Master System, Game Gear and SG-1000 share the already-bundled
Genesis Plus GX library. In total, 18 console libraries map to 11 native
cores. Separate external emulator installations are not required.

See [expanded console notes](V2_1_EXPANDED_CONSOLES.md) and the strict
[18-system acceptance gate](../config/v2.1-release-acceptance.json).
These additional systems are **not** approved for public release until
real-game/video/input/audio/save/platform checks pass.

### Emulator update checks

The app runs a read-only source check in a background thread on startup,
then at most once every 24 hours. Users can click **Check emulator updates**
in the game panel. Installed Libretro native libraries are SHA-256 checked
against the bundled `CORE_PROVENANCE.json`; upstream GitHub source revisions
are reported without asserting that a newer compatible binary is available.

Native binaries are never overwritten inside a running app. Updated cores
must be reviewed for compatibility and licensing, built as part of a complete
signed installer, smoke-tested, and then distributed with an app update.
The check does not install any other applications or game images.

### Optional external hardware-rendered developer fallbacks

| Console | Optional developer-only fallback | Behavior |
| --- | --- | --- |
| Nintendo 64 | RetroArch with Mupen64Plus-Next core | Anything Plays scans N64 games and launches RetroArch with the selected native core |
| Nintendo GameCube | Dolphin Emulator | Anything Plays scans discs and launches Dolphin's own GPU window |

Only developers diagnosing experimental software-renderer performance need
to select an external executable. For the **in-app** N64 and GameCube modes,
the alpha installers include the Libretro cores and Dolphin system data
themselves. Game files are never included.

**New experimental camera and keyboard bridges:**

- **N64:** Anything Plays writes a temporary RetroArch configuration for
  Network RetroPad input, then sends controller button/axis events to
  `127.0.0.1:55400`. The main-stick camera zones become analog stick input;
  the C-button zones become right-stick input. RetroArch remains a separate
  GPU-rendered game window.
- **GameCube on macOS and Linux:** Anything Plays creates a dedicated 2.1
  Dolphin user folder with a named-pipe controller. The camera zones provide
  A/B/X/Y, Z, shoulder buttons, main stick and C-stick directions. Dolphin
  remains a separate GPU-rendered game window. This isolated test profile
  stores its saves separately from a regular Dolphin installation.
- **GameCube on Windows:** The named-pipe bridge is not supported in this
  alpha. Use Dolphin's own controller settings.
- **Manual keys:** Custom keys work while the Anything Plays game panel has
  keyboard focus; when RetroArch/Dolphin has focus, its own local controller
  mappings apply instead. Camera tracking can continue in the background.

**Do not confuse input integration with GPU video integration.**
Experimental software-rendered N64 mode draws its frames in the app's game
panel, but this has not been verified with real games on the target systems.
The external developer fallbacks still draw in separate windows. The
experimental Dolphin software renderer now sends CPU-owned video frames to
Anything Plays, but **it remains unproven at real-game speeds**. Accelerated
Libretro graphics embedding would require a native GPU context, framebuffer
ownership and render lifecycle; the existing Tk/software path cannot provide
that by itself. Real-game compatibility, latency, saves and multi-hour
reliability still require hardware testing.

**Security:** RetroArch's Network RetroPad receiver has no authentication.
Although Anything Plays sends only to localhost, RetroArch may listen on
other network interfaces. The per-launch `--appendconfig` file sets
`config_save_on_exit = false`; don't test this bridge on untrusted networks.
Dolphin uses local named pipes and its separate alpha user profile.

Dolphin accepts fullscreen and borderless display settings at startup.
The embedded Game only view is limited to software-rendered Libretro cores.

## Public-domain Nintendo 64 video diagnostic

The 2.1 CI now has a dedicated N64 in-panel rendering probe. It downloads
Christopher Bonhage's **Unlicensed/public-domain SaveTest-N64** test ROM from
an exact pinned upstream commit into a temporary CI directory, verifies the
expected Git blob hash, and records a SHA-256 identity. The ROM is **not**
committed or bundled with Anything Plays and is never fetched at runtime.
The probe loads it through the actual ParaLLEl-N64 / Angrylion
`CoreSession` (no external emulator), captures a real decoded RGB image,
and records FPS, frame count, and whether frames contain nonblank pixels.
The probe runs in an isolated subprocess so a native crash cannot kill the
whole packaging process. Its artifact is called
`AnythingPlays-2.1-N64-real-homebrew-evidence`.

The probe is an engineering test, not a release certification. Failure is
reported in CI; passing it is not a substitute for testing playable games,
sound, analog inputs, saves, camera controls, and sustained operation on
all supported platforms.

**First native video result:** [CI run #291](https://github.com/MasynNay/anything-plays/actions/runs/42333130745)
successfully decoded 1,198 frames at 59.9 FPS with 239 nonblank samples
during a 20-second run of the public-domain test ROM on Linux x64.
This proves an N64 homebrew RGB video path works in the app's core
frontend on that runner. It does not certify other ROMs, other platforms,
camera controls, saves or hours-long operation.

## Testing priorities

1. Validate each installer starts without replacing stable 2.0.
2. Start an existing game on each legacy console; confirm save RAM/audio.
3. Use a legally obtained homebrew/test NES and Genesis ROM, check all
   gamepad buttons and save/reload.
4. Select all four view modes and verify F11/F10/Escape behavior, including
   game-only fullscreen.
5. Rebind two keyboard keys and confirm restart persistence, conflict
   rejection and per-console independence.
6. Set Bold camera zones to 8–12px borders and centered text; check target
   tracking on the raw camera feed and readability at real camera distance.
7. Launch N64 through installed RetroArch and GameCube through Dolphin;
   confirm camera and manual gamepad responses, analog directions, launcher
   errors, and release-on-stop. Check GameCube saves in the isolated test
   profile rather than regular Dolphin.
8. Compare FPS, idle CPU, memory usage and latency with stable 2.0.

## Long-running stability and memory testing

**Long uptime is a release requirement.** A clean short build does not prove
that an app can run overnight, or that the native emulator/driver never leaks.

The 2.1 alpha now has several bounded-resource protections:

- Tk image canvas items are **reused** rather than deleted and recreated
  for each game or camera frame; native image pixel storage is also reused
  where dimensions permit.
- Game rendering runs on its own timer, and idles at a lower polling rate
  without a running game. Camera processing also slows for still images.
- ROM shelf thumbnails, controller/audio command queues, and resized
  camera-zone artwork caches all have explicit size limits.
- Stopping a camera releases capture and stale frame buffers; exiting cancels
  the recurring UI/update timers and releases images and emulator resources.
- Identical SRAM is not rewritten to disk every few seconds. A temporary
  save-write error is surfaced in the UI without terminating gameplay.
- Emulator updates are checked at startup and every 24 hours during
  continued uptime, without unverified changes to signed app bundles.

Every test build runs a **30-second synthetic GUI soak** and uploads a
JSON memory/resource report to GitHub Actions. To run a longer soak on a
Mac development checkout with dependencies installed:

```bash
PYTHONPATH=. python3 tests/soak_gui.py --seconds 21600 \\
  --max-growth-mb 96 --report long-soak.json
```

On Linux, prefix the command with `xvfb-run -a` when no display is
available. The report measures resident memory after a warm-up and checks
that Tk image/callback counts and thumbnail caches stay bounded. This is
**synthetic**: it uses generated game video and camera frames, not an actual
N64/GameCube game or physical camera.

Before releasing 2.1, perform additional **4-hour and overnight tests with
real webcams and legally obtained test/homebrew ROMs** on macOS Apple Silicon,
Intel macOS, Windows and Linux. Record process memory, CPU use, controller
latency, audio continuity, save integrity, camera reconnection and close/
relaunch behavior. If steady-state memory keeps climbing, the release should
remain blocked until the responsible native component or UI resource is fixed.

## Known technical boundaries

This is an alpha. Runtime tests use synthetic camera frames and test cores;
physical webcam/graphics compatibility varies with installed emulators,
controllers and OS permissions. New NES/Genesis binary/source licensing and
cross-platform real-game smoke tests are required before public 2.1.
Do not move or overwrite the published 2.0.0 tag or replace its assets.

The GitHub project remains MIT-licensed only for its original application
source. FCEUmm is GPLv2; Genesis Plus GX is noncommercial; existing
Snes9x and mGBA keep their separate terms. Bundled new test cores are
development artifacts, not a general license to commercially redistribute
third-party emulator binaries.
