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
