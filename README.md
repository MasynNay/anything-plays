<div align="center">

<img src="assets/anything_plays_v21.webp" alt="Anything Plays fish holding a handheld console" width="132">

# Anything Plays

**If it moves, it plays.**

Camera-powered games · Local, private controls · Windows, macOS and Linux

[Latest stable release](https://github.com/MasynNay/anything-plays/releases/tag/v2.0.0) · [Version 3.0 development](https://github.com/MasynNay/anything-plays/tree/feature/v3.0-unified-test) · [Report an issue](https://github.com/MasynNay/anything-plays/issues)

</div>

## Release status

| Version | State | Details |
| --- | --- | --- |
| **2.0.0** | Published, stable | Original supported consoles; existing user installations are unchanged |
| **3.0.0 Preview** | **In development, not a public release** | New console libraries, small starter installer and optional in-app emulator downloads |

**3.0 preview is not finished.** CI verifies installation and embedded video/audio
for NES and Atari 2600 across four desktop architectures; N64 homebrew can draw
real video, but broader compatibility, physical audio and performance have not
been certified. **GameCube is experimental and not installable from the public
emulator catalog** until rendering, audio, controls, saves and stability pass.

## What does Anything Plays do?

Select a color in the webcam feed, draw control zones and move an object
between zones to operate a game in the embedded player. Alternatively,
click the game view and use configurable keyboard controls. Webcam use is
optional. The application does not inject keys into other programs, and
camera processing happens locally.

## How version 3.0 distributes emulators

Install the **small starter application** once. Game Boy, Game Boy Color and
Game Boy Advance work with the bundled **mGBA** core.

Choose a different console, then click **Download emulator** to install an
approved platform-specific core **inside Anything Plays**. The app verifies
GitHub release digests, core identity, package contents and approval records
before activating it. A downloadable core works offline after installation.
Shared console families reuse a single core. **No RetroArch or standalone
Dolphin installation is required for approved supported systems.**

Some consoles are not yet publicly downloadable because reviewed emulator
packs have not been published. The app will say so rather than install an
unreviewed third-party binary. GameCube deliberately shows
**In development** while its native renderer and matching system assets are
being validated. Game content and optional firmware are **never supplied**.

## Console library plan

| Core | Console libraries | 3.0 distribution |
| --- | --- | --- |
| mGBA | Game Boy, Game Boy Color, Game Boy Advance | Included with starter |
| Snes9x | Super Nintendo | Optional, pending pack approval |
| FCEUmm | NES | Optional; cross-platform audio/video and managed-install tests passed |
| Genesis Plus GX | Genesis, Master System, Game Gear, SG-1000 | Optional; validation in progress |
| Stella 2014 | Atari 2600 | Optional; cross-platform audio/video and managed-install tests passed |
| ProSystem | Atari 7800 | Optional; validation pending |
| Beetle PCE Fast | TurboGrafx-16 / PC Engine HuCard | Optional; validation pending |
| Beetle NeoPop | Neo Geo Pocket and Color | Optional; validation pending |
| Beetle WonderSwan | WonderSwan and Color | Optional; validation pending |
| ParaLLEl-N64 | Nintendo 64 | Optional; 3D gameplay compatibility still under testing |
| Dolphin Libretro | GameCube | **Blocked:** engine, Sys bundle and hardware validation incomplete |

The list describes recognized libraries and development scope, **not
guaranteed compatibility for every ROM**.

## Downloading a release

Use the [GitHub Releases page](https://github.com/MasynNay/anything-plays/releases).
A future 3.0 *application* release will present four prominent downloads:

- Windows x64: `AnythingPlaysSetup-3.0.0.exe`
- Mac with Apple Silicon: `AnythingPlays-3.0.0-macos-arm64.dmg`
- Mac with Intel: `AnythingPlays-3.0.0-macos-x64.dmg`
- Ubuntu / Debian x64: `anything-plays_3.0.0_amd64.deb`

A `SHA256SUMS.txt` is the fifth user-facing artifact. Reviewed emulator
packs live under a **separate 3.0 emulator-pack catalog release**, so they
do not clutter the main installer downloads. The release notes link to
source/license details, while the installers carry the required notices.
**These 3.0 filenames are planned; no stable 3.0 installers are published yet.**

## Repository layout

```text
anything-plays/
├── app.py                   # Desktop application entry point
├── anything_plays/          # Emulators, camera controls, UI, storage
├── assets/                  # Approved icons and art
├── packaging/               # Windows, macOS, Linux builds + installer script
├── tools/                   # Diagnostic, provenance and validation tooling
├── tests/                   # Unit, integration and native playback tests
├── config/                  # Fail-closed release acceptance records
├── licenses/                # Third-party notices distributed with the app
├── docs/                    # Architecture, release, QA and development guides
├── .github/workflows/       # Automated build and verification pipelines
├── fetch_mgba_core.py       # Core acquisition API, shared by CI and tooling
├── verify_bundle.py         # Cross-platform installation audit API
└── requirements*.txt        # Runtime and build dependencies
```

The core acquisition and bundle-verification entry points stay at the root
because existing Python tests, developer automation and release tooling
import them directly. Generated PyInstaller `.spec` files are not tracked.

## Developing

Use Python 3.12 or 3.13 with Tkinter. From the repository root:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p "test_*.py"
python app.py
```

Create a local 3.0 *starter preview* (not an approved public release) by
setting `AP_V30_MINIMAL_CORE_BUILD=1`, then running the build script for
your system:

```text
Windows:  packaging\build_windows.bat
macOS:    bash packaging/build_macos_dmg.sh
Linux:    bash packaging/build_linux_deb.sh
```

Test builds have independent installation identities and preference
directories so they cannot overwrite the published 2.0 application.

## Community and security

See [Contributing](CONTRIBUTING.md), [Security](SECURITY.md),
[Code of Conduct](CODE_OF_CONDUCT.md),
[Third-party licenses](docs/THIRD_PARTY_NOTICES.md) and the
[3.0 release organization policy](docs/V3_RELEASE_STRUCTURE.md).

Neither commercial game ROMs nor BIOS/firmware are supplied. Only use
game files you are entitled to run. No automatic public release is permitted
without a reviewed third-party source/license inventory and real packaged-app
verification.

Licensed under [MIT](LICENSE) for project-owned code; native emulator cores
retain their respective third-party licenses.
