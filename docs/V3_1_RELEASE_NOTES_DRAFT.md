# Anything Plays 3.1.0 — Release notes (DRAFT, DO NOT PUBLISH)

**Development status:** Unreleased. This is a review copy, not a GitHub Release.
Do not mark 3.1 as stable until the acceptance criteria in
[V3_1_RELEASE_ACCEPTANCE.md](V3_1_RELEASE_ACCEPTANCE.md) are met.

## What's new

- **Physical controllers:** Optional, SDL-backed standard gamepad support for
  manual play in embedded emulator sessions, alongside camera input and
  keyboard controls. No system-wide keyboard injection or network dependency.
- **Visual configuration:** A compact controller card on the right of the game
  screen, with connection status, rescan, themed controller artwork and a
  dedicated visual mapping window.
- **Per-console remapping:** Choose face buttons, D-pad, both analog sticks,
  triggers, shoulders and menu buttons independently for each console.
- **Safer input:** Clear controller-only held buttons on disconnect, focus loss,
  emulator stop and mode change without releasing keyboard or camera input.
- **Cleaner settings:** Game Controls button, separate keyboard shortcut
  access from Step 8, and one control-label size slider near the preview.
- **Compatibility:** Intended to preserve all 18 console profiles and the
  eleven original-source native emulator cores from 3.0.

## QA evidence already available

- Python 3.12 and 3.13 regression and Tk GUI smoke checks.
- Synthetic gamepad, button remapping, analog axis, disconnect and focus-loss
  tests on Linux x64, Windows x64, Intel macOS and Apple Silicon.
- Four minimal 3.1 Preview 1 test installers with checksum receipts, containing
  *only* GB/GBC/GBA support: [Preview 1](https://github.com/MasynNay/anything-plays/actions/runs/42822217817).
- Four verified complete 18-console **QA packages** using exactly the
  published 3.0 original-source emulator binaries plus the frozen 3.1
  controller-enabled application:
  [Linux](https://github.com/MasynNay/anything-plays/actions/runs/42842903097),
  [Windows](https://github.com/MasynNay/anything-plays/actions/runs/42847847307),
  and [both macOS architectures](https://github.com/MasynNay/anything-plays/actions/runs/42843346985).
  All are temporary Preview 2 artifacts rather than final stable builds.
  [QA download and test instructions](V3_1_QA_DOWNLOADS.md).

The existence of builds and CI evidence is not evidence of real-world
USB/Bluetooth device compatibility or automatically sufficient licensing proof.

## Intended stable release assets — NOT YET AVAILABLE

The public 3.1 release should only contain actual version-correct installable
files, after exact source/binary and QA verification for all four targets:

- Windows x64 setup EXE
- Linux x64 Debian package
- macOS Apple Silicon disk image
- macOS Intel disk image
- SHA256SUMS.txt and original third-party corresponding-source access
- Notices covering mGBA, the original eleven-core lineup,
  pygame-ce/SDL and other compiled third-party libraries

Do not rename Preview 1/2 artifact files to 3.1.0 or promote an mGBA-only
package as the full release. Stable 3.0 must remain available.

## Known limitations to disclose

- Compatibility and performance depend on the computer and individual game.
- Controller support is available for embedded manual play, not a universal
  OS-wide virtual controller driver.
- Some native systems and games need dedicated save, audio and graphics checks.
- Physical USB/Bluetooth controller pairing and reconnect behavior are not
  certified by the synthetic four-platform test suite.
- Mac packages may be ad-hoc signed and unnotarized; installation warnings
  must be documented.
- No commercial games, ROMs or console firmware are distributed.

## Publication checklist

See [3.1 release acceptance](V3_1_RELEASE_ACCEPTANCE.md). Update this document
from measured final-release evidence, not from build intentions.
