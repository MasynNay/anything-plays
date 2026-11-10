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

## What is still required before a full 3.1 stable release

- [ ] **Restore the full offline package:** all 18 profiles backed by
  the eleven reviewed, source-built emulator libraries from published 3.0,
  with their original upstream code, licensing notices, and Dolphin resources.
  Preview 1 deliberately bundles only mGBA for GB/GBC/GBA, so this gate is
  not met by the four successful preview installers.
- [ ] **Rebuild and exercise all four full installers:** installed app and
  native core hash checks, source correspondence, title and install identity,
  save/reload, N64/GameCube switching, native GUI/video/audio.
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

The next engineering milestone is a complete four-platform 3.1 release
candidate with all eleven native cores. A documented hardware test and
licensing review are then the remaining approval steps before publication.
