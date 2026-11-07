# Anything Plays — Development Roadmap

**If it moves, it plays.** Anything Plays turns camera-detected motion into local video-game controls. This roadmap describes shipped work, the **active 3.0 development preview**, and the evidence required before the next public release.

**Last reviewed:** November 7, 2026  
**Stable:** [v2.0.0](https://github.com/MasynNay/anything-plays/releases/tag/v2.0.0)  
**Active development:** [`feature/v3.0-unified-test`](https://github.com/MasynNay/anything-plays/tree/feature/v3.0-unified-test)  
**Current focus:** Windows real-device testing, then Linux  
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
| Windows real-device clean install and regression | **Next: manual QA** | [#26](https://github.com/MasynNay/anything-plays/issues/26) |
| Linux real-device clean install and regression | **Queued: manual QA** | [#25](https://github.com/MasynNay/anything-plays/issues/25) |
| GameCube GPU smoothness and long-session behavior | **In progress** | [#27](https://github.com/MasynNay/anything-plays/issues/27) |
| Third-party licenses, signing, clean-install release gates | **Blocking stable 3.0** | [#28](https://github.com/MasynNay/anything-plays/issues/28) |

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

### Currently validating

- [ ] **Windows real-device acceptance** — full installer, clean startup, game audio, save/reload, N64 ROM switching and local controls. [Track #26](https://github.com/MasynNay/anything-plays/issues/26).
- [ ] **Linux real-device acceptance** — equivalent tests on a real Linux machine, including GameCube GPU behavior where supported. [Track #25](https://github.com/MasynNay/anything-plays/issues/25).
- [ ] **GameCube reliability and smoothness** — actual emulation FPS, frame pacing, controller latency, 30+ minute sessions, and compatibility evidence across GPUs. [Track #27](https://github.com/MasynNay/anything-plays/issues/27).
- [ ] **Evidence-backed native-core readiness** — complete mono Neo Geo Pocket audio acceptance and per-console save/input checks; do not substitute silently passing fixtures for audible gameplay. [Track #24](https://github.com/MasynNay/anything-plays/issues/24).

### Stable 3.0 release criteria

- [ ] Every declared supported console meets the release checklist with actual playback evidence, not just packaged core presence.
- [ ] Fresh-install QA covers available Windows, Linux and Apple Silicon hardware. Intel macOS is covered by CI; **physical Intel hardware testing is not yet available** and should be documented honestly or supplied by contributors.
- [ ] Verify game audio, manual and object controls, save persistence, repeated ROM switching and clean shutdown.
- [ ] Complete redistribution-license / source-provenance review and OS signing/notarization decisions.
- [ ] Meet all [fail-closed 3.0 acceptance criteria](https://github.com/MasynNay/anything-plays/blob/feature/v3.0-unified-test/config/v3.0-release-acceptance.json) and publish understandable release notes and SHA-256 checksums.

The explicit release-readiness work is in [#28](https://github.com/MasynNay/anything-plays/issues/28). **Stable 2.0 stays available throughout this work.**

## Ideas for after 3.0 — proposals, not commitments

These are opportunities to investigate **after stability and compliance**, not features promised for 3.0.

| Candidate | Why it matters | What would make it worthwhile |
| --- | --- | --- |
| Camera calibration and preview diagnostics | Less trial-and-error with lighting, reflections and similarly colored objects | Configurable preview feedback, measurable tracking accuracy and a clear opt-in flow |
| Portable user-profile export/import | Preserve layouts and color mappings between machines | Versioned, validated settings format; explicit privacy safeguards; import/export tests |
| Easier accessibility presets | Lower the setup barrier for nonstandard controls | One-action templates, clear keyboard navigation and user testing |
| Performance telemetry panel | Help distinguish GPU emulation bottlenecks from UI preview bottlenecks | Local-only measurements, no collection by default, low overhead |
| In-app health report | Make bug reports actionable without sharing ROMs or personal camera footage | Sanitized diagnostics, core/version hashes, opt-in export and documented privacy |

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
