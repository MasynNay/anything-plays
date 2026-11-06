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

> **Version 2.0 status:** The maintainer has completed functional testing of
> Windows EXE, macOS DMG, and Ubuntu/Debian DEB builds. The source is ready for
> integration into `main`, but public v2.0 installers remain withheld until
> third-party redistribution and corresponding-source requirements are resolved.

## Supported consoles

| Console | Accepted ROMs | Libretro core |
| :-- | :-- | :-- |
| Game Boy | `.gb` | mGBA |
| Game Boy Color | `.gbc` | mGBA |
| Game Boy Advance | `.gba` | mGBA |
| Super Nintendo | `.sfc`, `.smc` | Snes9x |

The console selector chooses the matching emulator automatically. GB, GBC and GBA
share the mGBA core while retaining independent game libraries and controls.
Native cores
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
split into testable modules. See [architecture guide](docs/ARCHITECTURE.md) for the design
and threading invariants.

## Repository structure

```text
anything-plays/
├── anything_plays/       Application, UI, tracking and Libretro adapters
├── app.py                Desktop application entry point
├── tests/                Unit, integration and headless UI tests
├── assets/               Branded artwork and application icons
├── licenses/             Third-party license texts
├── docs/                 Architecture, release notes and compliance tracking
│   └── history/          Archived development snapshots
├── .github/workflows/    Continuous integration and release build workflow
├── build_windows.bat     Windows installer
├── build_macos_dmg.sh    macOS disk image
├── build_linux_deb.sh    Debian package
├── fetch_mgba_core.py    Build-time Libretro downloader
└── verify_bundle.py      License-presence and core-integrity verification
```

The application logic is in the `anything_plays` Python package; `app.py`
remains the stable launcher. Files in `docs/history/` describe past development,
not the current build status. No ROMs, BIOS files or third-party core binaries
are committed to this repository.

## Develop and test

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py anything_plays fetch_mgba_core.py verify_bundle.py tests
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
platforms.** Use the [QA checklist](docs/QA_CHECKLIST.md) before shipping.

### Build for your platform

| Host | Build command | Target |
| :-- | :-- | :-- |
| Windows | `build_windows.bat` | PyInstaller + Inno Setup installer |
| macOS | `bash build_macos_dmg.sh` | `.app` and DMG |
| Ubuntu/Debian | `bash build_linux_deb.sh` | `.deb` package |

Build on the target OS and architecture. The scripts download both required emulator
cores, package them with their provenance manifest, and fail if a required core
cannot be retrieved. **Nightly downloads are not pinned to a reproducible
revision**, even when SHA-256 values are recorded afterward. Platform installers
still require independent testing and a completed third-party licensing review.

A version tag matching `v*` triggers the GitHub Actions build workflow.
**Automatic public publishing is disabled** until bundled-core redistribution
requirements are resolved. Do not create release tags prematurely.

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

- [Architecture and module boundaries](docs/ARCHITECTURE.md)
- [Pre-release QA checklist](docs/QA_CHECKLIST.md)
- [Release candidate notes](docs/RELEASE_NOTES.md)
- [Historical refactor report](docs/history/REFACTOR_REPORT.md)
- [Contributing guide](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Third-party components and licensing](docs/THIRD_PARTY_COMPONENTS.md)

## Free and open source

Anything Plays is intended to remain **completely free of charge**,
with no advertisements, donations, subscriptions, or paid functionality.

Original Anything Plays source code is made available under the
[MIT License](LICENSE), to the extent its contributors have the
right to license it.

The MIT License permits commercial reuse of MIT-covered code.
This does not change the project's commitment to providing
official releases free of charge.

### Third-party emulator licenses

Anything Plays uses independently developed emulator cores. Public binary
builds use mGBA for GB/GBC/GBA and Snes9x for SNES:

- **mGBA:** Mozilla Public License 2.0
- **Snes9x:** Custom noncommercial license

These components are not covered by the Anything Plays MIT License.
**Only the project's original MIT-licensed code is represented as open source
under MIT.** Because Snes9x has noncommercial restrictions, the complete
bundled installer must not be described as wholly OSI-approved open source.
Official Anything Plays downloads will nevertheless remain free of charge.

See [Third-Party Notices](docs/THIRD_PARTY_NOTICES.md) for attribution,
license information, and outstanding redistribution requirements.

**Bundled installers are not approved for public release until
third-party licensing and source distribution obligations have
been resolved.**

Anything Plays is an independent project and is not affiliated with or endorsed
by Nintendo, Pokémon, Libretro, Gambatte, mGBA, or Snes9x.
