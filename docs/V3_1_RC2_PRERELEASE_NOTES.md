# Anything Plays 3.1 RC2 | Stream Mode, controller UI and live display bezels

**Release candidate for public testing. Not stable 3.1.0.** Anything Plays 3.0.0 remains the latest stable release. The installer set in this draft is intended to include **Windows x64, Linux x64, macOS Apple Silicon and macOS Intel**.

## New in 3.1 RC2

- **Stream Mode:** a separate, resizable OBS Window Capture display, styled like a dual-screen handheld. The live embedded game occupies the upper screen and the annotated camera occupies the lower one. Stream controls stay in their own window and are not visible to viewers.
- **Customizable stream appearance:** stacked or side-by-side display, swap game/camera positions, select any of the app's 16 themes, choose border color and thickness, change screen proportions, toggle labels, and select 15, 24 or 30 FPS. Layout persists in RC2 preferences.
- **Distinct camera and emulator bezels:** dedicated themed frames with truthful camera and game-session indicators.
- **Improved gamepad setup:** controller diagrams, responsive button feedback, analog hysteresis, optional mapping adjustments and privacy-conscious diagnostics.
- **Isolated RC2 installation:** distinct application IDs and native package names, with a separate RC2 settings directory. RC1 and stable 3.0 are not overwritten.
- **Preserved console lineup:** 18 console profiles using 11 original-source emulator core families, with offline downloads and no bundled game ROMs or firmware.

## What the CI tests prove

Each platform's exact full installer must be built from a pinned source commit and checksum-verified against the original public 3.0 emulator binaries. The application must be reinstalled from the finished installer, launch a genuine Tk desktop session, open and customize Stream Mode, draw a synthetic reference camera frame, close cleanly and prove that original RC1 and stable 3.0 settings remained unchanged.

This is **technical CI acceptance**, not a claim that every commercial game, controller, webcam, save, audio format or long gaming session has passed physical user testing. Users who encounter issues can file a GitHub issue with their operating system and app console profile.

## Third-party sources and rights

The original eleven emulator source trees and corresponding SHA-256 manifests are available at [Anything Plays 3.0 original sources](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources). Original pygame-ce and SDL source candidates and notices were gathered for the earlier [3.1 RC1 source review](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc1). The app source, build scripts and history are available in this GitHub repository.

**These sources do not yet constitute independently verified complete corresponding source for all compiled transitive libraries or confirmed LGPL user-relinking rights for every runtime.** The redistribution/source review remains open and must be resolved before treating 3.1 as production approved. Neither the CI run nor these notes give any new license permission.

## Installation limitations

Windows may display an unknown-publisher warning. macOS builds are ad-hoc signed and not notarized. Do not overwrite a working RC1 or 3.0 installation; RC2 is installed alongside them. Configure game audio capture separately in OBS. Externally launched emulator video (such as an external Dolphin session) is not automatically mirrored into Stream Mode; in that case it displays a truthful placeholder rather than an invented game frame.

No copyrighted ROMs, console firmware, BIOS, or games are included. Download and use only game content you have the right to run.

**Release approval:** Public candidate availability and stable 3.1.0 publication are separate decisions; do not mark the stable release accepted because RC2 package and synthetic CI tests passed.
