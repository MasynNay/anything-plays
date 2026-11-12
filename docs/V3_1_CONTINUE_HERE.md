# Anything Plays 3.1.0 — CONTINUE HERE

**Maintainer-facing engineering checkpoint: November 11, 2026.**
Keep this file factual and current. This project has experienced interrupted
conversations and expensive duplicated native builds. Always inspect actual
GitHub Actions results before reporting a new pass or publishing an installer.

## Public release truth

- **Latest stable:** [v3.0.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0), original sources [v3.0.0-sources](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources). Do not touch stable 3.0, 2.0 or 1.5 assets.
- **Public 3.1 preview:** [v3.1.0-rc2](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc2). All 18 profiles and 11 emulator source-core families are present. It includes DS-inspired adjustable Stream Mode, themed screen bezels and optional controllers. The user reported installing and launching the Linux DEB and successfully viewing the Stream Mode layout. **No physical controller or full game/camera/audio/OBS recording test is implied.**
- **3.1.0 stable is NOT published.** Do not relabel the immutable old RC2 files as stable or misrepresent a private CI artifact as a public release.

## Verified post-RC2 engineering already merged

- [Camera-disconnect Stream Mode privacy fix #197](https://github.com/MasynNay/anything-plays/pull/197) merged. The unconnected webcam's stale last frame is cleared from the stream output rather than freezing.
- [Four-platform full-core QA and macOS Bash packaging fix #198](https://github.com/MasynNay/anything-plays/pull/198) merged. [Source checks 43094552640](https://github.com/MasynNay/anything-plays/actions/runs/43094552640) and [authentic 18-console installer + installed native GUI checks 43094552705](https://github.com/MasynNay/anything-plays/actions/runs/43094552705) **PASSED across Windows x64, Linux x64, macOS Intel, macOS Apple Silicon** for exact source revision `26fdc6cf9399ea0fd79665850089471f5ffec70d`. These packages still carry an isolated **RC2** QA identity and were never publicly promoted.
- [Final artifact provenance/staging gate #200](https://github.com/MasynNay/anything-plays/pull/200) merged in main as `e6767d3a420f4af0cec53bc5ba21b32e60b48923`. Python 3.12 and 3.13 source checks passed, including `test_v31_final_release_stage.py`. The read-only workflow `.github/workflows/v31-stage-final-four-reviewed-qa.yml` runs **only after** the new final workflow succeeds, downloads four complete installers plus four installed-GUI receipts, rejects mismatched bytes/false approvals, and preserves a **private** package/checksum bundle.

## Current 3.1.0 genuine-production-identity work — DO NOT RESTART FROM SCRATCH

- **Open PR:** [#199 — Actual four-platform complete 3.1.0 installers, 18 profiles, full installed GUI acceptance](https://github.com/MasynNay/anything-plays/pull/199).
- **Latest exact PR source head:** `d852de9a513f83a329c14647ddc86bf3690fb5f5` as of this checkpoint. Confirm the current PR head before checking or merging.
- **Native source-stage workflow:** [43116501433](https://github.com/MasynNay/anything-plays/actions/runs/43116501433). **Windows x64 PASSED, Linux x64 PASSED.** macOS Apple Silicon and Intel were **QUEUED at last check**, not failed. These source-stage builds contain mGBA only; do not call them full 18-profile distribution.
- **Companion source-check workflow:** [43116501551](https://github.com/MasynNay/anything-plays/actions/runs/43116501551). Python **3.12/3.13 regression tests PASSED**, native mGBA compatibility **PASSED**, Windows/Linux package checks **PASSED**. Both macOS packaging jobs were **QUEUED at last check**.
- **New root-cause fix (November 11, 2026):** [full 3.1.0 run 43114768325](https://github.com/MasynNay/anything-plays/actions/runs/43114768325) passed four actual 3.1.0 source identities, then exposed the same precise full-core failure on Windows, Linux and Intel Mac: `verify_bundle -> fetch_mgba_core.core_names_for_build` rejected the new `AP_V31_FINAL_CANDIDATE=1` identity as unrecognized. Fixed by `75f81205a6ea9f2bbb4e39c9f5abdaf5eb7467df`: require exactly one of Preview/RC1/RC2/final, retain no-production-flags and source-SHA constraints. Added adversarial regression tests in `d852de9a513f83a329c14647ddc86bf3690fb5f5`. [New exact-head native/full QA 43120583726](https://github.com/MasynNay/anything-plays/actions/runs/43120583726) has been started; **results were still pending at the checkpoint**. Do not merge or publish based on the older failed run.

- The prior PR head source checks found a **single stale test assertion** in `tests/test_v31_rc2_full_assembly.py` expecting a Windows full installer helper without `final=final`. Fixed by commit `ea08041a139301c00b7ff8655846a16ea3ebad01` and current Python 3.12/3.13 tests pass. Do not revert the correct new helper just to satisfy the old string.
- **New final-version identities:** Linux `anything-plays-31_3.1.0_amd64.deb` at `/opt/anything-plays-31`; Windows `AnythingPlaysSetup-3.1.0.exe` with distinct Inno AppId; Mac `AnythingPlays-3.1.0-macos-{arm64,x64}.dmg` with `com.anythingplays.release31` and `AnythingPlays31.app`. The embedded `final_candidate` identity migrates RC2 settings to `.config/anything-plays-31` by atomic copy-once, preserving RC2, RC1 and stable 3.0.
- PR #199's final workflow then builds **eleven original 3.0 source-core families** into each fresh actual-3.1.0 installer, audits original native hashes, launches the **actually installed** Tk/Stream Mode GUI on every native host and verifies three older user-setting namespaces unchanged. **These four full final candidate/installed jobs had NOT yet completed at this checkpoint.** No final QA success claim is authorized until all receipts pass.
- The `final_candidate` identity and private staging receipts deliberately have `public_release_approved=false`, `final_release_approved=false` and/or `stable_3_1_0_published=false`. Those are truthful technical QA markers, **not** a distribution grant. Do not change or ignore flags just to publish.

## Additional exact-head source verification, 11 November 2026

**Latest PR #199 source-check suite 43120583722 is GREEN 7/7 non-skipped jobs:** Python 3.12 and 3.13 unit/regression suites, native mGBA, Windows/Linux packaging and both Intel/Apple Silicon macOS package checks all completed successfully. The virtual-controller matrix entry was deliberately skipped. This verifies source and minimal packages, **not** the final 11-core full installers.

**Latest full 3.1.0 private identity run 43120583726:** genuine 3.1.0 Windows, Linux and Intel macOS source-stage installers **PASSED and uploaded source-stage artifacts**. Apple Silicon was queued at last check. This is 3/4 source stages, **not 3/4 full 11-core installers**. Full original-core assembly and final installed desktop jobs are **not yet verified** in this run. Never merge PR #199 based only on source stage or this checkpoint. [Run](https://github.com/MasynNay/anything-plays/actions/runs/43120583726).

## November 11 verified completion: genuine 3.1.0 draft with four installers

**PR #199 MERGED**: `2b1567e86cb305a7bd10fc76c494d81b39aa77bd` after the exact source SHA `d852de9a513f83a329c14647ddc86bf3690fb5f5` passed [all 13 final native jobs](https://github.com/MasynNay/anything-plays/actions/runs/43120583726): 4 original source-stage app identities, 4 complete 11-core/18-console native installers, 4 installed frozen Stream Mode/Tk settings-isolation jobs and 1 installed-receipt/fixture contract job. The companion [full source checks](https://github.com/MasynNay/anything-plays/actions/runs/43120583722) passed.

**Private four-platform release staging succeeded** at [run 43123263034](https://github.com/MasynNay/anything-plays/actions/runs/43123263034) from the *same exact QA run*, producing `AnythingPlays-3.1.0-FINAL-FOUR-FULL-INSTALLERS-PRIVATE-REVIEW` with four byte-matched verified binaries, manifest, source note and checksum.

**Private GitHub Release draft CREATED** by [run 43128235685](https://github.com/MasynNay/anything-plays/actions/runs/43128235685). Authenticated GitHub Releases API confirms `id=442346875`, `tag_name=v3.1.0`, `draft=true`, `prerelease=false`, `target_commitish=d852de9a513f83a329c14647ddc86bf3690fb5f5`, with **seven** exact assets: `anything-plays-31_3.1.0_amd64.deb`, `AnythingPlaysSetup-3.1.0.exe`, `AnythingPlays-3.1.0-macos-arm64.dmg`, `AnythingPlays-3.1.0-macos-x64.dmg`, `FINAL_QA_MANIFEST.json`, `FINAL_SOURCE_ACCESS_REVIEW.md`, and `SHA256SUMS.txt`. Owner-only link: https://github.com/MasynNay/anything-plays/releases/tag/untagged-293d7611aadb2e7f65f3.

**Do not redo full package builds just to stage installers. They are in the GitHub draft now.** Do not publish the draft until a genuine redistribution/source/relinking review is complete, physical-device acceptance requirements are resolved or explicitly documented and accepted, and the owner makes a final release decision. The formal manifest closes only 2 of 6 gates (`full_eighteen_console_installer`, `four_platform_full_installer_verification`). `public_release_approved` remains false. Stable `3.0`, public `3.1-rc2`, and the portfolio public stable link remain untouched.

## Native licensing/source review handoff

A consolidated exact-final-binary dependency review now lives in
[V3_1_NATIVE_DISTRIBUTION_REVIEW.md](V3_1_NATIVE_DISTRIBUTION_REVIEW.md).
It enumerates the final 3.1 installer filenames, upstream pygame/SDL and
eleven original-core source evidence, actual modified pygame C extension
replacement results across four operating systems, the unverified matching
native components and the specific tests/rights decisions required before
public publication. The [source candidate artifact run 42909893531](https://github.com/MasynNay/anything-plays/actions/runs/42909893531)
remains available; candidates are not full LGPL correspondence certification.
The private GitHub release draft and seven uploads have been independently
rechecked through authenticated releases API. **The public latest release is
still stable v3.0.0.** Keep both public RC2 and stable 3.0 untouched.

## Exact next actions

1. Inspect PR #199's current head and [the native full workflow](https://github.com/MasynNay/anything-plays/actions/workflows/v31-final-identity-private-qa.yml). If a job fails, read its exact GitHub job logs, fix source/test bugs and run exact-head checks again. A previous macOS error was an intermittent `upload-artifact@v4` backend failure (invalid HTML); retry only failed jobs after checking it is infrastructure, not application failure.
2. Require all four source stages, all four full 11-core/18-profile assemblies and all four **installed** frozen Stream Mode checks to pass before merging #199. Do not count a partial job matrix as all four.
3. The merged trusted final staging workflow can then collect four exact full binaries plus source/QA manifest and SHA256 sums as `AnythingPlays-3.1.0-FINAL-FOUR-FULL-INSTALLERS-PRIVATE-REVIEW`. Confirm its actual successful run and the contents; it is NOT a release.
4. Review third-party pygame-ce/SDL and OpenCV/FFmpeg transitive native notices, corresponding source and replacement/relinking obligations. The source-app revision, original 11 emulator sources, [six-source SDL/pygame candidate audit](V3_1_SOURCE_COMPANION.md) and [genuine modified pygame C replacement on all four OSes](V3_1_LGPL_ACTUAL_MODIFIED_PYGAME_WINDOWS_SOURCE_QA.md) are valuable but **not** complete native legal/source clearance.
5. The owner has personally validated Linux installation and the visual DS Stream Mode layout. Physical controllers, camera tracking, games, audio and long-session behavior still have unknown coverage. Treat these as documented known limitations/acceptance decisions, not invented passed tests.
6. Only after a truthful rights/source-first decision, exact production-version verified binaries, final notes and separate authorization should `v3.1.0` be published as **stable**. Preserve 3.0 and the RC2 prerelease. Update the portfolio and download links only after actual publication has succeeded.

**Do not treat a GitHub Actions run that is merely queued, partial, cancelled, or still running as successful. Never claim stable 3.1.0 is public without verifying the GitHub Release and all exact assets.**
