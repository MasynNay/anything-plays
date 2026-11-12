# Anything Plays 3.1.0

The 3.1 desktop release expands **Anything Plays** with Stream Mode, customizable camera and game display frames, and optional SDL gamepad controls. The application provides 18 console profiles using 11 emulator core families; games, ROMs and BIOS files are not included.

## What's new

- **Stream Mode:** Nintendo DS-inspired top-and-bottom or side-by-side layouts with independent camera/game arrangement, resizing, 16 appearance themes, bezel styling and 15, 24 or 30 FPS display options. Capture the **Stream Output** window in OBS. Anything Plays does not itself record or broadcast.
- **Camera and game display frames:** clearer, theme-aware borders and real status indicators.
- **Optional gamepad mapping:** per-console mappings, visual input preview and safe rescan/disconnect behavior, alongside the existing camera and manual controls.
- **Better handling of long sessions:** bounded preview work, cleared stale camera frames after disconnect, controller input release on focus changes and window cleanup.
- **3.1 preferences isolation:** keeps existing 3.0 and RC2 settings intact while copying RC2 settings on first 3.1 launch.

## Download the version for your computer

| Platform | Full installer |
| --- | --- |
| Windows x64 | `AnythingPlaysSetup-3.1.0.exe` |
| Ubuntu or Debian x64 | `anything-plays-31_3.1.0_amd64.deb` |
| macOS Apple Silicon | `AnythingPlays-3.1.0-macos-arm64.dmg` |
| macOS Intel | `AnythingPlays-3.1.0-macos-x64.dmg` |

Use `SHA256SUMS.txt` to verify download integrity. All four installers, the checksum list, `FINAL_QA_MANIFEST.json` and `FINAL_SOURCE_ACCESS_REVIEW.md` must match as one release set. **Do not mix earlier 3.1 preview or stock-OpenCV draft installer files with the clean 3.1 release.**

## Verification and source

The exact application source revision for these packages is [`104b96621ec4cb8dc39fde8c3fe96fc854c406ed`](https://github.com/MasynNay/anything-plays/tree/104b96621ec4cb8dc39fde8c3fe96fc854c406ed). [All 13 native source, full-installer and installed Stream Mode QA jobs passed](https://github.com/MasynNay/anything-plays/actions/runs/43140637755) on Windows x64, Linux x64, Apple Silicon and Intel Mac. [The final original-installer/source-wheel provenance stage](https://github.com/MasynNay/anything-plays/actions/runs/43142249044) verified the exact checksum and native wheel identity of each installer.

Each candidate uses an independently built camera-only OpenCV wheel with FFmpeg disabled. See [the exact OpenCV source archive, compile flags, Windows patch and reproduction instructions](https://github.com/MasynNay/anything-plays/blob/main/docs/V3_1_CLEAN_OPENCV_SOURCE_REPRODUCTION.md). Emulator source archives and notices are in the [3.0 source companion](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources). Other license-covered native libraries retain their own copyright and source obligations as documented in the published corresponding-source materials.

## Installation and limitations

This is a desktop application; a physical camera, gamepad and emulator compatibility depend on your hardware and operating system. Some external emulator views do not provide an embeddable game frame and display an explicit placeholder in Stream Mode. OBS handles recording and audio capture. On macOS the app is ad-hoc signed and not Apple-notarized; Windows binaries may not be publisher-signed.

Report reproducible issues in [GitHub Issues](https://github.com/MasynNay/anything-plays/issues). Existing stable 3.0 and 3.1 RC2 releases are retained for rollback.
