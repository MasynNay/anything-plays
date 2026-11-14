# Anything Plays — Product roadmap

**If it moves, it plays.** Anything Plays is a free desktop application that turns locally tracked camera movement into controls for classic games. This is the current **post-3.1.1 stable** product plan, not a list of unverified feature promises.

[Official website](https://anythingplays.masynnay.com/) · [Download stable 3.1.1](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.1) · [Report an issue](https://github.com/MasynNay/anything-plays/issues) · [Architecture](ARCHITECTURE.md)

## Release history and current status

| Version | Status | What shipped |
| --- | --- | --- |
| **1.5** | Released | Original camera-to-game desktop studio |
| **2.0** | Released | Four consoles, flexible control zones, themes, local ROM libraries |
| **3.0** | Released, November 9, 2026 | 18 console profiles, 11 native emulator core families, Windows/Linux/Apple Silicon/Intel Mac installers |
| **3.1.0** | **Public stable, November 11, 2026 (Mountain Time)** | OBS-friendly two-screen Stream Mode, 16 themes, configurable bezels, optional SDL gamepad mapping/tester, safer reconnect/focus handling, isolated preferences, all 18 consoles |
| **3.1.1** | **Public stable, November 12, 2026 (Mountain Time)** | Camera recovery, controller/SDL resilience, atomic game-save reliability, ROM/art shelf fault isolation, expanded four-platform tests; same 18 consoles |
| **3.2** | Proposed | Camera calibration, simpler controller onboarding, portable control profiles |
| **3.3** | Proposed | GameCube and 3D performance, smoother streaming capture, lower latency and extended-session optimization |

The current [3.1.1 release](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.1) provides four full installers, matching SHA256 checksums, per-platform native build and installed GUI evidence, a source-access review, and the byte-identical original pygame/SDL/mpg123 source companion from 3.1.0. The **exact tested application revision** is `e433d4475e22ce2b39d79cf4d656b027c17d9ef7`. All nine source/package/real-Tk+Stream-Mode review jobs passed in [native run 43355665931](https://github.com/MasynNay/anything-plays/actions/runs/43355665931), and the [eight-asset publication and anonymous-access verification passed](https://github.com/MasynNay/anything-plays/actions/runs/43358855767). The earlier [3.1.0 stable release](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0) remains available unchanged.

**Quality distinction:** All four 3.1.1 native installers and their actual frozen Tk/Stream Mode launches passed; virtual-time controller/save checks and a real timed Linux UI soak also passed. This is **not** certification of physical controller pairing, live webcam capture, every retail-game save/audio combination, multiple hours of real gameplay or every GPU. These remain field-validation work disclosed in the [3.1.1 release notes](releases/ANYTHING_PLAYS_V3_1_1_PUBLIC_NOTES.md). The complete app is free and noncommercial, with independent emulator/library licensing and original source access; an actual gamepad is optional.

## Continuing: 3.1.1 — Field compatibility and maintenance

**Goal:** Support the now-released 3.1.1 with practical hardware reports and targeted fixes, without presenting synthetic tests as physical-device certification.

| Workstream | Definition of done |
| --- | --- |
| Real controller acceptance | Exercise Xbox/PlayStation-style USB/Bluetooth connect, mapping, game input, unplug/reconnect, focus loss and safe release on actual machines. Mark untested hardware explicitly instead of counting simulated events as devices. |
| Camera and control reliability | Confirm first-use camera permissions, target loss/reacquisition, primary and secondary object behavior, STOP safety and no stuck buttons. Keep footage local and exclude private camera recordings from reports. |
| ROM switching, saves and startup | Reproduce load → unload → load, failed ROM recovery, save persistence, shutdown and relaunch across GB/GBC/GBA/SNES/N64 and targeted GameCube sessions. No game/BIOS files in CI artifacts. |
| Windows/Linux/Mac packaging | Verify one clean installation per practical native OS, updates without overwriting 3.1.0 settings, clear unsigned/notarization warnings and installer integrity. |
| Crash and memory hygiene | Test repeated launches/switches, camera/controller disconnects and at least a 30-minute representative session; quantify resource growth and regressions. |

**3.1.1 shipped after actual fixes and focused regression evidence**, not merely a version-number change. Real-device, licensed-game and host-specific diagnostics remain ongoing; collect issue reports in [Windows #26](https://github.com/MasynNay/anything-plays/issues/26) and [Linux #25](https://github.com/MasynNay/anything-plays/issues/25). A later 3.1.2 hotfix should only ship for a demonstrated issue with its own platform-specific tests. Do not confuse earlier owner 3.0/3.1 RC tests with acceptance of every new device.

## Next: 3.2 — Setup and control experience

**Development underway:** A source-only 3.2 branch introduces versioned, privacy-safe per-console control-profile export/import with confirmation, legacy migration and same-session undo; see [3.2 setup and controls](V3_2_SETUP_CONTROLS.md). This is not a 3.2 release or hardware validation. Camera calibration, controller onboarding and diagnostics remain pending.

**Goal:** A first-time user should be able to go from installation to a working camera or keyboard-controlled game without reading technical documentation.

1. **Local camera calibration wizard.** Guide camera selection, color sampling, lighting, live zone feedback and target stability in a small flow, with an expert path still available. Show measurable jitter, lost tracking and zone-trigger events; avoid false accuracy promises. [Feature issue #29](https://github.com/MasynNay/anything-plays/issues/29).
2. **Simple gamepad and keyboard setup.** A controller connection checklist, clearly grouped buttons and sticks, per-console live testing, plain-language remapping and a safe reset.
3. **Portable layout export/import.** Versioned, privacy-conscious settings files containing input mappings, color controls and theme preferences, **not** game ROMs, personal paths, camera frames, credentials or saves. Validate malformed files, show a preview and allow rollback before applying. [Feature issue #30](https://github.com/MasynNay/anything-plays/issues/30).
4. **Easier diagnostics and help.** Visible explanations for camera access, unsupported game frames, missing cores, controller disconnects and update availability; one-click copy of redacted diagnostics where appropriate.

**Success:** Successful setup with fewer steps, measured reduction in spurious tracking triggers, deterministic validation tests and clean migration between supported operating systems.

## Then: 3.3 — Performance and creator tools

**Goal:** Improve actual gameplay responsiveness and make Stream Mode resilient during long streams.

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
- No dates are committed for 3.2 or 3.3. Triage 3.1.1 issues through [GitHub Issues](https://github.com/MasynNay/anything-plays/issues), test changes and only publish incremental fixes when verified.

## Historical engineering log

The prior roadmap contained a detailed chronological record of 3.1 Preview, RC1, RC2, source-wheel and native-library testing, most of which preceded the successful public stable release. That complete snapshot is preserved in [the pre-3.1-stable roadmap archive](development/ROADMAP_PRE_3_1_STABLE_ARCHIVE.md). Current release evidence is in [3.1 acceptance](V3_1_RELEASE_ACCEPTANCE.md) and the [engineering checkpoint](development/CONTINUE_HERE.md). Those records remain available without burying the current product roadmap.
