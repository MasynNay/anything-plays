# Source audit — Anything Plays 1.5.0

## Scope

Reviewed the four application Python modules, dependency manifest, assets, native core, packaging scripts, and existing documentation from the supplied v23 archive. Removed generated build directories, release binaries, the local virtual environment, and macOS resource forks from the publishable source tree.

## Changes applied

- Preserved camera discovery retry and backend behavior, but ensured the Linux camera-name file handle is closed deterministically.
- Added explanatory module/function documentation and normalized a few import/spacing conventions without changing public interfaces.
- Removed unused imports from the core downloader.
- Replaced the ignore rules to protect ROMs, native cores, build products, editor artifacts, and environments while **keeping** `AnythingPlays.spec` trackable.
- Added source-level regression tests for syntax, historical settings path, Select/Shuffle migration, and packaging-script presence.
- Rewrote README for GitHub, documenting setup, builds, limitations, compatibility, and release checklist.

## Compatibility preserved

- `app.py` entry point, module filenames, controls, camera settings, zone profiles, and native build scripts.
- Legacy preferences file: `~/.config/fish-plays-pokemon-studio/preferences.json`.
- Existing JSON profile loading and missing-zone migration.
- Core discovery and build-time Libretro download strategy.

## Open risks / follow-up validation

1. Native webcam, Tk, mGBA, and GUI integration cannot be verified by static tests alone.
2. macOS Finder startup behavior should be tested on a clean machine; the supplied history reports an initial crash/reopen sequence. No unverified startup change was introduced.
3. Nightly Libretro core downloads are not reproducible or pinned; confirm license terms and checksums before public distribution.
4. The source archive included a macOS `.dylib`, intentionally excluded from the GitHub-ready source ZIP; platform build scripts fetch the appropriate core.
5. Project artwork ownership/license needs confirmation before open-source publication.
6. The emulator's libretro callback and threading paths deserve native integration and stress testing.

## Verification

Run `python -m unittest discover -s tests -v` and `python -m compileall -q app.py cameras.py gba_emulator.py fetch_mgba_core.py`. No claim of successful native installer builds or live camera/emulator testing is made.
