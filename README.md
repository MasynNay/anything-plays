<div align="center">

<img src="assets/anything_plays_v21.webp" alt="Anything Plays fish holding a handheld console" width="132">

# Anything Plays

**If it moves, it plays.**

Camera-powered games · Local, private controls · Windows, macOS and Linux

[Stable 2.0 download](https://github.com/MasynNay/anything-plays/releases/tag/v2.0.0) · [3.0 engineering status](ROADMAP.md) · [Code architecture](docs/ARCHITECTURE.md) · [Report an issue](https://github.com/MasynNay/anything-plays/issues)

</div>

## Release status

| Version | State | Details |
| --- | --- | --- |
| **2.0.0** | Published, stable | Original supported consoles; existing user installations are unchanged |
| **3.0.0 Preview** | **In development, not a public release** | 18 console profiles, 11 native cores in complete test installers; manual compatibility and compliance QA still required |

**3.0 is release-candidate engineering, not yet a public stable binary release.**
The [complete offline installer lab](https://github.com/MasynNay/anything-plays/actions/runs/42437133733)
passed on Windows x64, Linux x64, macOS Intel and macOS Apple Silicon. All
four developer installers contain **18 console profiles**, **11 Libretro cores**
and Dolphin system assets. The maintainer reports successful Linux GameCube
playback. The **Control label size** slider sits beneath the camera preview,
retains per-console settings and fits long names inside their own zones.

The remaining launch requirements are exact native source/license
compatibility, selected real-device/audio/endurance acceptance, and a
verified production release. The documented [GPL/noncommercial core
compatibility issue](docs/V3_LICENSE_COMPATIBILITY_GATE.md) must be
resolved before publishing the combined stable installer. Automated
packaging does not independently establish redistribution rights.
The [release evidence](docs/V3_DISTRIBUTION_READINESS.md) and
[continuation checkpoint](CONTINUE_HERE.md) track the exact state.

## What does Anything Plays do?

Select a color in the webcam feed, draw control zones and move an object
between zones to operate a game in the embedded player. Alternatively,
click the game view and use configurable keyboard controls. Webcam use is
optional. The application does not inject keys into other programs, and
camera processing happens locally.

## How version 3.0 distributes emulators

**Full offline developer preview:** [Four-platform test installers](https://github.com/MasynNay/anything-plays/actions/runs/42437133733) contain all **11 bundled native cores** for **18 console profiles** and the matched Dolphin system files. These are GitHub Actions artifacts for testing, **not approved public releases**; they are time-limited and may require a GitHub login. Neither RetroArch nor a separate Dolphin installation is required, and the packages include **no ROMs or BIOS**.

**Build variants:** Lightweight, mGBA-only application artifacts are for development diagnostics, not the planned stable 3.0 distribution. The intended stable 3.0 installer is the complete offline package with the already-selected emulator lineup. No separate RetroArch or Dolphin download is expected. Future in-app core updates remain optional and must use reviewed, verifiable packages.

The [3.0 distribution audit](docs/V3_DISTRIBUTION_READINESS.md), [draft notes](docs/V3_RELEASE_NOTES_DRAFT.md), and [package provenance records](config/v3.0-preview-candidate-integrity.json) are retained for review. The original emulator and Dolphin ZIP archives are preserved as test-only CI artifacts. No unapproved developer artifacts should be relabeled as stable 3.0 downloads.

## Console library plan

All eleven cores below are included in the **full offline 3.0 developer preview** on the four build targets. This inventory does **not** certify compatibility with every game or authorize public redistribution.

| Core | Console libraries | Readiness note |
| --- | --- | --- |
| mGBA | Game Boy, Game Boy Color, Game Boy Advance | Native gameplay tested; continue physical QA |
| Snes9x | Super Nintendo | Native gameplay tested; continue physical QA |
| FCEUmm | NES | Native audio/video verified with homebrew; continue real-device QA |
| Genesis Plus GX | Genesis, Master System, Game Gear, SG-1000 | Native homebrew acceptance implemented; real-device coverage pending |
| Stella 2014 | Atari 2600 | Native audio/video tests; real-game coverage pending |
| ProSystem | Atari 7800 | Native homebrew tests; real-device coverage pending |
| Beetle PCE Fast | TurboGrafx-16 / PC Engine HuCard | Native homebrew tests; real-device coverage pending |
| Beetle NeoPop | Neo Geo Pocket and Color | **Monochrome NGP audible-fixture coverage still incomplete** |
| Beetle WonderSwan | WonderSwan and Color | Native homebrew AV checks; real-device coverage pending |
| ParaLLEl-N64 | Nintendo 64 | **Repeat-launch fix** passed 3 cycles on four OS builds; owner tested switching on Apple Silicon |
| Dolphin Libretro | GameCube | Bundled in experimental preview; **GPU performance/real-game acceptance incomplete** |

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
