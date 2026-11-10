# Anything Plays 3.1 — Release acceptance

**Status: NOT READY FOR A STABLE RELEASE.** This document tracks evidence,
not a promise of a release date. Stable 3.0 stays public and untouched.

## What is already working

- [x] The 3.1 source branch includes Game Controls, per-console mapping,
  manual SDL gamepad input, and theme-aware controller settings.
- [x] Windows, Linux, Apple Silicon, and Intel Mac synthetic gamepad
  simulations passed through real input handling on
  [the four-platform run](https://github.com/MasynNay/anything-plays/actions/runs/42771771434).
- [x] Python 3.12/3.13 unit tests, real Tk GUI smoke, and native mGBA
  compatibility passed at
  [the latest 3.1 source run](https://github.com/MasynNay/anything-plays/actions/runs/42822880056).
- [x] Four *unreleased*, isolated 3.1 Preview 1 installers built and retained
  as **GitHub Actions artifacts**, not GitHub Releases:
  [the preview run](https://github.com/MasynNay/anything-plays/actions/runs/42822217817).
- [x] Each first preview provides checksum receipts and isolates installer
  identities and settings from stable 3.0.


## Four-platform full-library QA milestone: PASS (not a stable release)

All four isolated QA installers have passed native library identity checks
and packaging. Each contains the original 11 source-built emulator families
used by the publicly released 3.0.0 package, preserving the 18-console map,
alongside the 3.1 controller-enabled preview application. The input packages
and compiled cores are checked against their recorded SHA-256 values.

| System | Full 18-console QA run | Result |
| --- | --- | --- |
| Linux x64 | [42842903097](https://github.com/MasynNay/anything-plays/actions/runs/42842903097) | Passed; DEB installed and core hashes checked |
| macOS Apple Silicon | [42843346985](https://github.com/MasynNay/anything-plays/actions/runs/42843346985) | Passed; re-signed QA app and DMG contents verified |
| macOS Intel | [42843346985](https://github.com/MasynNay/anything-plays/actions/runs/42843346985) | Passed; re-signed QA app and DMG contents verified |
| Windows x64 | [42847847307](https://github.com/MasynNay/anything-plays/actions/runs/42847847307) | Passed; real Inno Setup install plus native DLL check in isolated process |

These are **Preview 2 QA binaries**, assembled from the exact published 3.0
native payload and frozen 3.1 Preview 1. They may still display "Preview 1"
inside the application; they are not an independently rebuilt 3.1.0 stable
release. They are retained as temporary Actions artifacts for 7 days.
[How to obtain and test them](V3_1_QA_DOWNLOADS.md).

The remaining stable release gates (physical controller hardware,
corresponding source for new SDL runtime, final native gameplay acceptance,
final reproducible installer builds, and exact release notes) remain open.
A green CI check does not replace those responsibilities.

## What is still required before a full 3.1 stable release

- [x] **Build full-library QA candidates:** all 18 profiles with the exact
  eleven native source-built cores from published 3.0, including Dolphin,
  their core manifests and licenses, verified on all four OS targets.
  **This closes packaging parity for QA only, not final stable approval.**
- [ ] **Final 3.1.0 stable rebuild and gameplay verification:** turn the
  verified source-built QA installers into true 3.1.0 native builds, confirm
  stable title and install identity, and exercise N64/GameCube game switching,
  save/reload, real native audio/video, and long-session behavior across all
  supported targets. Full-library QA package hashes are passed, but final
  stable identity and real-game end-to-end acceptance are not.
- [ ] **Actual controller testing:** at least one real USB or Bluetooth
  SDL-compatible gamepad on accessible hardware; test recognition,
  remapping, disconnect/reconnect, focus loss, startup/shutdown and
  keyboard/camera coexistence. Simulated devices prove logic, not HID drivers.
- [ ] **SDL/pygame-ce distribution review:** review LGPL-2.1-or-later
  notices, native wheel/SDL contents, original-source access, and
  applicable dynamic-library replacement/relinking obligations.
- [ ] **3.1 corresponding-source package:** preserve third-party emulator
  sources and newly bundled runtime source/attribution alongside release
  artifacts. Reusing a 3.0 source zip cannot by itself establish that new
  3.1 runtime components are covered.
- [ ] **Final release QA and documentation:** verify the actual four
  stable 3.1.0 installer hashes and update release notes, website, README,
  and post-release support/rollback instructions.

## Release constraints

The test artifacts are only valid for development and may expire. The current
public [3.0.0 release](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0)
has full offline console functionality; it must not be replaced by mGBA-only
3.1 Preview 1. **Neither a CI green check nor a GitHub draft PR is proof that
the untested physical controller or redistribution requirements are satisfied.**

The four-platform full-library packaging milestone is now complete.
The next steps are a final source-built **stable-identity** candidate,
real-game/physical-controller acceptance, and SDL/pygame-ce redistribution
review before any public stable release.
