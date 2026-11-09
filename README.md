<div align="center">

<img src="assets/anything_plays_v21.webp" alt="Anything Plays fish logo" width="120">

# Anything Plays

**If it moves, it plays.**

Turn real-world movement into video game controls with a webcam, customizable input zones, and a built-in game player.

**Windows · macOS · Linux**

[**Website**](https://anythingplays.masynnay.com/) · [**Download latest release**](https://github.com/MasynNay/anything-plays/releases/latest) · [**Roadmap**](ROADMAP.md) · [**Architecture**](docs/ARCHITECTURE.md) · [**Report an issue**](https://github.com/MasynNay/anything-plays/issues)

</div>

## See it in action

<div align="center">
  <img src="site/assets/anything-plays-desktop-preview.webp" alt="Actual Anything Plays desktop app showing a camera tracking grid, game library, console configuration, and volume controls" width="900">
  <p><em>A real capture of the packaged desktop application on Linux, not a browser mockup.</em></p>
</div>

## What it does

Anything Plays is an open-source desktop application that turns camera-detected movement into local emulator inputs. Track a fish, a toy, your hand, or another colored object. As it moves through your configured zones, Anything Plays presses the corresponding game buttons.

You can also play using your keyboard. The webcam is optional, and camera processing stays on your computer.

- **Camera-powered controls:** Track colored objects and assign their movement to game inputs.
- **Customizable layouts:** Arrange, resize, and remap zones; adjust button labels and save console-specific settings.
- **Game library:** Browse ROM folders with a visual shelf and remembered library locations.
- **Embedded emulation:** Play inside the desktop application without installing a separate RetroArch or Dolphin app.
- **Cross-platform desktop app:** Native installers for Windows, macOS Apple Silicon, macOS Intel, and Debian/Ubuntu Linux.
- **Local-first design:** No account or cloud connection is required to play your own games.

## Console support

The **3.0 application** has 18 console profiles powered by 11 native emulator cores.

| Family | Consoles |
| --- | --- |
| Nintendo handhelds | Game Boy, Game Boy Color, Game Boy Advance |
| Nintendo home consoles | NES, Super Nintendo, Nintendo 64, GameCube |
| Sega | Genesis / Mega Drive, Master System, Game Gear, SG-1000 |
| Atari | Atari 2600, Atari 7800 |
| NEC | TurboGrafx-16 / PC Engine (HuCard) |
| SNK | Neo Geo Pocket, Neo Geo Pocket Color |
| Bandai | WonderSwan, WonderSwan Color |

The selected 3.0 core lineup includes **mGBA, FCEUmm, Supafaust, BlastEm, ParaLLEl-N64, Dolphin, Tia, ProSystem, Beetle PCE Fast, NeoPop, and Beetle WonderSwan**. Source-built replacements remove historical noncommercial and obsolete emulator components from this lineup.

Game compatibility varies by emulator and computer. GameCube requires suitable graphics hardware. No commercial game ROMs or proprietary console firmware are distributed.

## Download and install

**[Get the latest published version from GitHub Releases](https://github.com/MasynNay/anything-plays/releases/latest)**

| Computer | Installer format |
| --- | --- |
| Windows (x64) | Setup `.exe` |
| macOS (Apple Silicon) | ARM64 `.dmg` |
| macOS (Intel) | x64 `.dmg` |
| Ubuntu / Debian (x64) | `.deb` |

GitHub Releases shows which versions are **actually public**. The stable **2.0** release remains available under [previous releases](https://github.com/MasynNay/anything-plays/releases/tag/v2.0.0). The 3.0 full-offline build and source review are tracked in the [roadmap](ROADMAP.md). Do not mistake a private development draft for a public download.

On macOS, builds may use ad-hoc signatures rather than Apple notarization. On Windows, installers may not have a commercial code-signing certificate. Verify releases and checksums before installation.

## Development

Anything Plays is built with **Python, Tkinter, OpenCV, NumPy, and Libretro**. The interface, video tracking, emulator lifecycle, audio, save handling, and per-console preferences live in separate modules. GitHub Actions tests and packages the application on all four build targets.

Use Python 3.12 or 3.13 with Tkinter:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p "test_*.py"
python app.py
```

To understand the implementation, start with [architecture](docs/ARCHITECTURE.md). For packaging, original emulator sources, test evidence, and build requirements, see the [technical documentation](docs/README.md). Contribution guidelines are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap and project status

Anything Plays is actively maintained. The [public roadmap](ROADMAP.md) summarizes completed milestones, verified 3.0 capabilities, current release work, and future improvements without burying the overview in CI logs.

If you encounter a bug, please [open an issue](https://github.com/MasynNay/anything-plays/issues) with your operating system, console, expected behavior, and reproduction steps. Please do not upload copyrighted game files, console firmware, or private camera footage.

## Licenses and acknowledgments

Original Anything Plays code is published under the [MIT License](LICENSE). Emulator cores and other embedded dependencies retain **their own upstream licenses and copyright notices**. The exact 3.0 source and licensing evidence is recorded in [the original-source assessment](docs/V3_0_EXACT_RUNTIME_LICENSE_SCOPE.md) and [distribution documentation](docs/V3_0_SOURCE_FIRST_RELEASE_DECISION.md).

Anything Plays is an independent portfolio and open-source project. It is not affiliated with Nintendo, Sega, Atari, SNK, NEC, Bandai, or the emulator teams. Bring only game files you are legally entitled to use.
