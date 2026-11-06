# Anything Plays 2.0.0

**If it moves, it plays.** Anything Plays turns tracked real-world movement
into game controls, while also supporting ordinary keyboard play.

This release adds four classic console families, more flexible controller
zones, separate game shelves, themes and native desktop installers.

## Download the version for your computer

| Platform | Installer |
| --- | --- |
| Windows 10/11, x64 | `AnythingPlaysSetup-2.0.0.exe` |
| macOS Apple Silicon (M1/M2/M3/M4), arm64 | `AnythingPlays-2.0.0-macos-arm64.dmg` |
| macOS Intel, x86_64 | `AnythingPlays-2.0.0-macos-x86_64.dmg` |
| Ubuntu/Debian Linux, x64 | `anything-plays_2.0.0_amd64.deb` |

Download **one** installer for your system from this release's Assets
section. The included `SHA256SUMS.txt` allows you to verify the exact
downloaded file. All four were assembled and integrity checked on their
native operating systems; Linux and macOS installer payloads were inspected
after packaging. Physical webcam compatibility may vary by device.

## What's new in 2.0

- Game Boy, Game Boy Color and Game Boy Advance via the native **mGBA** core
- Super Nintendo via the native **Snes9x** Libretro core
- Separate ROM libraries, save handling, controller profiles and settings
  for each console
- Expanded configurable control zones, evenly sized grids, optional
  button disabling, and customizable visual layouts
- Sixteen application themes and console-specific ROM artwork
- Camera-based color tracking, manual keyboard controls, game audio and
  battery-backed saves
- Refactored and documented Python source with automated regression and
  platform packaging checks
- Cleaner FFmpeg-free OpenCV builds on all four platforms, preserving
  DirectShow, AVFoundation or V4L2 camera support while avoiding unneeded
  bundled FFmpeg/x264/x265 and Qt GUI libraries
- Linux packaging uses system PortAudio and excludes unused bundled
  Readline/JACK/ALSA/Berkeley DB libraries

The emulator libraries and source distributions are pinned by SHA-256. See
[release source and license information](https://github.com/MasynNay/anything-plays/blob/main/docs/RELEASE_SOURCE_ACCESS.md)
and [RC6 verification](https://github.com/MasynNay/anything-plays/blob/main/docs/RC6_VERIFICATION.md).

## Install and first launch

**Windows:** Run the `.exe` installer. This installer is not
Authenticode-signed; Windows SmartScreen may ask you to review it.

**macOS:** Open the DMG and copy `AnythingPlays.app` into Applications.
The app is ad-hoc signed but not notarized with an Apple Developer ID.
Gatekeeper may require you to approve the first launch in System Settings
→ Privacy & Security. Only approve software you obtained from this
project's official GitHub release.

**Ubuntu/Debian:** Install the downloaded DEB using the package installer,
or use `sudo apt install ./anything-plays_2.0.0_amd64.deb` to install its
system dependencies.

Anything Plays includes **no commercial game ROMs or BIOS files**. Supply
your own legally obtained compatible game images. A webcam is optional
if using keyboard input.

## Free use and third-party licenses

Anything Plays is distributed **free of charge**, with no advertisements,
subscriptions, donations, or other monetization. The original application
source is MIT-licensed, but **the full installer is not wholly MIT-licensed**.
Bundled mGBA is MPL 2.0; Snes9x has a **noncommercial license** and includes
a separately LGPL-licensed NTSC filter. The project's commissioned
artwork is separately rights-controlled. The full notices are included
inside the installers. Source snapshots of both emulator cores and
the source and patch for the custom OpenCV wheels are attached or linked
with the release.

The underlying emulator builds report precise upstream commits and their
archive bytes match the saved hashes. The upstream buildbot binaries have
not been independently reproduced from source; no reproducible-build
guarantee is made. Please respect each upstream project's license terms.
