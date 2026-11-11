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

The full eighteen-console native core assembly into uniquely versioned RC2 installers is a **separate, necessary next stage**. At present, the existing full-core RC1 assembler must **not** be used to repackage an RC2 source app or reuse the RC1 app ID. The previous PR #184 provides current-source nonrelease core-assembly QA but intentionally retained RC1 internal IDs for disposable tests. A future RC2 assembly must combine both the independently verified native cores and RC2's uniquely isolated settings/installer identity.

All six stable 3.1 public-release gates remain false, including complete native corresponding source/LGPL relinking, physical camera and controller acceptance, retail-game play/saves and final release approval. RC2 is not automatically approved or public because it uses distinct identifiers.
