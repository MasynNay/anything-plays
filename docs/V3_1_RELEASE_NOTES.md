# Anything Plays 3.1.0 — Release notes

> **Ready-to-use release copy, not a published release.** These notes describe
> the version-correct private build that passed CI on November 11, 2026.
> Publish them with the `v3.1.0` GitHub Release **only after** the independent
> release acceptance and third-party licensing/source review is complete.
> At present the downloadable public 3.1 version remains
> [v3.1.0-rc2](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc2).

Anything Plays lets you control supported emulated games using colored objects
tracked through a camera, with optional keyboard and gamepad input. This update
focuses on better on-screen presentation, livestreaming, and controller setup,
without requiring a network service or bundled game files.

## What's new in 3.1.0

**Stream Mode — a finished-looking two-screen broadcast layout.** Open Stream
Mode beside **View mode**, or press **Ctrl+Shift+S**. A separate **Stream
Output** window composes the live built-in game display and the existing
annotated camera view into a Nintendo DS-inspired stacked presentation, with a
side-by-side option. Capture **Stream Output**, not **Stream Settings**, in
OBS Window Capture. Stream Mode supports swapping panes, custom bezel
thickness and color, all 16 application themes, pane proportions, labels and
15/24/30 FPS output refresh. Sources keep their aspect ratios when resized.

**Theme-matched screen housings.** The camera and game canvases have distinct
trim, subtle console-inspired details and accurate standby/activity status.
These bezels do not obscure or filter camera or emulator pixels.

**Safer camera disconnects.** The Stream Output camera pane now clears a stale
frame if a connected webcam stops or a status probe fails. Intentionally
selected reference photos remain available and are labeled as references,
rather than incorrectly presented as live video.

**Controller experience.** Optional SDL-based gamepad input for embedded
sessions, a visual controller mapping panel, live button/stick tester, input
diagnostics and more reliable recovery when a controller disconnects or input
enumeration fails. Controller mappings remain specific to a console; releases,
focus changes and emulator unloads clear controller-held buttons safely.

**A safe settings upgrade.** The 3.1.0 package has distinct application,
installer and preferences identities. On first launch, the app copies eligible
RC2 preferences into its own settings directory, retaining the original RC2,
RC1 and 3.0 files. Stable 3.0 and existing RC2 installations are not silently
replaced.

**Compatibility.** The full platform builds retain all 18 console profiles
and the eleven original source-built emulator core families used by public
3.0.0. No game ROMs, console firmware or copyrighted game images are included.

## Supported download files

| Operating system | Full 18-console installer |
| --- | --- |
| Windows x64 | `AnythingPlaysSetup-3.1.0.exe` |
| Linux x64 (Debian/Ubuntu) | `anything-plays-31_3.1.0_amd64.deb` |
| macOS Apple Silicon | `AnythingPlays-3.1.0-macos-arm64.dmg` |
| macOS Intel | `AnythingPlays-3.1.0-macos-x64.dmg` |

The release must also carry `SHA256SUMS.txt`, exact original source and
third-party license/access notices. **Do not download these filenames from a
GitHub Actions QA artifact and assume the public release exists.** The
files must appear on the actual `v3.1.0` GitHub Releases page after
publication has been independently confirmed.

## Test evidence and practical limitations

The [exact-version CI run
43120583726](https://github.com/MasynNay/anything-plays/actions/runs/43120583726)
passed four independently compiled final application identities, four full
18-console original-core installer assemblies and four *installed* Tk GUI,
Stream Mode and preferences-isolation acceptance suites on their native
operating systems. [Source checks
43120583722](https://github.com/MasynNay/anything-plays/actions/runs/43120583722)
passed Python 3.12/3.13, native mGBA and four-platform packaging. The
[private four-installer checksum bundle
43123263034](https://github.com/MasynNay/anything-plays/actions/runs/43123263034)
passed final matching of source, checksum and installed-app receipts.

These checks **are not** a substitute for testing every real USB/Bluetooth
controller, webcam, ROM, retail gameplay session, sound configuration,
save/restore or long-duration session. The project owner reported successful
real-Linux installation, launch and visual DS-style Stream Mode check for the
earlier public RC2, but did not report physical-controller testing.

Stream Mode presents the existing *built-in* emulator image. An externally
launched emulator with no built-in video source shows an honest placeholder.
Anything Plays does not stream, record or transmit content. OBS must handle
recording and audio capture separately. Hardware camera capture and OBS window
recording need to be evaluated on the target system.

macOS apps may be ad-hoc signed and not Apple-notarized; installation may
display normal unnotarized app warnings. Game availability and performance
depend on the emulator, platform, system and the user's legally acquired
software. The application's MIT license applies only to original project
code; bundled dependencies have their own licenses. See the accompanying
third-party notices and corresponding-source materials.

## Useful links

- [Project homepage](https://anythingplays.masynnay.com/)
- [Repository and source code](https://github.com/MasynNay/anything-plays)
- [Public RC2 prerelease](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc2)
- [Stable 3.0 and its source companion](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources)
- [3.1 release acceptance](V3_1_RELEASE_ACCEPTANCE.md)
- [Stream Mode guide](V3_1_STREAM_MODE.md)

**Publication constraint:** This copy is prepared for final review.
It does not declare that stable `v3.1.0` is already available or that
native dependency licensing, relinking, or the remaining physical-device
acceptance requirements have been completed.
