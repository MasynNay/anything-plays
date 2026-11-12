# Anything Plays 3.1.0 — CONTINUE HERE

**Maintainer-facing engineering checkpoint: November 11, 2026.**
Keep this file factual and current. This project has experienced interrupted
conversations and expensive duplicated native builds. Always inspect actual
GitHub Actions results before reporting a new pass or publishing an installer.

## Latest verified technical state — fresh clean 3.1.0 installers

**TWO complete, genuine source-built FFmpeg-disabled 3.1.0 installers passed
native full 18-console assembly and installed Tk/DS Stream Mode QA:**

- **Linux x64:** [PR #212](https://github.com/MasynNay/anything-plays/pull/212)
  MERGED, [Actions 43136053895](https://github.com/MasynNay/anything-plays/actions/runs/43136053895)
  PASS. Private `AnythingPlays-3.1.0-LINUX-FULL-18-CAMERA-ONLY-NEW-BUILD-QA-PRIVATE`.
- **macOS Apple Silicon:** [PR #215](https://github.com/MasynNay/anything-plays/pull/215)
  MERGED, [Actions 43138729334](https://github.com/MasynNay/anything-plays/actions/runs/43138729334)
  PASS. Private `AnythingPlays-3.1.0-MACOS-ARM64-FULL-18-CAMERA-ONLY-NEW-DMG-PRIVATE-QA`.
  This used the genuinely newly source-built Apple Silicon wheel from
  [PR #213](https://github.com/MasynNay/anything-plays/pull/213), with FFmpeg/AVIF off,
  AVFoundation camera backend proven, and verified the real ad-hoc signed/mounted
  full 18-console GUI, Stream Mode and isolated first-run preferences.

**Next-platform full package workflows are safely staged as branches, but NOT yet
verified or released:** `qa/v31-windows-full-clean-opencv-exe` contains
`.github/workflows/v31-windows-full-source-opencv-qa.yml`; and
`qa/v31-macos-intel-full-clean-opencv-dmg` contains
`.github/workflows/v31-macos-intel-full-source-opencv-qa.yml`. Both are
prepared to consume independent pinned native source-built wheels, reassemble
11 original-source cores/18 console profiles, inspect the real finished
EXE/DMG and run installed frozen Tk/Stream Mode plus settings-isolation checks.
Do **not** create their PRs before the supplier wheel runs below pass and
retain their original artifacts; absent source-wheel evidence is a hard
stop. Windows workflow passes native Windows paths into the CMD builder.
These two staged source branches are *not* successful installer QA yet.

**Still active, DO NOT CLAIM PASSED until current job results confirm:**
- **Windows:** [PR #214](https://github.com/MasynNay/anything-plays/pull/214);
  original published 2.0 setup.py patch headers corrected in the workflow,
  exact-head [run 43138596964](https://github.com/MasynNay/anything-plays/actions/runs/43138596964)
  reached actual native FFmpeg-off DirectShow OpenCV compilation. At this
  checkpoint native wheel **IN PROGRESS**; no new Windows full installer yet.
- **Mac Intel:** [PR #213](https://github.com/MasynNay/anything-plays/pull/213);
  [run 43137079614](https://github.com/MasynNay/anything-plays/actions/runs/43137079614)
  had Apple Silicon wheel PASS but Intel source wheel compilation **IN PROGRESS**;
  no new Intel Mac full installer yet.

The **older four-platform stock-OpenCV seven-asset private draft** remains
unchanged and should NOT be mixed with either new clean native binary/receipt.
The historical public stable 3.0 and public 3.1 RC2 releases are unchanged.
All clean native results are technical QA only. Real physical camera/gamepad,
actual game saves/audio/endurance, corresponding source/third-party LGPL and
codec/relinking legal review and final owner publication approval are OPEN.
Formal release manifest still has just 2/6 gates supported. No public stable
3.1.0 release has been verified.

## November 11/12 release engineering update — newer than the checkpoint below

**Progress now actually completed and merged (do not rerun expensive work):**

- [PR #209](https://github.com/MasynNay/anything-plays/pull/209) merged: real
  pristine SHA256-pinned OpenCV 4.14.0.94 Linux source wheel with FFmpeg disabled,
  V4L2 backend present and unmodified source/wheel retained as private evidence
  ([native run 43133383864](https://github.com/MasynNay/anything-plays/actions/runs/43133383864)).
- [PR #211](https://github.com/MasynNay/anything-plays/pull/211) merged: that
  **newly compiled** wheel swapped into an extracted complete 18-profile 3.1.0
  Linux GUI and tested under Xvfb; actual frozen Tk and Stream Mode passed
  ([run 43135466315](https://github.com/MasynNay/anything-plays/actions/runs/43135466315)).
- [PR #212](https://github.com/MasynNay/anything-plays/pull/212) merged at
  `d94efcd03a3fcf30df31e67bd6331de30a157f49`: a **fresh genuine 3.1.0
  full Linux DEB** rebuilt with that source OpenCV wheel, the original 11
  core families and 18 profiles, FFmpeg-codec filename inventory, and
  real installed frozen Tk/Stream Mode QA all **PASSED**
  ([run 43136053895](https://github.com/MasynNay/anything-plays/actions/runs/43136053895)).
  The new complete DEB and truthful SHA/source receipts are in private
  artifact `AnythingPlays-3.1.0-LINUX-FULL-18-CAMERA-ONLY-NEW-BUILD-QA-PRIVATE`.
  It does **not** replace the existing seven-asset private `v3.1.0` draft.
- [PR #210](https://github.com/MasynNay/anything-plays/pull/210) merged:
  disposable full 3.1 GUIs with source-built **2.0** camera-only cv2 binaries
  booted on Windows and two Macs
  ([43137224618](https://github.com/MasynNay/anything-plays/actions/runs/43137224618)).
  Reuse proof is not a source-complete new 3.1 wheel or redistribution approval.

**Native source build work currently in progress (check latest runs):**

- [PR #213](https://github.com/MasynNay/anything-plays/pull/213):
  genuine OpenCV 4.14.0.94 source wheel builds on native
  Apple Silicon and Intel Mac, with FFmpeg/AVIF disabled and
  AVFoundation backend retained. Both builds passed source/test setup
  and were compiling at last check
  ([run 43137079614](https://github.com/MasynNay/anything-plays/actions/runs/43137079614)).
- [PR #214](https://github.com/MasynNay/anything-plays/pull/214):
  new independent Windows FFmpeg-disabled DirectShow source wheel.
  First build failed because the published original 2.0 packaging patch's
  descriptive `setup.py` diff headers were misread as literal filenames;
  scratch-only header normalization was committed on this PR. Check
  its new workflow run before claiming compile success.

**Next:** finish/repair both Mac and Windows source wheels, use them in fresh
native final-identity 18-console build/installed GUI acceptance (original
full frozen 3.1 draft bytes must not be silently changed), audit new
source/notice/relinking obligations per OS, then handle the remaining physical
hardware / owner signoff and stable public release authorization.
The original four full QA passes and private draft remain valid evidence
for the *old* stock-OpenCV binaries, not the newly rebuilt Linux binary.
**None of these private technical passes closes legal or real-device gates.**

## Prior dated engineering milestone and dependency decision (November 11)

**New camera-only OpenCV remediation experiment:** [PR #209](https://github.com/MasynNay/anything-plays/pull/209) adds a **disposable Linux-only source-build** of `opencv-python-headless==4.14.0.94`, with the exact published PyPI sdist SHA-256, FFmpeg/GStreamer/Qt disabled and V4L2 enabled. [Actions 43133383864](https://github.com/MasynNay/anything-plays/actions/runs/43133383864) had verified the sdist and passed its private receipt tests; actual native wheel compilation was **IN PROGRESS** at this checkpoint. The accompanying [source tests 43133383667](https://github.com/MasynNay/anything-plays/actions/runs/43133383667) passed on Python 3.12/3.13 plus native mGBA. No frozen installer, camera hardware, third-party source/relinking clearance or public release result follows until future native evidence is checked. Do not merge it or repeat heavy builds just because this report says queued/in progress.

**Complete source-pinned 3.1.0 build and private seven-asset draft are DONE;
stable publication is NOT DONE.** All four final full 18-console/11-core
installers and actual installed frozen GUI/Stream Mode smoke checks passed
in [run 43120583726](https://github.com/MasynNay/anything-plays/actions/runs/43120583726).
The [private four-installer staged bundle](https://github.com/MasynNay/anything-plays/actions/runs/43123263034)
was SHA-verified; the GitHub Release draft exists as
`v3.1.0`, release ID `442346875`, with all seven assets, and **is not public**.

**Additional native distribution audit completed:** [PR #203](https://github.com/MasynNay/anything-plays/pull/203)
found exact native/notice paths on all four OSes; [PR #204](https://github.com/MasynNay/anything-plays/pull/204)
confirmed that the frozen OpenCV runtime in public 3.0 is **byte-identical**
to final 3.1 on each corresponding OS. FFmpeg-named OpenCV binaries occur
in both builds on Linux, Windows and Apple Silicon; the latter also includes
libx264 and libx265. Intel Mac has no FFmpeg/x264/x265 names in the checked
OpenCV subset. The earlier claim that public 3.0 was universally FFmpeg-free
was incorrect (the separate historical *2.0* custom wheel claim may still
apply only to 2.0). See
[exact codec/source review](V3_1_OPENCV_EXACT_RUNTIME_REVIEW.md) and
[distribution review](V3_1_NATIVE_DISTRIBUTION_REVIEW.md).

**Still open:** independent native corresponding-source and redistributable
license/relinking review, physical-device/gameplay acceptance, final rollout
approval. The formal [release readiness manifest](../config/v3.1-release-readiness.json)
correctly keeps approval `false`; 2/6 evidence gates are closed. No further
full installer rebuild is needed **unless actual dependency remediation
changes installer bytes**, in which case the relevant platforms require fresh
source, native installed QA, receipts and checksums.

## Public release truth

- **Latest stable:** [v3.0.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0), original sources [v3.0.0-sources](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources). Do not touch stable 3.0, 2.0 or 1.5 assets.
- **Public 3.1 preview:** [v3.1.0-rc2](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc2). All 18 profiles and 11 emulator source-core families are present. It includes DS-inspired adjustable Stream Mode, themed screen bezels and optional controllers. The user reported installing and launching the Linux DEB and successfully viewing the Stream Mode layout. **No physical controller or full game/camera/audio/OBS recording test is implied.**
- **3.1.0 stable is NOT published.** Do not relabel the immutable old RC2 files as stable or misrepresent a private CI artifact as a public release.

## Verified post-RC2 engineering already merged

- [Camera-disconnect Stream Mode privacy fix #197](https://github.com/MasynNay/anything-plays/pull/197) merged. The unconnected webcam's stale last frame is cleared from the stream output rather than freezing.
- [Four-platform full-core QA and macOS Bash packaging fix #198](https://github.com/MasynNay/anything-plays/pull/198) merged. [Source checks 43094552640](https://github.com/MasynNay/anything-plays/actions/runs/43094552640) and [authentic 18-console installer + installed native GUI checks 43094552705](https://github.com/MasynNay/anything-plays/actions/runs/43094552705) **PASSED across Windows x64, Linux x64, macOS Intel, macOS Apple Silicon** for exact source revision `26fdc6cf9399ea0fd79665850089471f5ffec70d`. These packages still carry an isolated **RC2** QA identity and were never publicly promoted.
- [Final artifact provenance/staging gate #200](https://github.com/MasynNay/anything-plays/pull/200) merged in main as `e6767d3a420f4af0cec53bc5ba21b32e60b48923`. Python 3.12 and 3.13 source checks passed, including `test_v31_final_release_stage.py`. The read-only workflow `.github/workflows/v31-stage-final-four-reviewed-qa.yml` runs **only after** the new final workflow succeeds, downloads four complete installers plus four installed-GUI receipts, rejects mismatched bytes/false approvals, and preserves a **private** package/checksum bundle.

## Historical build timeline before the completed native release draft

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

## Exact next actions after successful four-platform packaging

1. **Do not repeat the finished four-platform 18-console builds** or make a
   second private draft. Existing exact source, SHA256 receipts, original
   release draft and corresponding artifacts are listed above; verify
   retention before relying on an artifact.
2. Complete the OpenCV/FFmpeg/codec source and redistribution review against
   [the actual four released-to-draft binaries](V3_1_OPENCV_EXACT_RUNTIME_REVIEW.md).
   In particular inspect Apple Silicon x264/x265 linking and applicable
   notices, original source and build flags. Options: independently clear
   the actual bundled native code and user-modification requirements, or
   source-build a verified camera-only OpenCV wheel and rerun the affected
   native installers and GUI acceptance. Never claim matching old 3.0 bytes
   equal legal clearance.
3. Complete pygame/SDL and remaining native source/notice/relinking review,
   including 11 original-core licenses. Leave the `pygame_sdl_redistribution_review`
   and `corresponding_source_material` gates `false` until grounded in
   independently reviewed complete evidence.
4. Obtain or explicitly document real hardware/controller/camera, gameplay,
   saves/audio/long-session acceptance. The owner confirmed only Linux RC2
   installation and DS Stream Mode first-look. Do not claim physical
   controller/gameplay/OBS recordings as passed.
5. Review [prepared release notes](V3_1_RELEASE_DRAFT_NOTES.md) and
   [exact publication runbook](V3_1_PUBLICATION_RUNBOOK.md), approve evidence
   and run `python -m tools.check_v31_release`. Use the **existing private
   seven-asset draft**, confirm original source SHA and asset bytes after any
   adjustments, and publish stable `v3.1.0` only when permission and
   acceptance are properly resolved. Preserve stable 3.0 and RC2 and update
   the portfolio only after verifying the new public release.

**GitHub private QA/draft is NOT a public release. Do not assert otherwise,
fabricate source correspondence or mark hardware testing as complete.**
