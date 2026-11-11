# Anything Plays 3.1 — Continuation checkpoint

Verified November 10, 2026. Read this before continuing release or controller engineering.

## Published and tested

- Public 3.1 RC1 prerelease: https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc1
- Source code PR #156 merged to main; GitHub publication tag points to main source.
- Four real offline installers: Windows x64, Linux x64, macOS Apple Silicon and Intel.
- Eleven original-source emulator families / 18 console profiles in each RC1.
- Successful source-matched publication workflow: https://github.com/MasynNay/anything-plays/actions/runs/42920357069
- Successful four-OS full installer QA: https://github.com/MasynNay/anything-plays/actions/runs/42905694504
- Successful four-OS installed desktop/settings checks: https://github.com/MasynNay/anything-plays/actions/runs/42906122307
- Successful 180-second real Tk/SDL synthetic camera endurance: https://github.com/MasynNay/anything-plays/actions/runs/42909405091
- Original pygame/SDL tagged source candidates plus SDL notices:
  https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc1 (source companion ZIP).
- Latest stable remains public 3.0.0; 2.0 and 1.5 still public.

## Four-platform original pygame wheel swap and real desktop startup

**All four operating systems passed** limited upstream pygame extension
swap acceptance against genuine pinned full 3.1 RC1 installers. Linux
and Windows had byte-identical original native wheel bytes, and copied
installations passed actual frozen desktop Tk startup plus isolated
legacy settings tests: [two-platform workflow](https://github.com/MasynNay/anything-plays/actions/runs/42937982305).
Apple Silicon and Intel Mac copies replaced differently signed/thinned
compiled base extensions, were ad-hoc re-signed, loaded through the
actual Python native loader and passed frozen GUI startup:
[Mac workflow](https://github.com/MasynNay/anything-plays/actions/runs/42936779875).

These demonstrate practical installation layout and certain native
replacement mechanisms, **not modified-from-source LGPL binaries, complete
corresponding source, legal clearance or final 3.1.0 stable approval.**
[Full limitations and upcoming tests](V3_1_LGPL_FOUR_PLATFORM_UPSTREAM_REPLACEMENT_QA.md).

## New verified macOS LGPL native extension replacement test

The independent [macOS replacement workflow](https://github.com/MasynNay/anything-plays/actions/runs/42936779875) PASSED on both
Apple Silicon and Intel on genuine RC1 builds. A disposable app copy
received the exact SHA-verified official pygame-ce wheel's
`pygame.base` native extension; each copied app was ad-hoc
re-signed, passed a live native loader test, and successfully ran
the **actual frozen Tk desktop GUI smoke**. The readonly original
DMG remained unchanged. See
[step-by-step evidence](V3_1_LGPL_UPSTREAM_EXTENSION_REPLACEMENT_QA.md).

This verifies a practical **upstream ABI-compatible extension swap**,
not a recompiled user modification, complete LGPL compliance or
full native corresponding source. All six final 3.1.0 stable gates
and production release approval remain **false**.

## Verified signed macOS wheel code provenance — November 10, 2026

The original signed 3.1 RC1 Mac installers were independently compared
against official pinned pygame-ce and OpenCV wheels: **241/241** compiled
native `__TEXT,__text` sections matched. Apple Silicon: pygame **120/121**,
OpenCV SDL **1/1**; Intel: pygame **120/120**. These are *code section*
matches, not whole-file binary, corresponding-source or LGPL relinking
approval. [Two-Mac audit](https://github.com/MasynNay/anything-plays/actions/runs/42925583942) · [OpenCV follow-up](https://github.com/MasynNay/anything-plays/actions/runs/42926295393) ·
[Technical details](V3_1_SIGNED_MACOS_WHEEL_CORRESPONDENCE.md).

All six stable 3.1.0 gates and public final-release approval remain false.

## Release issue resolved

GitHub's Actions release creation 403 arose because a workflow token could
not target a feature commit that modified workflow files absent from main.
Use the default branch for unpublished draft creation, merge the exact
tested runtime source, then publish a prerelease targeted at main. This
worked. SHA256SUMS.txt was also adjusted to GitHub's normalized Linux
asset filename (tilde changed to dot), without changing installer bytes.

## Remaining true stable 3.1.0 requirements

- Real USB/Bluetooth controller tests, unplug/rescan/focus behavior and
  saved-game/audio/camera compatibility on final installer hardware.
- Review complete SDL/pygame corresponding-source provenance, transitive
  notices and LGPL native library replacement/relinking instructions.
- Produce actual final 3.1.0 stable installer identity on all four OS
  targets; do not simply rename the RC1 binaries.
- New final stable installer and source receipts with checksums, real
  installed testing, and reviewed release notes.
- Once independently accepted, create stable 3.1.0 release and update
  the latest stable link. Do not overwrite 3.0 or 2.0.

Stable release manifest: config/v3.1-release-readiness.json. All six stable
gates remain false while final work is open. A public RC1 prerelease
does not satisfy stable acceptance.
