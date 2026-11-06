<div align="center">
  <img src="assets/anything_plays.png" alt="Anything Plays logo" width="136">

  # Anything Plays

  **If it moves, it plays.**

  Turn everyday movement into a controller for classic video games.

  **Camera-powered play · Four consoles · Windows, macOS & Linux**

  [Releases](https://github.com/MasynNay/anything-plays/releases) ·
  [Get started](#get-started) ·
  [How it works](#how-it-works) ·
  [Report an issue](https://github.com/MasynNay/anything-plays/issues)
</div>

---

## Play a game. Let something else hold the controller.

Anything Plays follows a selected color through a webcam and translates movement
into gamepad buttons. Divide the camera view into zones, then let a toy, a fish,
a hand, or anything else you can track move between them. Each zone triggers a
button inside an embedded emulator—**not a system-wide keyboard event**.

Prefer a conventional controller? Click the game display and play using the
keyboard. A webcam is optional for manual play.

> **Version 2.0 status:** This is refactored release-candidate source, **not a
> published v2.0 installer**. Final package testing, exact third-party license
> compliance, and release approval are still required.

## Supported consoles

| Console | Accepted ROMs | Libretro core |
| :-- | :-- | :-- |
| Game Boy | `.gb` | Gambatte |
| Game Boy Color | `.gbc` | Gambatte |
| Game Boy Advance | `.gba` | mGBA |
| Super Nintendo | `.sfc`, `.smc` | Snes9x |

The console selector chooses the matching emulator automatically. Native cores
are downloaded and bundled **at build time** for packaged applications.
**No commercial game ROMs or BIOS files are distributed.** You supply your own
legally usable game files.

## Features

- **Color-tracked camera controls.** Choose a webcam and target color; adjust
  tolerance, minimum tracked area, camera mirroring, button duration, and cooldown.
- **Control zones built your way.** Draw rectangles in the video feed, fit
  active buttons to a balanced grid, disable individual mappings, or use a
  Shuffle zone that rearranges the visible controls.
- **Profiles for each console.** Independent control zones and mappings survive
  switching between Game Boy, Color, Advance, and SNES. Older settings migrate
  forward without resetting valid custom layouts.
- **A tactile ROM shelf.** Browse games by console in a horizontal library with
  locally rendered cartridge silhouettes and optional artwork stored alongside
  your ROMs. Drag, flick, or use Previous and Next.
- **Sixteen visual themes.** Choose light and dark palettes and customize the
  on-video labels, tint strength, outlines, and optional PNG zone artwork.
- **Keyboard play and game audio.** Play directly in the embedded display;
  camera controls can be paused without disabling manual input.
- **Local by design.** Tracking and gameplay run on your computer. The core
  downloader needs internet access only when building or preparing source.

## Get started

### Install a packaged application

Published builds will be listed on the
[GitHub Releases page](https://github.com/MasynNay/anything-plays/releases).
These **planned v2.0 filenames** must be verified against the final release:

| Platform | Planned artifact |
| :-- | :-- |
| Windows x64 | `AnythingPlaysSetup-2.0.0.exe` |
| macOS Apple Silicon | `AnythingPlays-2.0.0-macos-arm64.dmg` |
| macOS Intel | `AnythingPlays-2.0.0-macos-x86_64.dmg` |
| Ubuntu/Debian x64 | `anything-plays_2.0.0_amd64.deb` |

Packaged installations do not require separate Python setup. Windows builds are
currently unsigned and may prompt SmartScreen. macOS builds are ad-hoc signed
but not Apple Developer ID notarized, so Gatekeeper may require manual approval.
Use the published checksums to verify any downloaded installer.

### Run from source

Python **3.12** is the locally tested development version; the CI workflow also
checks Python 3.13. Install Tkinter and a compatible operating-system video
backend. On macOS, Homebrew users may need `python-tk@3.12`; on Ubuntu/Debian,
install `python3-tk`, `libgl1`, and `libportaudio2` if needed.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python fetch_mgba_core.py
python app.py
```

On Windows, create the environment with `py -3.12 -m venv .venv` and activate it
with `.venv\Scripts\activate`. On platforms where your configured Python isn't
named `python3.12`, use its actual executable. The downloader retrieves matching
native libraries from the Libretro buildbot; it also creates
`cores/CORE_PROVENANCE.json` with source URLs and SHA-256 hashes.

### The first five minutes

1. **Choose a console.** Pick GB, GBC, GBA, or SNES in the game panel.
2. **Choose a ROM folder.** The shelf displays files supported by that console.
3. **Open a game.** Click a cartridge or use *Open game ROM*.
4. **Choose how to play.** Click the game screen to use the keyboard, or start a
   webcam and click *Pick color from video* to sample the moving target.
5. **Enable object controls.** Arrange the control zones and choose *Enable
   object controls*. Press **Esc** or the prominent Stop button to halt camera
   input immediately.

Bright, even lighting and a target color that contrasts with its surroundings
produce the most reliable tracking.

### Manual keyboard controls

| Key | In-game button |
| :-- | :-- |
| Arrow keys | D-pad |
| Z / X | A / B |
| A / S | Y / X (SNES) |
| Q / W | L / R (GBA/SNES) |
| Enter | Start |

Click the game display first to give it keyboard focus. Select is available
through the on-camera mapping controls; this version does not assign it a
keyboard shortcut.

## How it works

```text
Camera frame ──► HSV color tracker ──► Zone hit test ──► Timed joypad input ─┐
                                                                           │
Focused keyboard ───────────────────────────────► Manual joypad input ─────┤
                                                                           ▼
ROM library ─► System/core selection ─────────────────────────────► Libretro worker
                                                                           │
                                                   ┌───────────────────────┤
                                                   ▼                       ▼
                                             RGB video frame            Game audio
                                                   │
                                                   ▼
                                              Tkinter display
```

The Tkinter event loop owns UI widgets and camera previews. A separate worker
owns the emulator core, including its callback pointers, save files, and frame
clock. Camera detection, audio queues, pixel conversion, and ROM discovery are
split into testable modules. See [ARCHITECTURE.md](ARCHITECTURE.md) for the design
and threading invariants.

## Develop and test

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py cameras.py cartridge_art.py core_locator.py \
    fetch_mgba_core.py gba_emulator.py libretro_*.py rom_library.py \
    settings_defaults.py system_profiles.py systems.py tracking.py \
    ui_*.py zone_rendering.py
```

On a Linux machine with Xvfb installed, you can also run the optional UI smoke
check without a physical monitor:

```bash
PYTHONPATH=. xvfb-run -a python tests/smoke_gui.py
```

The tests cover console profiles, source compatibility, tracking, button timing,
ROM discovery, cartridge artwork, audio buffering, video pixel formats, save
files, and a small synthetic Libretro native integration test on Linux. **They
are not a substitute for playing actual games with a real webcam on the target
platforms.** Use the [QA checklist](QA_CHECKLIST.md) before shipping.

### Build for your platform

| Host | Build command | Target |
| :-- | :-- | :-- |
| Windows | `build_windows.bat` | PyInstaller + Inno Setup installer |
| macOS | `bash build_macos_dmg.sh` | `.app` and DMG |
| Ubuntu/Debian | `bash build_linux_deb.sh` | `.deb` package |

Build on the target OS and architecture. The scripts download all three emulator
cores, package them with their provenance manifest, and fail if a required core
cannot be retrieved. **Nightly downloads are not pinned to a reproducible
revision**, even when SHA-256 values are recorded afterward. Platform installers
still require independent testing and a completed third-party licensing review.

A push of a version tag matching `v*` triggers the GitHub Actions release
workflow. **Do not create or push a release tag until the release has been
approved.**

## Settings and saves

To keep existing installations compatible, Anything Plays intentionally retains
its original preference location:

```text
~/.config/fish-plays-pokemon-studio/preferences.json
~/.config/fish-plays-pokemon-studio/system_profiles.json
```

Each console remembers its ROM folder and profile independently. Battery-backed
game progress is saved as `<rom-name>.sav` beside the source ROM. Back up your
ROMs, `.sav` files, and settings before replacing an installed build.

## Project resources

- [Architecture and module boundaries](ARCHITECTURE.md)
- [Pre-release QA checklist](QA_CHECKLIST.md)
- [Release candidate notes](RELEASE_NOTES.md)
- [Refactor and verification report](REFACTOR_REPORT.md)
- [Contributing guide](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Third-party components and licensing](THIRD_PARTY_COMPONENTS.md)

## Free, independent, and not yet licensed for redistribution

Anything Plays is intended to be **free of charge and non-commercial**, with no
advertisements, donations, or paid functionality. That describes the project's
intent; it does **not** automatically license the original source for reuse.
No license grant has yet been added for the project's original code.

The Gambatte, mGBA, and Snes9x cores carry their **own** licenses and
redistribution conditions. Snes9x is restricted to non-commercial use; other
cores may require notices and corresponding source availability. The effect of
integrating GPL-covered components with this application also requires review.
See [THIRD_PARTY_COMPONENTS.md](THIRD_PARTY_COMPONENTS.md). These obligations
must be resolved **before publicly distributing bundled installers**.

Anything Plays is an independent project and is not affiliated with or endorsed
by Nintendo, Pokémon, Libretro, Gambatte, mGBA, or Snes9x.
