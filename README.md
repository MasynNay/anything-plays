<div align="center">

# Anything Plays

### If it moves, it plays.

**Turn real-world movement into Game Boy Advance controls with a webcam.**

[**Download v1.5.0**](https://github.com/MasynNay/anything-plays/releases/tag/v1.5.0) · [Report an issue](https://github.com/MasynNay/anything-plays/issues) · [Release notes](RELEASE_NOTES.md)

![Windows](https://img.shields.io/badge/Windows-supported-0078D4?logo=windows) ![macOS](https://img.shields.io/badge/macOS-Intel%20%26%20Apple%20Silicon-555555?logo=apple) ![Linux](https://img.shields.io/badge/Linux-Debian%2FUbuntu-FCC624?logo=linux&logoColor=black) ![Version](https://img.shields.io/badge/version-1.5.0-blue)

</div>

## What is Anything Plays?

Anything Plays is a desktop application that uses **OpenCV computer vision** to track a selected color in a camera feed. When the tracked object enters a configurable control zone, the app translates that movement into Game Boy Advance button presses using the **mGBA libretro core**.

A fish swimming in a tank, a moving toy, or any other suitably trackable object could become the controller. The app also includes manual controls, so you can explore it without a camera-controlled setup.

> **No fish required.** Anything Plays is designed around the movement of a trackable object, not a specific animal or device.

## Download and install

**You do not need to install Python to use the packaged releases.**

| Platform | Download | Getting started |
| --- | --- | --- |
| Windows (x64) | [Windows installer](https://github.com/MasynNay/anything-plays/releases/tag/v1.5.0) | Download `AnythingPlaysSetup-1.5.0.exe`, run the installer, then launch Anything Plays. |
| macOS (Apple Silicon) | [macOS DMG](https://github.com/MasynNay/anything-plays/releases/tag/v1.5.0) | Download the ARM64 DMG, open it, and install the app. |
| macOS (Intel) | [macOS DMG](https://github.com/MasynNay/anything-plays/releases/tag/v1.5.0) | Download the Intel/x86_64 DMG, open it, and install the app. |
| Debian/Ubuntu Linux | [Linux package](https://github.com/MasynNay/anything-plays/releases/tag/v1.5.0) | Download the `.deb` package and install it with your package manager. |

Find the files under **Assets** on the [v1.5.0 release page](https://github.com/MasynNay/anything-plays/releases/tag/v1.5.0).

**Important:** The builds are not commercially code-signed or notarized. Windows SmartScreen or macOS Gatekeeper may warn about an unrecognized developer. Only proceed if you trust the downloaded software. The release's `SHA256SUMS.txt` can be used to verify download integrity.

**Game files are not included.** Supply your own legally obtained, compatible GBA ROMs. No ROMs or BIOS files are distributed with this project.

## How it works

1. **Choose a camera** and view the live preview, or use manual controls to explore the app.
2. **Select a color** on the object you want to track.
3. **Arrange control zones** for directions and GBA buttons.
4. **Load a compatible GBA ROM** and start the embedded emulator.
5. **Move the object** through the camera's zones to trigger game inputs.

Tracking quality depends on lighting, color contrast, camera placement, and object movement.

## Features

- **Camera tracking:** Camera selection, live preview, color sampling, tracking tolerance, minimum object area, and mirroring.
- **Custom controls:** Editable zones for directional inputs, A, B, Start, Select, and Shuffle.
- **Flexible layouts:** Symmetric 3 × 3 preset, randomized zone positions, manual zone drawing, and Shuffle overlay.
- **Visual customization:** Zone labels, opacity, high-contrast/outline/minimal styles, and optional PNG artwork.
- **Built-in GBA gameplay:** Embedded mGBA libretro emulation and ROM shelf browsing.
- **Profiles and manual input:** Save/load JSON configurations and use keyboard controls.
- **Cross-platform packaging:** Automated release builds for Windows, macOS Intel, macOS Apple Silicon, and Debian/Ubuntu Linux.

## Project status

**v1.5.0 is the first public release.** The GitHub Actions source checks and platform builds passed, and the Windows installer was downloaded and launched successfully. The macOS and Linux release packages have not yet been independently verified from a clean download.

A recorded gameplay demonstration may be added in a future update.

## Technology

| Component | Technology |
| --- | --- |
| Desktop UI | Python + Tkinter |
| Camera and object tracking | OpenCV |
| Game emulation | mGBA libretro core |
| Native packaging | PyInstaller, Inno Setup, DMG and DEB build scripts |
| Automated builds | GitHub Actions |

## Run from source

For developers who prefer to run the Python application directly:

**Requirements:** Python 3.10+, Tkinter, and a compatible native mGBA libretro core. A camera is optional for manual play.

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

On Linux, install your distribution's `python3-tk` package if necessary. On macOS, use a Python distribution with Tk 8.6 or newer.

The app searches for a compatible core in `cores/`, packaged application directories, and standard RetroArch core locations. You can also select a core in the interface. Run `python fetch_mgba_core.py` to fetch a native core for your build host; this requires internet access and uses Libretro nightly builds.

## Build and test

Build packages on their target operating system. See `build_windows.bat`, `build_macos_dmg.sh`, and `build_linux_deb.sh` for platform-specific build procedures. The GitHub Actions workflows in `.github/workflows/` automate source checks and tagged release builds.

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py cameras.py gba_emulator.py fetch_mgba_core.py
```

These checks do not replace hands-on testing of camera permissions, ROM loading, tracking, controls, profiles, and installers.

## Configuration compatibility

To preserve existing user settings, Anything Plays retains the historical preferences path:

`~/.config/fish-plays-pokemon-studio/preferences.json`

Existing JSON profiles remain compatible, including defaults for older profiles missing Select or Shuffle zones.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidance and [SECURITY.md](SECURITY.md) for responsible vulnerability reporting. For bugs and feature requests, [open an issue](https://github.com/MasynNay/anything-plays/issues).

## Licensing and third-party components

**No license is currently granted for this repository's original source code.** Please do not assume it is open-source licensed until the project owner adds a `LICENSE` file. Third-party libraries, native emulator cores, and artwork may have their own licenses and redistribution requirements. Confirm redistribution rights before reusing bundled assets or distributing modified packages.

Anything Plays is an independent project and is not affiliated with or endorsed by Nintendo, Pokémon, or the mGBA project.
