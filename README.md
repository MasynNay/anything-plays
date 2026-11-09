<div align="center">

<img src="assets/anything_plays_v21.webp" alt="Anything Plays fish holding a handheld console" width="132">

# Anything Plays

**If it moves, it plays.**

Camera-powered games · Local, private controls · Windows, macOS and Linux

[Website](https://anythingplays.masynnay.com/) · [Stable 2.0 download](https://github.com/MasynNay/anything-plays/releases/tag/v2.0.0) · [3.0 engineering status](ROADMAP.md) · [Code architecture](docs/ARCHITECTURE.md) · [Report an issue](https://github.com/MasynNay/anything-plays/issues)

</div>

## Release status

| Version | State | Details |
| --- | --- | --- |
| **2.0.0** | Published, stable | Original supported consoles; existing user installations are unchanged |
| **3.0.0 Preview** | **In development, not a public release** | 18 console profiles, 11 native cores in complete test installers; manual compatibility and compliance QA still required |

**3.0 is working development software, not yet a licensed public stable binary release.**
The most recent **ten-original-source-core** [complete offline installer lab](https://github.com/MasynNay/anything-plays/actions/runs/42535823260)
passed on Windows x64, Linux x64, macOS Intel and macOS Apple Silicon. These
four test-only developer installers contain **18 console profiles**, **11 native
Libretro core families**, and bundled Dolphin Sys assets, with no separate
emulator installation. Ten core families are compiled from pinned original
sources; **Dolphin is the remaining family using an archived native binary**.
The developer also personally confirmed working N64 games and repeated ROM
switching, plus working Dolphin/GameCube gameplay on Windows, macOS and Linux
following the Linux installation fix. These confirmed observations do not
establish the right to redistribute the combined binaries.
The **Control label size** slider sits beneath the camera preview, retains
per-console settings and fits long names inside their own zones.

The remaining launch requirements are exact native source/license
compatibility, selected real-device/audio/endurance acceptance, and a
verified production release. The required [Neo Geo Pocket 11-job
native acceptance run](https://github.com/MasynNay/anything-plays/actions/runs/42451407552)
passed for genuine monochrome and color on all four operating systems.
That is original homebrew/Libretro callback evidence, **not** a physical
retail-game test. [Issue #41](https://github.com/MasynNay/anything-plays/issues/41)
is closed; [release issue #28](https://github.com/MasynNay/anything-plays/issues/28)
remains open. Testers can record actual installation, game video, audible
sound, camera actions, save/reload and endurance using the [private, offline
physical QA checklist](docs/V3_PHYSICAL_QA_RUNBOOK.md). The documented [GPL/noncommercial core
compatibility issue](docs/V3_LICENSE_COMPATIBILITY_GATE.md) must be
resolved before publishing the combined stable installer. Automated
packaging does not independently establish redistribution rights.
The [release evidence](docs/V3_DISTRIBUTION_READINESS.md) and
[continuation checkpoint](CONTINUE_HERE.md) track the exact state.
The newest complete test-only installers were independently rehashed against
their SHA-256 manifests on all four architectures at commit
`7004115e7b9d57a3ef8f44062e134a3b55410f25`.
[Private owner hardware QA instructions](docs/V3_PHYSICAL_QA_RUNBOOK.md)
include a [frozen four-installer fingerprint catalog](config/v3.0-owner-qa-preview-hashes-unapproved.json)
for that exact test build. No public distribution approval or physical gameplay
has been inferred from these build checks.

## What does Anything Plays do?

Select a color in the webcam feed, draw control zones and move an object
between zones to operate a game in the embedded player. Alternatively,
click the game view and use configurable keyboard controls. Webcam use is
optional. The application does not inject keys into other programs, and
camera processing happens locally.

## How version 3.0 distributes emulators

**Full offline developer previews:** The [original full four-platform test build](https://github.com/MasynNay/anything-plays/actions/runs/42455076101) contained all 11 native core families and bundled Dolphin Sys for 18 profiles. A subsequent [ten-original-source-core full native lab](https://github.com/MasynNay/anything-plays/actions/runs/42535823260) passed on all four platforms with the noncommercial SNES/Sega libraries replaced by original source-built alternatives, and original source-built N64 and mGBA cores. These are **different development candidates**, not approved public releases or interchangeable production downloads. The ten-core research run retains diagnostic evidence; do not assume its installation files are offered as a public release. Neither approach requires end users to separately install RetroArch or Dolphin. No ROMs or BIOS are bundled.

**Build variants:** Lightweight, mGBA-only application artifacts are for development diagnostics, not the planned stable 3.0 distribution. The intended stable 3.0 installer is the complete offline package with the already-selected emulator lineup. No separate RetroArch or Dolphin download is expected. Future in-app core updates remain optional and must use reviewed, verifiable packages.

The [3.0 distribution audit](docs/V3_DISTRIBUTION_READINESS.md), [draft notes](docs/V3_RELEASE_NOTES_DRAFT.md), and [package provenance records](config/v3.0-preview-candidate-integrity.json) are retained for review. The original emulator and Dolphin ZIP archives are preserved as test-only CI artifacts. No unapproved developer artifacts should be relabeled as stable 3.0 downloads.

## Console library plan

The table below describes the **most recently tested ten-original-source-core full 3.0 experimental installer** (18 profiles, 11 native families). Older full previews instead used Snes9x and Genesis Plus GX for SNES and Sega. Both variants are **test-only**. This inventory does not certify every game or authorize redistribution.

| Core | Console libraries | Readiness note |
| --- | --- | --- |
| mGBA | Game Boy, Game Boy Color, Game Boy Advance | Native gameplay tested; continue physical QA |
| Mednafen Supafaust | Super Nintendo | Original pinned source-built replacement for Snes9x; real original homebrew audio/video CI on four OS |
| FCEUmm | NES | Native audio/video verified with homebrew; continue real-device QA |
| BlastEm | Genesis, Master System, Game Gear, SG-1000 | Original pinned source-built replacement for Genesis Plus GX; four Sega paths checked in native CI |
| Stella 2014 | Atari 2600 | Native audio/video tests; real-game coverage pending |
| ProSystem | Atari 7800 | Native homebrew tests; real-device coverage pending |
| Beetle PCE Fast | TurboGrafx-16 / PC Engine HuCard | Native homebrew tests; real-device coverage pending |
| Beetle NeoPop | Neo Geo Pocket and Color | Authentic monochrome and color native audio/video/input CI passed all four OSes; physical game/saves still need validation |
| Beetle WonderSwan | WonderSwan and Color | Native homebrew AV checks; real-device coverage pending |
| ParaLLEl-N64 | Nintendo 64 | Source-built original N64 native video passed four OS; maintainer confirmed gameplay and repeated ROM switching |
| Dolphin Libretro | GameCube | Owner confirmed working on Windows, macOS and Linux; original source-to-distributed-binary correspondence and license review remain pending |

See [3.0 engineering status](ROADMAP.md) and [#24](https://github.com/MasynNay/anything-plays/issues/24) for the distinction between implemented code, native homebrew diagnostics and release approval.

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
import them directly. Generated PyInstaller `.spec` files are not tracked. CI also enforces a clean root and excludes generated installers, third-party emulator binaries, and game ROMs through the [repository hygiene checker](tools/check_repository_hygiene.py).

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

See the [3.0 engineering status](ROADMAP.md) and open [3.0 tracking issues](https://github.com/MasynNay/anything-plays/issues) for current work.

See the [documentation index](docs/README.md), [workflow guide](.github/README.md), [Contributing](CONTRIBUTING.md), [Security](SECURITY.md),
[Code of Conduct](CODE_OF_CONDUCT.md),
[Third-party licenses](docs/THIRD_PARTY_NOTICES.md) and the
[3.0 release organization policy](docs/V3_RELEASE_STRUCTURE.md).

Neither commercial game ROMs nor BIOS/firmware are supplied. Only use
game files you are entitled to run. No automatic public release is permitted
without a reviewed third-party source/license inventory and real packaged-app
verification.

Licensed under [MIT](LICENSE) for project-owned code; native emulator cores
retain their respective third-party licenses.
