# Anything Plays — Development Roadmap

**If it moves, it plays.** Anything Plays turns camera-detected motion into local video-game controls. This roadmap describes shipped work, the **active 3.0 development preview**, and the evidence required before the next public release.

**Last reviewed:** November 9, 2026  
**Stable:** [v2.0.0](https://github.com/MasynNay/anything-plays/releases/tag/v2.0.0)  
**Active development:** [`feature/v3.0-unified-test`](https://github.com/MasynNay/anything-plays/tree/feature/v3.0-unified-test)  
**Current focus:** Complete exact 44-native source review evidence, third-party GPL compatibility and source obligations, and final four-platform release acceptance  
**Tracking:** [3.0 engineering issue #24](https://github.com/MasynNay/anything-plays/issues/24) · [Open work](https://github.com/MasynNay/anything-plays/issues)

> **Status matters:** A passing CI run means its stated automated checks passed. It does **not** imply every game, camera, or GPU has been tested. Full 3.0 installers are **developer previews**, not a published, licensed-and-signed stable 3.0 release. No artificial ship dates or activity claims are used here.

## At a glance

| Area | Status | Evidence / next step |
| --- | --- | --- |
| 2.0 supported consoles (GB, GBC, GBA, SNES) | **Released** | [Stable v2.0.0](https://github.com/MasynNay/anything-plays/releases/tag/v2.0.0) |
| Modular desktop UI, themes, ROM shelf, object-based controls | **Implemented in 3.0 preview** | [3.0 source branch](https://github.com/MasynNay/anything-plays/tree/feature/v3.0-unified-test) |
| 18 console profiles, 11 bundled native cores, four installer targets | **Automated packaging passed** | [Full-bundle CI](https://github.com/MasynNay/anything-plays/actions/runs/42415284318) |
| Simultaneous object/color tracking, local P1/P2 inputs | **Automated simulation passed** | [Camera-to-controller simulation](https://github.com/MasynNay/anything-plays/actions/runs/42402602944) |
| N64 ROM unload/reload without quitting the app | **Fixed and owner-verified on Apple Silicon** | [Four-platform 3× native restart CI](https://github.com/MasynNay/anything-plays/actions/runs/42415242942) |
| Windows real-device clean install and regression | **Partial hardware smoke passed; broader QA open** | [#26](https://github.com/MasynNay/anything-plays/issues/26) |
| Linux real-device clean install and regression | **User reports GameCube/Dolphin works on Linux; formal clean-install and full-regression QA pending** | [#25](https://github.com/MasynNay/anything-plays/issues/25) |
| GameCube GPU smoothness and long-session behavior | **In progress** | [#27](https://github.com/MasynNay/anything-plays/issues/27) |
| Third-party licenses, signing, clean-install release gates | **Blocking stable 3.0** | [#28](https://github.com/MasynNay/anything-plays/issues/28) |

## Latest verified activity — November 7, 2026

- **Apple Silicon:** Maintainer confirmed repeated Nintendo 64 ROM switching without relaunching Anything Plays after the per-game native lifecycle fix.
- **Windows:** Maintainer reported that the real application worked without issues in the features tested. This is **partial QA**, not certification of every core, game, camera or save workflow.
- **Linux:** A genuine `/opt/.../dolphin-emu/Sys/codehandler.bin` permission failure was reproduced from a root-owned DEB. The updated build now passes a **non-root installed-app launch** (fresh and saved-GameCube profiles), bundled Sys visibility checks, and real native GameCube homebrew playback from a read-only installation. [Full installer evidence](https://github.com/MasynNay/anything-plays/actions/runs/42421756448). **On November 7, the maintainer reported Dolphin/GameCube working on Linux; exact installer provenance and full clean-install regression remain to be documented.**
- **Portfolio:** The [public project showcase](https://anythingplays.masynnay.com/) is deployed by GitHub Pages from `main`, with real desktop artwork, a clearly labelled interactive concept, tech stack and this transparent roadmap.

These are engineering milestones, **not an announcement of a stable 3.0 release**. Roadmap statuses update when real evidence changes, not just to make the project appear active.

## November 8, 2026 — verified 3.0 playback and source progress

- **Maintainer gameplay already completed:** Nintendo 64 game loading, repeated ROM switching and Dolphin/GameCube playback were confirmed working by the owner. GameCube functionality was reported on Windows, Apple Silicon macOS and Linux after the Sys-file access fix. These are genuine owner reports and **must not be requested again** as new tests. They do not certify every game, save format, physical audio output or exact yet-to-be-produced public installer.
- **Ten genuinely original source-built core families:** [the full offline desktop installer lab](https://github.com/MasynNay/anything-plays/actions/runs/42535823260) passed on all four targets: Windows x64, Linux x64, macOS Apple Silicon and Intel. [PR #102](https://github.com/MasynNay/anything-plays/pull/102) is merged. All 18 profiles and 11 native core slots remain present. The original Dolphin buildbot binary is now the only native family in this experimental lineup not independently rebuilt from the exact pinned source.
- **Release-mode engineering caught up with the tested app:** [PR #103](https://github.com/MasynNay/anything-plays/pull/103) merged the ten-original-source native production package path, rather than continuing to use eight source-built cores plus old unverified mGBA/N64 buildbot files. Original mGBA MPL and all 11 pinned N64 source notices are required and independently checked by installed-package verification. The [source, Python 3.12/3.13, native compatibility gate](https://github.com/MasynNay/anything-plays/actions/runs/42540053797) passed; the [four-platform installer lab](https://github.com/MasynNay/anything-plays/actions/runs/42540053912) passed **4/4**; and the [full ten-original-source installed desktop integration](https://github.com/MasynNay/anything-plays/actions/runs/42540053758) passed **4/4** (Windows, Linux, Mac ARM and Mac Intel). This is a **verified technical milestone**, not yet a public binary redistribution approval.
- **The remaining 3.0 publication blocker is not an N64 or Dolphin gameplay defect:** exact combined GPL license compatibility, independently verified corresponding sources for the *distributed* native libraries and their dependencies (including Dolphin), immutable approved production artifacts and final production-identity acceptance are still unresolved. Successful real gameplay is recorded, not ignored. No stable 3.0 installer has been published yet.

## November 9, 2026 — exact source-built Dolphin and evidence integrity

- **All eleven original native families have been compiled from pinned upstream source in the experimental offline 3.0 candidate**, replacing the last historical Dolphin buildbot binary. The original Dolphin source includes its parent and 37 pinned submodule Gitlinks. The earlier ten-family milestone remains part of the history, not the final state of the active test candidate.
- **Source-built Dolphin GPU playback passed on Linux** with real homebrew video, audio samples and controller polling in [run 42566459865](https://github.com/MasynNay/anything-plays/actions/runs/42566459865). The older CPU-only zero-frame probe did not exercise the production accelerated renderer. This does not establish retail-game compatibility or physical-device QA on every OS.
- **Eleven-family full offline installer test:** [run 42577510631](https://github.com/MasynNay/anything-plays/actions/runs/42577510631) had Windows x64, Linux x64 and Mac ARM **passed** while Mac Intel was still compiling at this checkpoint. The earlier complete four-platform ten-family candidate had already passed; do not conflate the two test sets.
- **Source evidence improvement:** [PR #122](https://github.com/MasynNay/anything-plays/pull/122) adds a post-matrix reviewer artifact for 44 installed native hashes and exact upstream source identities. Additional regression tests now reject fabricated Dolphin license-notice dictionaries, invalid source paths or digests and falsely asserted approval. The PR is **pending new CI**; the review artifact is not a legal determination or a distributable binary.
- **Public release remains v2.0.0.** Third-party GPL compatibility, exact corresponding-source distribution obligations, immutable release-mode native inputs and final production acceptance remain unresolved. No permissions or legal QA booleans are inferred from compilation or installed homebrew playback.

## Delivered milestones

### 1.0–2.0 — Desktop foundation

- [x] Camera color detection mapped to configurable gamepad zones.
- [x] Embedded GB, GBC, GBA and SNES, with separate ROM shelves and profile persistence.
- [x] Theme and layout customization, local keyboard input, and controlled game audio.
- [x] Cross-platform 2.0 installer release.

### 3.0 preview — Wider compatibility and reliable recovery

- [x] Implemented 18 console profiles with 11 emulator cores in **full offline developer-test** installers; no separate emulator installation required.
- [x] Added an object-neutral tracking interface, optional second tracked color, opt-in multiple objects per color, and independent local Player 1/Player 2 input.
- [x] Added an in-game volume slider and mute button, with persistent listening level.
- [x] Added synthetic moving-object integration tests that exercise the actual Tk camera/UI path and Libretro input callbacks.
- [x] Reproduced a persistent N64 second-ROM failure across four operating-system runners, implemented per-game Mac process isolation and safe N64 lifecycle cleanup on other platforms, then passed three consecutive native restarts per platform.
- [x] Preserved the original fish artwork; removed only the exterior black icon matte via an alpha-only transformation, protected by regression tests.
- [x] Added adjustable GameCube display preview pacing. **Actual emulation-FPS improvement on physical GPUs is still unverified.**

### Final 3.0 interface polish

- [x] Restored a prominent **Control label size** slider below the camera preview, with immediate adjustment and per-console profile persistence in the launch-polish branch.
- [x] Added zone-aware label fitting so long GameCube and N64 labels do not paint across neighboring tracking zones; automated regression test added (CI verification pending).
- [ ] Verify label scaling, reset and profile persistence on real Windows, macOS and Linux displays before merging.

### Currently validating

- [ ] **Windows real-device acceptance** — first real-device smoke was reported successful for features tested; complete the full installer, game audio, save/reload, N64 switching, and local-control checklist before marking acceptance complete. [Track #26](https://github.com/MasynNay/anything-plays/issues/26).
- [ ] **Linux real-device acceptance** — physical testing exposed a root-owned Dolphin Sys directory that prevented GameCube launch and later app startup. The corrected 3.0 DEB passes non-root installed-GUI tests with fresh and GameCube-saved settings, plus native GameCube playback from read-only DEB. The maintainer now reports Dolphin/GameCube works on Linux, but exact installer provenance and a complete clean-install regression remain to be documented. [Track #25](https://github.com/MasynNay/anything-plays/issues/25).
- [ ] **GameCube reliability and smoothness** — actual emulation FPS, frame pacing, controller latency, 30+ minute sessions, and compatibility evidence across GPUs. [Track #27](https://github.com/MasynNay/anything-plays/issues/27).
- [ ] **Evidence-backed native-core readiness** — complete mono Neo Geo Pocket audio acceptance and per-console save/input checks; do not substitute silently passing fixtures for audible gameplay. [Track #24](https://github.com/MasynNay/anything-plays/issues/24).

### Stable 3.0 release criteria

- [ ] Every declared supported console meets the release checklist with actual playback evidence, not just packaged core presence.
- [ ] Fresh-install QA covers available Windows, Linux and Apple Silicon hardware. Intel macOS is covered by CI; **physical Intel hardware testing is not yet available** and should be documented honestly or supplied by contributors.
- [ ] Verify game audio, manual and object controls, save persistence, repeated ROM switching and clean shutdown.
- [ ] Complete redistribution-license / source-provenance review and OS signing/notarization decisions.
- [ ] Meet all [fail-closed 3.0 acceptance criteria](https://github.com/MasynNay/anything-plays/blob/feature/v3.0-unified-test/config/v3.0-release-acceptance.json) and publish understandable release notes and SHA-256 checksums.

The explicit release-readiness work is in [#28](https://github.com/MasynNay/anything-plays/issues/28). **Stable 2.0 stays available throughout this work.**

## Repository cleanup at the 3.0 release

Repository hygiene is a **release deliverable**, not an invitation to delete historic work. Once the stable 3.0 binaries, corresponding source, license review and hardware acceptance are actually approved and published:

- [ ] Merge any verified 3.0 pull requests and close superseded proposals with an explanation. Retain the review and commit history.
- [ ] Audit old release, experiment, test and research branches against `main` and the published 3.0 release tag; delete only branches that are demonstrably redundant or archived after preserving unique work. Preserve `main`, the active development branch and anything not yet merged.
- [ ] Close completed 3.0 issues with links to the fix and supporting checks; move genuinely unfinished work to clearly labelled maintenance or future-version issues. Keep post-3.0 proposals #29 and #30 as intentional roadmap items.
- [ ] Consolidate obsolete build experiments, temporary project files, duplicated workflows and stale documentation without disrupting stable 2.0 or required license/source evidence.
- [ ] Perform a final editorial pass on `README.md`, `ROADMAP.md`, screenshots, support and install instructions, release notes, changelog and GitHub Pages showcase.
- [ ] Confirm stable 3.0 is the actual public release with four valid installer links and matching published checksums; clean up stale drafts without deleting old releases.

Historical pre-release inventory (November 8, 2026, immediately after PR #102): **111 branches, seven open issues and no open pull requests at that checkpoint**. This is a dated audit baseline, **not a current live count**. As of November 9, original-source Dolphin Linux research [PR #105](https://github.com/MasynNay/anything-plays/pull/105) and production Sys lock regression [PR #111](https://github.com/MasynNay/anything-plays/pull/111) are open; four-platform original-source-backed Sys installer [run 42555031999](https://github.com/MasynNay/anything-plays/actions/runs/42555031999) passed, but public stable 3.0 remains blocked on full native source/rights acceptance. Stable 2.0 remains preserved.

## Ideas for after 3.0 — proposals, not commitments

These are opportunities to investigate **after stability and compliance**, not features promised for 3.0.

| Candidate | Why it matters | What would make it worthwhile |
| --- | --- | --- |
| [Camera calibration and preview diagnostics](https://github.com/MasynNay/anything-plays/issues/29) | Less trial-and-error with lighting, reflections and similarly colored objects | Local diagnostic feedback, measured false activations and accessible opt-in calibration |
| [Portable user-profile export/import](https://github.com/MasynNay/anything-plays/issues/30) | Preserve layouts and color mappings between machines | Versioned settings-only JSON, validation and cross-platform import tests |
| Easier accessibility presets | Lower the setup barrier for nonstandard controls | One-action templates, clear keyboard navigation and user testing |
| Performance telemetry panel | Help distinguish GPU emulation bottlenecks from UI preview bottlenecks | Local-only measurements, no collection by default, low overhead |
| In-app health report | Make bug reports actionable without sharing ROMs or personal camera footage | Sanitized diagnostics, core/version hashes, opt-in export and documented privacy |

**Candidate initiatives currently tracked:** [#29 Local camera calibration](https://github.com/MasynNay/anything-plays/issues/29) and [#30 Portable profile export/import](https://github.com/MasynNay/anything-plays/issues/30). These have concrete proposed acceptance criteria but **no committed dates or implementation claims**.

Proposals should begin as [GitHub issues](https://github.com/MasynNay/anything-plays/issues) with a user problem, scope, acceptance criteria, and ideally a small reproducible test.

## How progress is tracked

1. **An issue is the unit of work.** Open work states the problem, scope and verifiable completion criteria. Existing 3.0 tasks: [#24](https://github.com/MasynNay/anything-plays/issues/24), [#25](https://github.com/MasynNay/anything-plays/issues/25), [#26](https://github.com/MasynNay/anything-plays/issues/26), [#27](https://github.com/MasynNay/anything-plays/issues/27), [#28](https://github.com/MasynNay/anything-plays/issues/28).
2. **Development is separated from stable releases.** Work is performed on [the 3.0 branch](https://github.com/MasynNay/anything-plays/tree/feature/v3.0-unified-test), not directly in public stable 2.0.
3. **Tests produce evidence.** Source tests, virtual-camera simulations, per-console native tests, multi-platform installers and sustained runs are available in [GitHub Actions](https://github.com/MasynNay/anything-plays/actions).
4. **User reports inform priorities.** For example, the N64 repeat-launch defect was reproduced before its fix was considered complete; Apple Silicon was then tested by the maintainer.
5. **Reviews change statuses, not just dates.** Update the issue and this roadmap when an acceptance criterion changes, a regression is fixed, or a real device is tested. Automated CI success and physical device coverage remain separate.

### Feedback and contributions

Found a reproducible issue or have a useful idea? [Open an issue](https://github.com/MasynNay/anything-plays/issues) with the affected platform, steps, expected behavior and safe logs, or read [CONTRIBUTING.md](CONTRIBUTING.md). Please do not upload commercial ROMs, BIOS files, private camera footage or secrets.

---

*Roadmap status is maintained manually and is subject to change based on user testing, compatibility, security and third-party license requirements. There is no public 3.0 release date until these gates are satisfied.*

### November 9, 2026 — Source-built Dolphin runtime evidence

The original pinned Dolphin Linux source now **compiles and links**, but the newly compiled binary is **not yet a validated replacement** for the owner's working core. Actual GameCube homebrew playback [run 42563978868](https://github.com/MasynNay/anything-plays/actions/runs/42563978868) loaded and executed 1,232 native frame loops and received controller inputs, yet produced **zero video callbacks**. The previous SIGSEGV is no longer the observed failure in that configuration; usable software video remains blocked. [PR #117](https://github.com/MasynNay/anything-plays/pull/117) tightens the test verdict to require changing video and real controls, with explicit regressions, and is pending source checks. Neither compilation nor this negative QA result authorizes a public release. The existing four-platform preview installers retain their original owner-tested Dolphin until an actual replacement passes.

The public `main` source history now includes release-staging PR #114, but this is **source integration only**, not binary distribution approval. The existing v2.0.0 tag and assets remain the stable release. Exact 11-core/four-platform rights, corresponding source, source-built GameCube video, immutable release inputs, and production acceptance remain prerequisites for v3.0.0.

### November 9, 2026 — Corrected original Dolphin GPU evidence and source preservation

The previous note about **zero video callbacks** described the *CPU/software* probe, not the production accelerated GameCube player. The real source-built Linux Dolphin GPU playback in [run 42566459865](https://github.com/MasynNay/anything-plays/actions/runs/42566459865) **passed**, producing 1,363 RGB frames at 24.71 FPS, 105 distinct nonblank frames, real controller response and nonzero PCM output from original licensed homebrew. This supersedes any blanket claim that the new Dolphin source build cannot render. It does **not** establish cross-platform production native-core compatibility, commercial game compatibility, complete corresponding source or redistribution rights. All four complete 18-profile offline preview integrations also passed [run 42568420431](https://github.com/MasynNay/anything-plays/actions/runs/42568420431), with test-only provenance rather than approved public installers.

[PR #119](https://github.com/MasynNay/anything-plays/pull/119) addresses a separate production release integrity defect: the source stager's output path previously protected only four source inputs, not the five extra original native build directories, mGBA, N64 and original Dolphin Sys. It now rejects staging into any source-evidence directory and adds regression cases. This is a source-preservation improvement, **not** an approval to distribute. Public v3.0 remains gated on an independently defensible mixed GPL2/GPL3 combination decision, corresponding source and dependencies for the exact binaries, immutable approved four-platform production lock and final acceptance. Existing public stable v2.0.0 downloads remain unchanged.

### November 9, 2026 — 44-source review and macOS DiskImages packaging reliability

The 44-native four-platform original-source evidence review [run 42581042306](https://github.com/MasynNay/anything-plays/actions/runs/42581042306) passed. Its evidence is **not** a redistribution approval. In a subsequent full 11-core/18-profile test [run 42581042276](https://github.com/MasynNay/anything-plays/actions/runs/42581042276), Windows, Linux and Intel Mac installers passed, while Apple Silicon's already-built app failed to mount its DMG because hosted macOS DiskImages repeatedly returned `Resource temporarily unavailable`. [PR #125](https://github.com/MasynNay/anything-plays/pull/125) extends strictly bounded retry and tests late recovery while preserving mandatory mounted DMG verification; merge only after source tests pass. An Actions rerun of the failed macOS job was requested. This is not an emulation regression or an approved stable release. Next milestones remain four-platform production provenance, exact corresponding source, qualified mixed GPL2/GPL3 rights decision, acceptance evidence and four public installer assets. No 3.0 release tag or downloads have been created.
