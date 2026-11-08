# Anything Plays 3.0.0 — release notes (DRAFT)

> **NOT A PUBLIC RELEASE.** These notes are prepared for the final approved 3.0 assets. The current builds are test-only previews. Do not publish these notes as if the download links exist.

**If it moves, it plays.** Anything Plays is a local, camera-powered controller and retro-game desktop app. A webcam is optional: manual keyboard controls remain available.

## What's new in 3.0

- **Expanded built-in console library:** 18 console profiles powered by 11 native emulator cores; the full offline test installers contain the cores and Dolphin support files rather than requiring separately installed RetroArch or Dolphin.
- **Nintendo 64 and GameCube:** Embedded gameplay paths with improved restart handling and GameCube display pacing settings. Actual performance varies by GPU and game.
- **Camera controls:** Object-neutral color tracking, optional secondary color, optional multiple objects per color and local player assignments for compatible games.
- **Visible label-size control:** Resize the labels on the camera control zones with a slider on the left. Long labels now shrink to fit rather than overlap neighboring zones. Per-console size settings persist.
- **Audio and display:** Game-volume slider and mute, windowed, borderless and fullscreen modes.
- **Reliability:** Expanded source, simulator, native emulator and packaging regressions, including Linux installed-app and Dolphin Sys read-only behavior.

## Downloads — planned, not yet published

| System | Intended file |
| --- | --- |
| Windows x64 | `AnythingPlaysSetup-3.0.0.exe` |
| macOS Apple Silicon | `AnythingPlays-3.0.0-macos-arm64.dmg` |
| macOS Intel | `AnythingPlays-3.0.0-macos-x64.dmg` |
| Debian/Ubuntu Linux x64 | `anything-plays_3.0.0_amd64.deb` |
| Integrity verification | `SHA256SUMS.txt` |

Full application installers are planned to contain the complete supported emulator lineup, **no commercial ROMs or BIOS**, and third-party license/source-access materials. User-provided game files must be files the user is legally entitled to run.

## Known limitations and installation notes

- Camera and GPU capabilities vary by hardware; GameCube is more demanding than older systems.
- Some hardware and game compatibility remains unverified until documented in the final release report.
- Windows executables may be unsigned and Mac downloads may be ad-hoc signed rather than notarized. The final publication must state exactly which signing protections are present.
- Some emulator components have non-MIT licenses and source/access obligations. The app's own MIT license does not replace them. See [3.0 redistribution audit](V3_DISTRIBUTION_READINESS.md).

## Evidence and release approval

- [Four-platform offline installer test workflow](https://github.com/MasynNay/anything-plays/actions/runs/42426209611) passed, including an unprivileged Linux installed-app startup and read-only GameCube playback.
- Developer-branch source checks passed. User-reported Linux Dolphin playability is recorded in [Linux QA issue #25](https://github.com/MasynNay/anything-plays/issues/25).
- **Final approval is pending**: exact third-party license/source review, immutable production binaries, release acceptance and checksum publication.

Do not make this release public until `python tools/check_v30_release.py` passes with the documented evidence, and the final downloaded installers and required source assets are verified.
