# Anything Plays

**If it moves, it plays.** Camera-controlled Game Boy Advance gameplay for Windows, macOS, and Linux.

**Version:** 1.5.0 · **Interface:** Tkinter · **Tracking:** OpenCV · **Emulation:** mGBA libretro core

Anything Plays tracks a chosen color in a webcam feed, converts movement through configurable screen zones into GBA controls, and displays the game alongside the camera preview. Manual keyboard controls are also available.

## Features

- Webcam discovery and selection with live preview and color sampling.
- Configurable tracking tolerance, minimum object area, button hold, cooldown, and mirroring.
- Editable control zones for directional buttons, A, B, Start, Select, and Shuffle.
- Symmetric 3 × 3 preset, randomized zone positions, optional Shuffle overlay, and manual zone drawing.
- Zone labels, opacity, high-contrast/outline/minimal styles, and optional local or HTTPS PNG artwork.
- ROM shelf browsing, embedded GBA display, manual input, and JSON profile save/load.
- Independently scrollable interface panes.

## Run from source

Requires Python 3.10+ with Tkinter, a supported webcam (optional for manual play), and a native mGBA **libretro** core compatible with your operating system and CPU architecture.

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

On Linux, install your distribution's `python3-tk` package if Tkinter is unavailable. On macOS, use a Python distribution with Tk 8.6 or newer.

The app searches for a compatible core in `cores/`, packaged application directories, and standard RetroArch core locations. You can also choose a core in the interface. To download a core for your build host, run `python fetch_mgba_core.py`. This uses Libretro nightly builds and requires internet access. **No ROMs or BIOS files are supplied.** Use only game content you are authorized to use.

## Download and release

Published installers appear under the repository **Releases** tab after a `v1.5.0` tag build succeeds. GitHub Actions builds Windows setup, macOS Intel and Apple Silicon DMGs, and an Ubuntu/Debian package; it also generates SHA256 checksums. The automated builds are defined in `.github/workflows/release.yml`. See `RELEASE_NOTES.md` for release text. These are unsigned or ad hoc signed builds, not notarized commercial installers.

## Build installers

Build on the **target operating system**, not by cross-compiling. All build scripts download the native core first.

| Platform | Command | Expected output |
| --- | --- | --- |
| Windows x64 | `build_windows.bat` | `release/AnythingPlaysSetup-1.5.0.exe` (with Inno Setup 6); otherwise portable `dist/AnythingPlays/` |
| macOS arm64 / x86_64 | `chmod +x build_macos_dmg.sh && ./build_macos_dmg.sh` | `release/AnythingPlays.dmg` |
| Debian/Ubuntu Linux | `chmod +x build_linux_deb.sh && ./build_linux_deb.sh` | `.deb` under `release/` |

`build_macos_linux.sh` dispatches to the appropriate Unix build script. The included `AnythingPlays.spec` is retained for existing PyInstaller workflows; the platform scripts use their own PyInstaller arguments.

**macOS distribution:** The DMG script applies an ad hoc signature and sets the camera privacy usage description. Public distribution requires appropriate Developer ID signing and notarization. Verify Finder and Applications launches on a clean Mac.

**Windows distribution:** Install Python and Inno Setup 6 to produce the installer. Test installation, uninstall, and camera access on a clean Windows system.

**Linux distribution:** Install `python3-venv`, `python3-tk`, and `dpkg-dev` before running the Debian build script.

## Settings and profiles

The application intentionally retains the historical preferences path: `~/.config/fish-plays-pokemon-studio/preferences.json`. **Do not rename this directory** during upgrades: changing it would break existing ROM directory preferences. Saved JSON profiles remain compatible, including migration defaults for older profiles missing Select or Shuffle zones.

## Repository layout

```text
app.py                 Tkinter interface, camera tracking, settings, profiles
cameras.py             Cross-platform camera discovery
gba_emulator.py        ctypes libretro bridge and emulator worker
fetch_mgba_core.py     Download and validate native mGBA core
assets/                Application artwork and icons
cores/                 Placeholder for locally downloaded cores (not tracked)
tests/                 Source-level regression checks
build_*.sh / .bat      Native packaging workflows
installer.iss          Windows Inno Setup configuration
AnythingPlays.spec     Existing PyInstaller specification
requirements.txt       Runtime Python dependencies
```

## Publishing v1.5.0

Create an empty GitHub repository, upload/commit this source tree to `main`, then run:

```bash
git tag v1.5.0
git push origin main
git push origin v1.5.0
```

The tag starts the multi-OS build workflow. When every job passes, GitHub publishes the installers and checksums as a release. The workflow cannot be executed until the repository is pushed to GitHub. Check the **Actions** tab for any host-specific build failures.

## Testing and release checklist

Run `python -m unittest discover -s tests -v` and `python -m compileall -q app.py cameras.py gba_emulator.py fetch_mgba_core.py` for source-level checks. These do **not** replace native runtime validation. Before tagging a release, test camera permissions, detection, manual controls, profile round-trips, ROM loading, zone shuffling, and installer launches on Windows, macOS, and Linux.

## Distribution notes

- No ROMs, BIOS files, build outputs, or platform-specific core binaries are included in this source repository.
- The build fetcher downloads Libretro nightly binaries. For repeatable public releases, pin and verify a tested binary and check relevant redistribution licenses.
- The artwork in `assets/` is preserved from the supplied project; confirm you have redistribution rights before publishing publicly.
- **License:** No license has been granted in this repository. Add a license only after the copyright holder chooses one.
- **Verification:** The project owner reports native testing on Windows, macOS, and Linux. GitHub-hosted release builds remain unverified until the tag workflow completes.
