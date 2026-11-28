# Anything Plays — Product roadmap

**If it moves, it plays.** Anything Plays is a free desktop application that turns locally tracked camera movement into controls for classic games. This is the current **post-3.3.0 stable** product plan, not a list of unverified feature promises.

[Official website](https://anythingplays.masynnay.com/) · [Download stable 3.3.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.3.0) · [Report an issue](https://github.com/MasynNay/anything-plays/issues) · [Architecture](ARCHITECTURE.md)

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
| **3.3.0** | **Public stable, November 21, 2026** | Stream Mode frame-lock isolation, bounded Tk cadence and input-latency diagnostics, camera/controller failure recovery, GameCube GPU preview/PCM observability; verified four-platform full-native installers / 11 core families / 18 console profiles |
| **3.3.1 maintenance** | Development / unreleased | Small Stream Mode shutdown fault-isolation improvements and field hardware issue triage, only for a future independently tested patch |

The current [3.3.0 public stable release](https://github.com/MasynNay/anything-plays/releases/tag/v3.3.0) ships four verified full-native desktop installers plus a source companion, SHA-256 manifest, QA report and source-access notes. Exact reviewed application source: `32c66632e30570f142aa992791ed44bdb1fad3aa`. The [full-native four-platform QA passed](https://github.com/MasynNay/anything-plays/actions/runs/44933612513) and [exact eight-asset publication succeeded](https://github.com/MasynNay/anything-plays/actions/runs/44934077937). [3.2.0 remains available](https://github.com/MasynNay/anything-plays/releases/tag/v3.2.0) as the previous stable rollback.

**Quality distinction:** the 3.2 installer upgrade, application startup and saved-memory checks passed native automated QA; this is **not** a universal certification of real webcams, USB/Bluetooth controller pairs, physical audio, commercial-game saves or GameCube GPU performance. The original MIT source and bundled native dependencies remain subject to their respective licensing and source-access notices.

## Continuing: 3.3.0 — Field compatibility and maintenance

**Goal:** Support the now-released 3.3.0 with practical hardware reports and targeted fixes, without presenting synthetic tests as physical-device certification. The remaining physical-camera, controller, GameCube/OBS endurance and licensing acceptance items are tracked in [issue #247](https://github.com/MasynNay/anything-plays/issues/247).

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

## Shipped in 3.3.0 — Performance and creator tools

**Goal and release result:** Improve Stream Mode responsiveness and recovery without changing the original visual design or emulator features. The [published 3.3.0 release](https://github.com/MasynNay/anything-plays/releases/tag/v3.3.0) passed automated source, Stream Mode endurance, and four-platform installer QA. Physical GPU, speaker, OBS, controller and camera testing remain explicitly **unverified**. This section records shipped work and its acceptance criteria, not a new feature announcement.

### Delivery order and acceptance gates

| Priority | Increment | Proof required before merging or calling it complete |
| --- | --- | --- |
| 1 | Stream Mode native-frame lock isolation | Only copy native pixels under the emulator lock; convert to PIL outside the lock. Verify the lock boundary, unchanged-frame caching, correct output and source checks on Python 3.12/3.13. |
| 2 | Stream refresh cadence | Source measures requested 15/24/30 FPS against completed Tk callback cadence, changed-image publications and bounded composition-cost P95/over-budget counts separately. A two-slot resized-source cache avoids needless scaling when one image remains unchanged; stale camera pictures are replaced with a waiting state without expiring intentional reference images. A real Tk + synthetic 180-second Stream Mode soak checks the cache, memory and refresh behavior; a separate 1,800-second source-only endurance workflow is manually triggered. See [Stream Mode cadence measurement](V3_3_STREAM_CADENCE.md). Verify actual OBS encoded frame rate and sustained real-host behavior before claiming a stream-performance gain. |
| 3 | Camera-to-game input latency | Opt-in, constant-memory software-stage P50/P95 buckets now cover start of tracking → native input handoff for held controls ([field guide](V3_3_INPUT_LATENCY.md)); still require independent camera-to-screen hardware baselines and pulse/external-mode evaluation. |
| 4 | GameCube A/V performance and stability | Local **Check my setup** now exposes bounded live and final native timing, GL readback cost, preview publication cadence versus the GameCube 20/30/60 FPS target, deadline misses and audio delivery counters; see the [real-device GameCube profile guide](V3_3_GAMECUBE_PERFORMANCE.md). Collect controlled 30-minute gameplay/real-speaker baselines and repeated switches on actual GPUs before merging. |
| 5 | Native packaging and patch candidate | Review notices and provenance, perform upgrade/revert and hardware acceptance, produce exact four-platform assets and SHA-256 manifest only after approval. Never rewrite old 3.2.0 installers. |

**Current implementation:** the [3.3 development branch](https://github.com/MasynNay/anything-plays/tree/feature/v3.3-stream-render-latency) moves Stream Mode's PIL conversion outside the native framebuffer lock and compensates capture refresh waits for render duration, with an 8 ms idle gap under overload. For dual-color camera tracking, both targets reuse a single HSV frame conversion, and the tracked control snapshots are handed to the emulator before OpenCV draws cosmetic preview contours. Tests cover independent player-one/player-two input, safe release, original camera pixels, stream lock boundaries, refresh compensation and retry backoff. A separate opt-in local timing probe now records bounded software-stage percentile buckets at the native input buffer, viewable and copyable through **Check my setup**, with no camera frame or personal paths retained ([instructions](V3_3_INPUT_LATENCY.md)). It is disabled by default and currently measures the embedded **Held while visible** input path only. The [GameCube A/V diagnostics](V3_3_GAMECUBE_PERFORMANCE.md) additionally show native run times, separate GL readback share, deadline misses, and PortAudio/PCM delivery counters in **Check my setup**, retaining only safe numeric aggregates when Dolphin closes. Stream Mode likewise shows [completed Tk refresh cadence versus successful changed-image publications](V3_3_STREAM_CADENCE.md), with its own 15/24/30 FPS target, session-scoped counters, and explicit no-samples state; that is not actual OBS recording FPS. Synthetic source CI verifies report/privacy semantics, not physical FPS, real speaker output, sensor-to-display latency, or sustained GPU throughput. The public v3.2.0 installer assets remain unchanged and available for rollback; the described 3.3.0 changes are in the separate verified public 3.3.0 installer binaries.

- **GameCube performance.** Measure native emulation work, frame-time variance, audio underruns and published preview cadence separately. Compare GameCube preview targets **20/30/60 FPS** and independent Stream Mode capture targets **15/24/30 FPS**, without claiming higher gameplay or physical display FPS. Investigate OpenGL readback stalls only when real hardware benchmarks demonstrate a benefit. [Performance issue #27](https://github.com/MasynNay/anything-plays/issues/27).
- **Lower camera-to-game latency.** Profile detection, UI frame pacing and game input propagation under one and multiple tracked objects; prevent slow preview rendering from blocking gameplay.
- **Stream Mode polish.** Improve resize/crop behavior, bezel alignment, capture consistency and per-theme readability across 16 themes. Preserve separate uncaptured stream settings and explain how external emulator windows are handled by OBS.
- **Long-session stability.** Measure memory, native worker shutdown and audio/video timing over at least 30 minutes and repeated game transitions on each feasible real host.

**Success:** Reproducible before/after measurements, no degraded input correctness, no hidden frame skipping or false FPS claims, and passing source/native CI.

## Next product milestone — Reusable control presets

The existing 3.2 portable profile import/export and all-console backup remain supported. The next feature increment adds a local named preset library accessible from Safety & Profiles:

- Save up to 12 named camera-control layouts per console, without replacing active controls.
- Apply a selected layout through the existing confirmed import transaction, with object input paused and Undo import available.
- Compare normalized current and selected button zones side by side before applying, including remapped labels and hidden disabled zones.
- Import a portable control file into the library without applying it, and export a saved preset as the existing version-1 portable profile format. Local preset names are not exported.
- Preserve ROM libraries, saves, artwork, local device settings and other consoles. Store the library beside the current preferences, with bounded versioned JSON, validation and atomic writes.
- Acceptance: four-platform storage and portable-profile regression tests, real Tk interaction tests, and subsequent clean-install/manual usability checks. The implementation is under development; it is not in the published 3.3.0 binaries.

The next source increment implements five built-in starting layouts across all 18 console profiles: large movement zones, two large action zones, simplified adventure controls, high-contrast full controls and a mirrored full grid. The browser previews active, disabled, remapped and moved camera buttons, supports saving a starter to the local library, and uses the existing confirmed apply/Undo path. Tracking colors, detection calibration, local device settings and global theme are preserved. The simplified layouts intentionally disable camera buttons not included in their description; these are uncalibrated starting points, not verified accessibility prescriptions. Physical user testing and installer verification are still required.

The preset collection exchange is implemented in development source: explicitly select up to 48 saved layouts across consoles, assign share labels, export a bounded versioned JSON collection, and review/select incoming layouts before an atomic import. Existing names are not automatically exported; generic labels are the default. Identical existing layouts are skipped, while conflicting names or capacity limits reject the entire selected batch. Imports never change active controls. No online catalog or account is involved. Source and actual Tk tests gate this increment; installed application usability remains a manual acceptance task.

## Creator workspace — reusable Stream Mode scenes

Development source adds a separate Creator scenes window in Stream Settings. Five built-in capture starters (portrait recording, landscape stream, camera spotlight, clean gameplay and low overhead) provide ordinary existing Stream Mode layouts and refresh settings. Save up to 16 named local configurations, preview synthetic panel geometry, apply all options as one update, undo the latest applied scene while the browser is open, and import/export versioned settings-only JSON. A saved scene includes layout, theme, refresh, screen share, labels, screen order and border settings; it never stores camera/game pixels, OBS credentials, devices, paths or ROMs. No changes to emulator FPS or native input, and no extra camera or OBS connection. The output window remains independently resizable.

Acceptance: strict scene validation, atomic persistence, existing compositor regressions, real Tk scene workflow and four-platform source checks. Physical OBS capture and installer testing remain outstanding.

Follow-on roadmap: richer per-setting change summaries, measured accessibility usability improvements, advanced creator capture customization and multiplayer mapping. No account, server or automatic upload is required. This increment does not yet include a community catalog or sync service.

## Future ideas — not committed

After stability, usability and performance improve, explore more accessible multiplayer mapping, community-shareable nonprivate control presets, better first-run tutorials, cross-device configuration transfer and additional streamer customization. New console families, web-play editions or streaming services are **not** automatic priorities: they require clear user value, compatible sources and legal packaging review.

## Release and security policy

- Keep builds, camera tracking, save handling and game ROM files **local by design**. Do not include ROMs or commercial firmware with the app.
- Preserve exact platform-native builds, SHA256 checksums, dependency notices and recipient source/rebuild rights; do not conflate LGPL obligations with physical hardware testing. See [the scoped 3.1 release decision](V3_1_SCOPED_DISTRIBUTION_DECISION.md) and [LGPL rebuild instructions](V3_1_LGPL_REBUILD_REPLACEMENT.md).
- The complete emulator installers remain free and **noncommercial** because bundled core licenses can be more restrictive than the MIT-licensed original application source.
- Keep earlier [stable 3.1.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0), [stable 3.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0) and [3.1 RC2](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc2) available for rollback.
- Version 3.2.0 shipped November 15, 2026. PR #245 merged later as source-only maintenance; its fixes are not retroactively present in already published 3.2.0 installers. 3.3.0 shipped November 21; future 3.3.1 maintenance has no committed release date. Triage 3.1.1 issues through [GitHub Issues](https://github.com/MasynNay/anything-plays/issues), test changes and only publish incremental fixes when verified.

## Historical engineering log

The prior roadmap contained a detailed chronological record of 3.1 Preview, RC1, RC2, source-wheel and native-library testing, most of which preceded the successful public stable release. That complete snapshot is preserved in [the pre-3.1-stable roadmap archive](development/ROADMAP_PRE_3_1_STABLE_ARCHIVE.md). Current release evidence is in [3.1 acceptance](V3_1_RELEASE_ACCEPTANCE.md) and the [engineering checkpoint](development/CONTINUE_HERE.md). Those records remain available without burying the current product roadmap.
