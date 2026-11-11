# Anything Plays 3.1 — Truly separate RC2 installation identity

This is the **next release-candidate development lane**. It is not a public release.

The public 3.1 RC1 already exists and uses its own app identity. RC2 must be able to coexist with it and the stable 3.0 desktop program. The latest 3.1 bezel and controller improvements can then be tested without overwriting any existing installer.

## Four operating systems

| Target | RC2 identity |
| --- | --- |
| Windows x64 | Independent Inno Setup AppId 779FBB2F-1ACC-456E-A088-75D395CE98A3, its own Program Files folder, shortcuts and installer filename |
| Linux x64 | Debian package and launcher named anything-plays-31-rc2, separate /opt tree and .desktop entry |
| Mac Apple Silicon | AnythingPlays31RC2.app, CFBundleIdentifier com.anythingplays.rc31v2, separate arm64 DMG |
| Mac Intel | Same separate bundle ID with its own x64 DMG |

All embedded RC2 executables include the reviewed build identity in assets/v31_build_identity.json with channel rc2, display title Release Candidate 2, and private preferences namespace anything-plays-31-rc2. This prevents the RC2 app itself from silently reading/writing the RC1 preferences file.

When RC2 starts for the first time, it may copy existing RC1 preferences and console profiles into the new directory using the already existing atomic create-only migration. It never changes RC1 or stable settings. An existing RC2 file is preserved, and symlink destinations are refused.

## Build acceptance

The four-platform workflow v31-rc2-isolated-source-app.yml creates actual **mGBA-only source application shells**, not full eighteen-console installers. The real frozen app and installer are verified with tools.verify_v31_rc --channel rc2. Windows, Mac and Linux package identities must match the embedded application identity. Each source stage stores an exact Git revision, checksum and nonrelease status.

## Full eleven-core, eighteen-console RC2 technical builds

The same source-pinned workflow now has a second, native full assembly job on
**Windows x64, Linux x64, macOS Apple Silicon, and macOS Intel**. Each job
downloads its exact-platform source-stage RC2 installer from the same CI run
and the public 3.0.0 original-source core installer and SHA-256 manifest.
The private RC2 full assembler fails closed unless the original 3.0 digest,
exact source revision, RC2 staging status, isolated preferences namespace,
installer ID, and the eleven original-source core families agree. It reopens
and verifies the final generated installer rather than trusting the source
archive alone.

The resulting, separately identified output filenames are:

- Linux: `anything-plays-31-rc2_3.1.0~rc2full_amd64.deb`
- Windows: `AnythingPlaysSetup-3.1.0-rc2-full.exe`
- Apple Silicon: `AnythingPlays-3.1.0-rc2-full-macos-arm64.dmg`
- Intel Mac: `AnythingPlays-3.1.0-rc2-full-macos-x64.dmg`

These 30-day private GitHub Actions artifacts contain checksum receipts and
an SDL runtime audit; no upload to Releases is permitted. A failed Linux
runner cannot cause an unverified Linux artifact to appear, but its external
network failure also does not discard independently authenticated Windows
and macOS candidates.

**Do not infer a successful build merely from the workflow existing.** Each
platform's original-source native assembly, installed input initialization,
RC2 identity checks and final checksum must pass before any of these
installers is described as usable. The full package is still owner-only
QA, not a stable or publicly approved 3.1 release.

The earlier [PR #184](https://github.com/MasynNay/anything-plays/pull/184)
remains an independent historical RC1-identity current-source exercise,
and must not replace this isolated RC2 path.

All six stable 3.1 public-release gates remain false, including complete native corresponding source/LGPL relinking, physical camera and controller acceptance, retail-game play/saves and final release approval. RC2 is not automatically approved or public because it uses distinct identifiers.
