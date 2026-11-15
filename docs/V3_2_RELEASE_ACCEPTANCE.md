# Anything Plays 3.2 — Feature-complete QA, public release still blocked

As of **November 15, 2026**, the 3.2 feature set is implemented on
[`feature/v3.2-integration`](https://github.com/MasynNay/anything-plays/pull/244).
The latest private full-native software and installer QA is green, but
**v3.2.0 has NOT been published, merged, or approved for distribution**.
The existing public [v3.1.1](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.1)
remains the stable application.

## Exact tested evidence

| Gate | Result |
| --- | --- |
| Source revision | `9f6950bc2a532375d2da5a6011571c9af11cf828` |
| Python 3.12/3.13, Tk and mGBA | [Run 43728173567](https://github.com/MasynNay/anything-plays/actions/runs/43728173567), passed |
| Linux/Windows/Intel Mac/Apple Silicon frozen installed apps | [Run 43728173563](https://github.com/MasynNay/anything-plays/actions/runs/43728173563), all four passed |
| Full-native inventory | 11 native core families, 18 console profiles |
| Linux bounded original / pinned homebrew software smoke | 18/18 positive profiles |
| Real physical webcam/controller, retail games and extended saves | Not verified |
| Independent 3.2 distribution/source approval | Not approved |

The private installed artifacts include separate full-native QA bundles for
`linux-x64`, `windows-x64`, `macos-arm64` and `macos-x64`. Their archived
GitHub Actions artifacts expire **November 22, 2026**, and contain exact-source
installer hashes and frozen-GUI receipts. They retain the separate 3.2 preview
installation identity and `anything-plays-32-preview` settings namespace.
**They are not a stable 3.1.1-to-3.2 upgrade.** No old saves or settings are
automatically imported, and no user ROMs or BIOS files are shipped.

The 18 homebrew positives come from bounded Linux native software programs,
not commercial games or hardware tests across every OS. GameCube's separate
native audio research produced nonzero PCM, but the combined homebrew release
matrix did **not** meet the headless 20 FPS threshold or validate physical
speaker output. Do not advertise universal compatibility or performance.

## 3.2 feature scope completed

The Get started launchpad, measured camera calibration/jitter guidance,
controller and keyboard onboarding/remapping, privacy-safe diagnostics,
portable single-console and 18-console controls backup/import/undo, reset
and Undo reset, per-console artwork, stored-profile rollback, and disarmed
camera/controller safety checks are implemented. Full package CI has passed;
source tests verify import/undo recovery under failed disk writes.

## Requirements before PUBLIC 3.2

1. Build and test the **real 3.2.0 stable upgrade identity** for all four
   operating systems, preserving the installed 3.1.1 settings, ROM libraries
   and progress. A side-by-side preview does not satisfy this gate.
2. Independently review full native-core redistribution rights, original
   notices, current Python/SDL/OpenCV runtime provenance, corresponding
   source/replacement rights, and finalized artifact SHA256 checksums.
3. Review real webcam/color tracking, USB/Bluetooth controller mapping,
   hotplug, keyboard-only play, and sustained legal-game/save testing on
   owner hardware. Report GameCube GPU/audio limits separately.
4. Obtain explicit approval of the **exact final tested source revision,
   final stable installer hashes, source companion, and release scope**.
   Publish a new version without replacing or deleting v3.1.1.

Machine-check the honest publication hold with
`python -m tools.check_v32_release_readiness --require-public-ready`.
The command intentionally fails until the evidence and all owner gates
in [`config/v3.2-release-readiness.json`](../config/v3.2-release-readiness.json)
are individually reviewed. A green CI badge never flips these flags.

[Full 3.2 QA release notes](releases/ANYTHING_PLAYS_V3_2_FULL_NATIVE_QA_NOT_RELEASE.md)
