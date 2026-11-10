# 3.1 RC1 — source-built application QA stage

**Unreleased. Not the full 18-console candidate.** The four-platform
[RC1 source application workflow](../.github/workflows/v31-rc1-source-app.yml)
builds new PyInstaller executables **from the current 3.1 branch source**.
This removes the previously frozen Preview 1 executable as the foundation
for subsequent full-console release-candidate work.

## What the current stage proves

- Windows x64, Ubuntu/Debian Linux x64, macOS ARM64 and Intel build the
  application from their own native host environment.
- Build-time version identity is embedded as
  `assets/v31_build_identity.json` inside the frozen executable.
  The exact reviewed RC1 identity has version 3.1.0, an RC1 window title,
  `public_release_approved: false`, and a separate settings namespace.
  Missing metadata or a mismatch causes receipt verification to fail.
- Windows Inno Setup uses an RC-specific AppId and install directory,
  Linux uses a distinct Debian package, binary and desktop launcher,
  and macOS uses a distinct .app name and bundle identifier. **No
  stable v3.0 installed app or user preferences should be replaced.**
- The exact installer SHA-256, source commit and target are written to
  `RC1_APP_STAGE_RECEIPT.json`, with the report explicitly marking
  `final_release_candidate: false`.
- The workflow has read-only GitHub permissions and uploads only
  temporary seven-day QA artifacts. No tags or GitHub Releases can be made.

This source-build stage currently uses the mGBA-only
`AP_V30_MINIMAL_CORE_BUILD=1` mode, so it supports **GB/GBC/GBA only**.
Never call these four packages the final full-console RC or public 3.1.
They must subsequently be combined with all 11 separately verified
original-source native cores, and the finished installed packages
revalidated on every host.

## Full 18-console RC1 candidate pipeline (active QA)

The [full RC1 QA workflow](../.github/workflows/v31-full-rc1-qa.yml)
reuses only the **new source-built RC1 application artifacts** from run
[42863846059](https://github.com/MasynNay/anything-plays/actions/runs/42863846059),
pinned to source commit
`86baa6972ed923540f6ab49b636652a0f499d45c`.
It checks that run's exact source identity, verifies each target's
app SHA-256 receipt and the public 3.0.0 native release SHA-256,
then assembles all 11 original-source cores into isolated 3.1 RC1 packages.

The installed full packages are independently verified with native
emulation smoke checks, full core correspondence and the JSON SDL
license/runtime audit. The workflows emit temporary seven-day QA ZIP
artifacts **only when their full build jobs succeed**. Exact output names
include `rc1-full` or `rc1full`, and never claim to be public 3.1.0.

**Full RC1 source-built QA: PASSED all four platforms on November 10,
2026.** [GitHub Actions run 42865608433](https://github.com/MasynNay/anything-plays/actions/runs/42865608433)
verified installed native packages and preserved four temporary, checksummed
18-console/11-core QA artifacts: Windows x64, Linux x64, macOS Apple Silicon
and Intel. Every package pairs the freshly built 3.1 RC application with
unchanged verified public 3.0 original-source emulator cores and ships a
frozen SDL runtime inventory. [Owner downloads and test steps](V3_1_RC_QA_DOWNLOADS.md).

This is stronger release-candidate **engineering evidence**, not a green
light for publication. Real hardware/gameplay, complete SDL corresponding
source/relinking review, final stable-identity migration and owner signoff
are still pending. Stable public 3.0.0 and earlier 3.1 QA packages remain
unchanged.

## Next technical release gates

1. Receive all four RC1 source-build successes and inspect actual
   installers, identities, native notices and SHA-256 receipts.
2. Assemble and independently verify the full 18-profile/11-native-core
   3.1.0 RC installers without reusing the older Preview 1 app.
3. Verify correct stable upgrade/migration behavior separately from
   isolated candidate settings. Do not write into the stable user's
   preferences in an unreleased candidate.
4. Preserve actual wheel/native SDL and emulator corresponding-source
   materials, including applicable LGPL replacement and relinking
   instructions. A license text alone is insufficient.
5. Complete real controller, save/reload, graphics/audio, game switching
   and long-session acceptance, followed by fresh final 3.1.0
   stable-identity production builds and an explicit owner approval.

The stable public
[3.0.0 release](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0)
remains unchanged. Review development through
[draft PR #156](https://github.com/MasynNay/anything-plays/pull/156)
and [3.1 acceptance](V3_1_RELEASE_ACCEPTANCE.md).
