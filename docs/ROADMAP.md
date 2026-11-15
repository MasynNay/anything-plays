# Anything Plays — Product roadmap

**If it moves, it plays.** Anything Plays is a free desktop application that turns locally tracked camera movement into controls for classic games. This is the current **post-3.2.0 stable** product plan, not a list of unverified feature promises.

[Official website](https://anythingplays.masynnay.com/) · [Download stable 3.2.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.2.0) · [Report an issue](https://github.com/MasynNay/anything-plays/issues) · [Architecture](ARCHITECTURE.md)

## Release history and current status

| Version | Status | What shipped |
| --- | --- | --- |
| **1.5** | Released | Original camera-to-game desktop studio |
| **2.0** | Released | Four consoles, flexible control zones, themes, local ROM libraries |
| **3.0** | Released, November 9, 2026 | 18 console profiles, 11 native emulator core families, Windows/Linux/Apple Silicon/Intel Mac installers |
| **3.1.0** | **Public stable, November 11, 2026 (Mountain Time)** | OBS-friendly two-screen Stream Mode, 16 themes, configurable bezels, optional SDL gamepad mapping/tester, safer reconnect/focus handling, isolated preferences, all 18 consoles |
| **3.1.1** | **Public stable, November 12, 2026 (Mountain Time)** | Camera recovery, controller/SDL resilience, atomic game-save reliability, ROM/art shelf fault isolation, expanded four-platform tests; same 18 consoles |
| **3.2.0** | **Public stable, November 15, 2026** | Guided onboarding, camera calibration, controller/keyboard setup, portable control backups and Undo, privacy-safe diagnostics; 11 original native cores / 18 console profiles, four native installers and verified 3.1.x upgrade path |
| **3.2 maintenance** | Source merged November 15, 2026 | Camera/controller recovery, ROM handoff and GameCube GPU/A/V diagnostics in [PR #245](https://github.com/MasynNay/anything-plays/pull/245); **not yet included in the published v3.2.0 binaries** |
| **3.3** | Development underway | Frame-lock isolation for Stream Mode and measurable capture/input responsiveness, followed by GPU and 30-minute field profiling; not released |

The current [3.2.0 public stable release](https://github.com/MasynNay/anything-plays/releases/tag/v3.2.0) ships all four native installers, a SHA-256 manifest, source-access notes and the build QA report. Exact application source revision: `0c4db50ede64646cecbadd400dd54f0ae76166c9`. [Four-platform release candidates passed](https://github.com/MasynNay/anything-plays/actions/runs/43742977770), and [the exact eight-asset publication workflow succeeded](https://github.com/MasynNay/anything-plays/actions/runs/43743526029). [Public 3.1.1 remains available](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.1) for rollback.

**Quality distinction:** the 3.2 installer upgrade, application startup and saved-memory checks passed native automated QA; this is **not** a universal certification of real webcams, USB/Bluetooth controller pairs, physical audio, commercial-game saves or GameCube GPU performance. The original MIT source and bundled native dependencies remain subject to their respective licensing and source-access notices.

## Continuing: 3.2.0 — Field compatibility and maintenance

**Goal:** Support the now-released 3.2.0 with practical hardware reports and targeted fixes, without presenting synthetic tests as physical-device certification.

| Workstream | Definition of done |
| --- | --- |
| Real controller acceptance | Exercise Xbox/PlayStation-style USB/Bluetooth connect, mapping, game input, unplug/reconnect, focus loss and safe release on actual machines. Mark untested hardware explicitly instead of counting simulated events as devices. |
| Camera and control reliability | Confirm first-use camera permissions, target loss/reacquisition, primary and secondary object behavior, STOP safety and no stuck buttons. Keep footage local and exclude private camera recordings from reports. |
| ROM switching, saves and startup | Reproduce load → unload → load, failed ROM recovery, save persistence, shutdown and relaunch across GB/GBC/GBA/SNES/N64 and targeted GameCube sessions. No game/BIOS files in CI artifacts. |
| Windows/Linux/Mac packaging | Verify one clean installation per practical native OS, updates without overwriting 3.1.0 settings, clear unsigned/notarization warnings and installer integrity. |
| Crash and memory hygiene | Test repeated launches/switches, camera/controller disconnects and at least a 30-minute representative session; quantify resource growth and regressions. |

**3.2.0 shipped after genuine multi-OS native upgrade tests and targeted regression evidence**, not merely a version-number change. Real-device, licensed-game and host-specific diagnostics remain ongoing; collect issue reports in [Windows #26](https://github.com/MasynNay/anything-plays/issues/26) and [Linux #25](https://github.com/MasynNay/anything-plays/issues/25). A later 3.1.2 hotfix should only ship for a demonstrated issue with its own platform-specific tests. Do not confuse earlier owner 3.0/3.1 RC tests with acceptance of every new device.

## Shipped in 3.2 — Setup and control experience

**Released publicly as 3.2.0:** versioned control-profile export/import and Undo ([guide](V3_2_SETUP_CONTROLS.md)), guided camera calibration ([guide](V3_2_CAMERA_CALIBRATION.md)), controller/keyboard onboarding ([guide](V3_2_CONTROLLER_ONBOARDING.md)) and privacy-safe setup diagnostics ([guide](V3_2_SETUP_DIAGNOSTICS.md)). The Get started launchpad and the full 18-profile same-install upgrade were verified in four-platform native QA. The separate `run_v32_preview.py` launcher remains a historical isolated development channel, not the stable installer. Physical device behavior still depends on hardware and drivers.

**Goal:** A first-time user should be able to go from installation to a working camera or keyboard-controlled game without reading technical documentation.

1. **Local camera calibration wizard.** Guide camera selection, color sampling, lighting, live zone feedback and target stability in a small flow, with an expert path still available. Show measurable jitter, lost tracking and zone-trigger events; avoid false accuracy promises. [Feature issue #29](https://github.com/MasynNay/anything-plays/issues/29).
2. **Simple gamepad and keyboard setup.** A controller connection checklist, clearly grouped buttons and sticks, per-console live testing, plain-language remapping and a safe reset.
3. **Portable layout export/import.** Versioned, privacy-conscious settings files containing input mappings, color controls and theme preferences, **not** game ROMs, personal paths, camera frames, credentials or saves. Validate malformed files, show a preview and allow rollback before applying. [Feature issue #30](https://github.com/MasynNay/anything-plays/issues/30).
4. **Easier diagnostics and help.** Visible explanations for camera access, unsupported game frames, missing cores, controller disconnects and update availability; one-click copy of redacted diagnostics where appropriate.

**Success:** Successful setup with fewer steps, measured reduction in spurious tracking triggers, deterministic validation tests and clean migration between supported operating systems.

## Now developing: 3.3 — Performance and creator tools

**Goal:** Improve actual gameplay responsiveness and make Stream Mode resilient during long streams. This is a development track, **not** a public release announcement. The first source changes live in a separate draft PR so the existing 3.2.0 installers remain safe.

### Delivery order and acceptance gates

| Priority | Increment | Proof required before merging or calling it complete |
| --- | --- | --- |
| 1 | Stream Mode native-frame lock isolation | Only copy native pixels under the emulator lock; convert to PIL outside the lock. Verify the lock boundary, unchanged-frame caching, correct output and source checks on Python 3.12/3.13. |
| 2 | Stream refresh cadence | Compare requested 15/24/30 FPS with achieved capture refresh under load. Fix avoidable timer drift without skipping game frames or saturating Tk's event loop; regression-test scheduling and window close. |
| 3 | Camera-to-game input latency | Measure tracking → control buffer → native frame on simulated and actual devices, record median and tail latency separately; prioritize correctness and no stuck controls. |
| 4 | GameCube A/V performance and stability | Use actual emulation frame timing, GL readback cost and audio underflow counters on real machines; run a 30-minute game and repeated switches. CI-only results do not certify a physical GPU. |
| 5 | Native packaging and patch candidate | Review notices and provenance, perform upgrade/revert and hardware acceptance, produce exact four-platform assets and SHA-256 manifest only after approval. Never rewrite old 3.2.0 installers. |

**Current implementation:** the [3.3 Stream Mode draft branch](https://github.com/MasynNay/anything-plays/tree/feature/v3.3-stream-render-latency) now moves PIL conversion outside the native framebuffer lock and compensates stream timer waits for render duration, with an 8 ms minimum idle gap under overload. Unit tests cover native-lock isolation, unchanged-frame caching, timer compensation and failure backoff. These source changes are not shipped in 3.2.0; no before/after real-device latency measurements have been collected, so no measured speedup is claimed.

- **GameCube performance.** Measure real emulation FPS, frame-time variance, audio underruns and camera/preview frame rate separately. Compare preview 15/24/30 FPS without claiming higher gameplay FPS. Investigate OpenGL readback stalls only when benchmarks demonstrate a benefit. [Performance issue #27](https://github.com/MasynNay/anything-plays/issues/27).
- **Lower camera-to-game latency.** Profile detection, UI frame pacing and game input propagation under one and multiple tracked objects; prevent slow preview rendering from blocking gameplay.
- **Stream Mode polish.** Improve resize/crop behavior, bezel alignment, capture consistency and per-theme readability across 16 themes. Preserve separate uncaptured stream settings and explain how external emulator windows are handled by OBS.
- **Long-session stability.** Measure memory, native worker shutdown and audio/video timing over at least 30 minutes and repeated game transitions on each feasible real host.

**Success:** Reproducible before/after measurements, no degraded input correctness, no hidden frame skipping or false FPS claims, and passing source/native CI.

## Future ideas — not committed

After stability, usability and performance improve, explore more accessible multiplayer mapping, community-shareable nonprivate control presets, better first-run tutorials, cross-device configuration transfer and additional streamer customization. New console families, web-play editions or streaming services are **not** automatic priorities: they require clear user value, compatible sources and legal packaging review.

## Release and security policy

- Keep builds, camera tracking, save handling and game ROM files **local by design**. Do not include ROMs or commercial firmware with the app.
- Preserve exact platform-native builds, SHA256 checksums, dependency notices and recipient source/rebuild rights; do not conflate LGPL obligations with physical hardware testing. See [the scoped 3.1 release decision](V3_1_SCOPED_DISTRIBUTION_DECISION.md) and [LGPL rebuild instructions](V3_1_LGPL_REBUILD_REPLACEMENT.md).
- The complete emulator installers remain free and **noncommercial** because bundled core licenses can be more restrictive than the MIT-licensed original application source.
- Keep earlier [stable 3.1.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0), [stable 3.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0) and [3.1 RC2](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc2) available for rollback.
- Version 3.2.0 shipped November 15, 2026. PR #245 merged later as source-only maintenance; its fixes are not retroactively present in already published 3.2.0 installers. No dates are committed for future 3.3 work. Triage 3.1.1 issues through [GitHub Issues](https://github.com/MasynNay/anything-plays/issues), test changes and only publish incremental fixes when verified.

## Historical engineering log

The prior roadmap contained a detailed chronological record of 3.1 Preview, RC1, RC2, source-wheel and native-library testing, most of which preceded the successful public stable release. That complete snapshot is preserved in [the pre-3.1-stable roadmap archive](development/ROADMAP_PRE_3_1_STABLE_ARCHIVE.md). Current release evidence is in [3.1 acceptance](V3_1_RELEASE_ACCEPTANCE.md) and the [engineering checkpoint](development/CONTINUE_HERE.md). Those records remain available without burying the current product roadmap.
