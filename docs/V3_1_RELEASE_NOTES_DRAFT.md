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
- **Live button tester:** View detected physical buttons and stick directions
  without starting a game. The tester is read-only, independent of remapping,
  and pauses its readout when Anything Plays loses focus.
- **Copy diagnostics:** Copy a local SDL/controller JSON report from the
  controller setup window without ROM filenames, personal paths,
  Bluetooth names or camera images. A separate feedback line confirms
  success without being overwritten by rapid gamepad status polling.
- **Atomic settings import:** The 3.1 candidate creates a
  complete private copy of existing preferences without overwriting
  stable 3.0 or a customized RC profile. Concurrent startup and
  symlink redirection are explicitly rejected or safely handled;
  verified both in [four-platform unit QA](https://github.com/MasynNay/anything-plays/actions/runs/42893632730) and
  [four-platform real installed-app QA](https://github.com/MasynNay/anything-plays/actions/runs/42895538165).
- **Rescan safety:** Immediately release held controller buttons on Rescan;
  malformed saved mappings are ignored instead of interrupting controller play.
- **Per-console remapping:** Choose face buttons, D-pad, both analog sticks,
  triggers, shoulders and menu buttons independently for each console.
- **Safer input:** Clear controller-only held buttons on disconnect, focus loss,
  emulator stop and mode change without releasing keyboard or camera input.
- **Cleaner settings:** Game Controls button, separate keyboard shortcut
  access from Step 8, and one control-label size slider near the preview.
- **Compatibility:** Intended to preserve all 18 console profiles and the
  eleven original-source native emulator cores from 3.0.

## QA evidence already available

**Newest verified development candidate (November 10, 2026):** The
updated 3.1 source app includes local Copy diagnostics, full
four-platform camera/controller integration tests, and persistent
clipboard feedback. [New source apps](https://github.com/MasynNay/anything-plays/actions/runs/42885525444) passed 4/4,
[full 18-console owner-QA installers](https://github.com/MasynNay/anything-plays/actions/runs/42886791394) passed
4/4, and [installed GUI boots](https://github.com/MasynNay/anything-plays/actions/runs/42887470580) passed 4/4.
[Pixel-tracking plus synthetic SDL input](https://github.com/MasynNay/anything-plays/actions/runs/42884824976)
passed on all four OSes with 18 profiles and 1,000 frames, while
[private controller report tests](https://github.com/MasynNay/anything-plays/actions/runs/42885687277)
passed four-platform clipboard and redaction checks.
All packages remain temporary nonrelease QA, and hardware, native
corresponding-source/LGPL and stable-release gates remain OPEN.


- Python 3.12 and 3.13 regression and Tk GUI smoke checks.
- Synthetic gamepad, button remapping, analog axis, disconnect and focus-loss
  tests on Linux x64, Windows x64, Intel macOS and Apple Silicon.
- Four minimal 3.1 Preview 1 test installers with checksum receipts, containing
  *only* GB/GBC/GBA support: [Preview 1](https://github.com/MasynNay/anything-plays/actions/runs/42822217817).
- Four **freshly compiled 3.1 RC1 application-stage builds** with isolated
  identities, verified on Windows, Linux and both macOS architectures:
  [native OS source-build run](https://github.com/MasynNay/anything-plays/actions/runs/42863846059).
- Four **full 18-profile/11-original-source-core RC1 QA installers** rebuilt
  around those freshly compiled apps (not frozen Preview 1), with exact
  core SHA-256 verification, frozen SDL audits and unapproved QA receipts:
  [full RC1 success 4/4](https://github.com/MasynNay/anything-plays/actions/runs/42865608433).
  [RC1 download/test instructions](V3_1_RC_QA_DOWNLOADS.md).
- Four verified older complete 18-console **QA packages** using exactly the
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
