# Anything Plays 3.1 — Four-platform QA downloads

**QA only. These are not public/stable 3.1 releases.**
All four installers are full 18-profile, 11-core test packages assembled from
the exact published 3.0 native emulator libraries and the controller-enabled
3.1 Preview 1. They are labeled Preview 2 and install separately from 3.0.
The embedded UI may still say Preview 1 because the application executable
comes from that frozen preview. They do not certify physical controllers,
game compatibility, or SDL redistribution approval.

## Download the artifact for your computer

1. Open the matching successful GitHub Actions run below.
2. Scroll to **Artifacts** (GitHub sign-in may be required).
3. Download the listed ZIP and extract the installer.
4. Compare the installer SHA-256 to the receipt JSON in the same ZIP.
   If it does not match, do not install.
5. The artifacts expire after 7 days; they are not permanent release assets.

| Computer | Successful run | Artifact ZIP | Installer inside |
| --- | --- | --- | --- |
| Linux x64 (Debian/Ubuntu) | [Run 42842903097](https://github.com/MasynNay/anything-plays/actions/runs/42842903097) | `AnythingPlays-3.1-FULL-18-Linux-QA-UNRELEASED` | `anything-plays-31-preview_3.1.0~preview2_amd64.deb` |
| Windows 10/11 x64 | [Run 42847847307](https://github.com/MasynNay/anything-plays/actions/runs/42847847307) | `AnythingPlays-3.1-FULL-18-windows-x64-QA-UNRELEASED` | `AnythingPlaysSetup-3.1.0-preview2.exe` |
| macOS Apple Silicon | [Run 42843346985](https://github.com/MasynNay/anything-plays/actions/runs/42843346985) | `AnythingPlays-3.1-FULL-18-macos-arm64-QA-UNRELEASED` | `AnythingPlays-3.1.0-preview2-macos-arm64.dmg` |
| macOS Intel | [Run 42843346985](https://github.com/MasynNay/anything-plays/actions/runs/42843346985) | `AnythingPlays-3.1-FULL-18-macos-x64-QA-UNRELEASED` | `AnythingPlays-3.1.0-preview2-macos-x64.dmg` |

For Debian/Ubuntu Linux, run from the extracted ZIP directory:

```bash
sudo apt install './anything-plays-31-preview_3.1.0~preview2_amd64.deb'
```

On Windows, run the Setup EXE and choose the separate preview installation.
On macOS, open the DMG and launch the `AnythingPlays31Preview.app` test app;
it is ad-hoc signed and not notarized by Apple, so use normal macOS security
controls if warned. Never disable system security globally.

## Quick acceptance checks

1. Confirm stable 3.0 still launches separately.
2. Launch the 3.1 QA app without a webcam or controller. Open the right-hand
   controller settings card and verify that its graphic, rescan and mapping
   dialogue work without throwing an exception.
3. Map a few keyboard controls, select GB/GBC/GBA and load a game you have
   the right to use. Verify that camera and keyboard input do not interfere.
4. Confirm full console selection, including N64 and GameCube. This verifies
   package availability, *not* that every commercial game will load.
5. If you have a controller, test connecting it after app launch, map A/B,
   D-pad, both analog sticks, triggers, and disconnect/reconnect while a
   game is loaded. Confirm held buttons stop after disconnect or focus loss.
6. Check a save/reload cycle and switching between two games on one console.
   Note exactly which OS/console/game was tested if reporting a failure.

**Do not publish or claim physical controller verification on the basis of
simulated devices.** Record observed behavior with the
[release acceptance checklist](V3_1_RELEASE_ACCEPTANCE.md) and
[review PR #156](https://github.com/MasynNay/anything-plays/pull/156).

The next stage is a proper 3.1.0 stable-identity build, its updated
corresponding-source package, exact four-platform checksums, and documented
physical-device acceptance. The current public release remains
[Anything Plays 3.0.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0).
