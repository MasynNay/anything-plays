# Anything Plays 3.1 — Continue here

**Engineering checkpoint: November 11, 2026.** This concise entry is the
current handoff. Long-form verified history remains in
[V3_1_RELEASE_ACCEPTANCE.md](V3_1_RELEASE_ACCEPTANCE.md). Always retrieve
fresh GitHub run statuses and the release API before reporting publication.

## Public release state

- Stable [3.0.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0)
  remains public and untouched. Keep public 2.0 and 1.5 assets unchanged.
- [3.1.0 RC2](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc2)
  remains publicly available with 18 console profiles, the original eleven
  source-built core families, DS-style dual-screen Stream Mode, custom
  themes/borders and optional controllers. Owner installed the RC2 Linux DEB,
  launched the app and visually checked Stream Mode; the owner did **not**
  report testing a physical controller, real camera/OBS recording, save/audio
  or sustained retail gameplay.
- **No verified public stable `v3.1.0` exists yet.** Private authentic
  final-version QA binaries are not public release downloads.

## Fully completed native release engineering

- [PR #197](https://github.com/MasynNay/anything-plays/pull/197): Stream
  camera-disconnect stale frame privacy fix, merged.
- [PR #198](https://github.com/MasynNay/anything-plays/pull/198): Mac Bash
  packaging fix and complete four-platform Stream Mode QA, merged.
- [PR #199](https://github.com/MasynNay/anything-plays/pull/199): authentic
  3.1.0 app, installer and isolated settings identities; complete original
  core assemblies and installed desktop GUI acceptance, merged at
  `2b1567e86cb305a7bd10fc76c494d81b39aa77bd`.
- **Exact binary source revision:**
  `d852de9a513f83a329c14647ddc86bf3690fb5f5`.
- [Four-platform final native
  run 43120583726](https://github.com/MasynNay/anything-plays/actions/runs/43120583726):
  genuine final identity 4/4, 11 original-source cores and 18 console
  profiles in full installers 4/4, **actually installed frozen GUI/Stream
  Mode and RC2-to-final settings isolation 4/4 PASSED**.
- [Source/package checks
  43120583722](https://github.com/MasynNay/anything-plays/actions/runs/43120583722):
  Python 3.12/3.13, mGBA and all four desktop packages PASSED.
- [Private release stage
  43123263034](https://github.com/MasynNay/anything-plays/actions/runs/43123263034):
  source/receipt/SHA-256 verification PASSED and retained artifact
  `AnythingPlays-3.1.0-FINAL-FOUR-FULL-INSTALLERS-PRIVATE-REVIEW`
  (431 MB ZIP, four full packages, source pointer, QA manifest, checksums).
  Private artifact expires; check live retention before accessing it.

Exactly verified full filenames: `AnythingPlaysSetup-3.1.0.exe`,
`anything-plays-31_3.1.0_amd64.deb`,
`AnythingPlays-3.1.0-macos-arm64.dmg`,
`AnythingPlays-3.1.0-macos-x64.dmg`.
Do not substitute single-mGBA source shells or published RC2 files.

## Remaining stable-release gates

In `config/v3.1-release-readiness.json`, **2 of 6 gates have genuine passing
evidence**: 18-console installers and four-platform installed checks. The
remaining gates are **not certified**:

1. Real physical controller acceptance (and record real device/session
   limits rather than assuming synthetic input is sufficient).
2. pygame-ce, SDL, OpenCV and transitive native **redistribution review**
   for actual final frozen binaries.
3. Complete legally adequate corresponding sources, notices and applicable
   replacement/relinking path for those exact compiled dependencies. Earlier
   modified-source pygame C-extension swaps only verified **one component**.
4. Reviewed user-facing notes and live rollout readiness. The
   [3.1 release notes](V3_1_RELEASE_NOTES.md) and
   [publication runbook](V3_1_PUBLICATION_RUNBOOK.md) are ready for review;
   neither is proof that a release was published.

`public_release_approved` must remain `false` until these are honestly
resolved. The installed Macs are ad-hoc signed, not notarized.

## Exact next steps

1. Verify the final staging run and artifact still exist. Use the
   [publication runbook](V3_1_PUBLICATION_RUNBOOK.md) to recheck the exact
   four installer bytes and source SHA. Do not rerun the expensive full builds
   if verified artifacts are still retained.
2. Finish frozen-native library and source correspondence/relinking audit
   with component-specific notices and replacement instructions. Do not claim
   legal approval based on code-section comparisons or one successful
   `pygame.base` source rebuild. See
   [V3_1_SOURCE_COMPANION.md](V3_1_SOURCE_COMPANION.md).
3. Add grounded real-device/controller/optional gameplay test evidence or
   explicitly resolve remaining scope with project owner. Do not invent
   owner hardware testing.
4. Independently approve the notes, plan and remaining evidence and run
   `python -m tools.check_v31_release` successfully. Only then publish a
   `v3.1.0` **stable** GitHub Release containing the four complete matching
   installers, source and notices, and checksums. Confirm post-upload bytes
   and release API state; update README and
   https://anythingplays.masynnay.com/ only after public publication.

**This file is a checkpoint, not an authorization to bypass licensing,
release rights or missing real-device evidence.**
