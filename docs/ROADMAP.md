# Anything Plays — Roadmap

**If it moves, it plays.** This roadmap tracks what has shipped, what has been verified in development, and where the project is going. It deliberately separates completed engineering work from public release availability.

[Website](https://anythingplays.masynnay.com/) · [Latest public release](https://github.com/MasynNay/anything-plays/releases/latest) · [Issues](https://github.com/MasynNay/anything-plays/issues) · [Architecture](ARCHITECTURE.md)

## Progress at a glance

| Milestone | Status | Result |
| --- | --- | --- |
| **1.5** — Original desktop application | Released | Camera-driven controls and local emulation |
| **2.0** — Expanded studio | Released | Game Boy, Game Boy Color, GBA, SNES; ROM libraries, themes and configurable zones |
| **3.0** — Unified offline console library | **Released · November 9, 2026** | 18 console profiles using 11 original-source-built cores, including Nintendo 64 and GameCube |
| **3.x** — Compatibility and polish | Planned | Smooth 3D performance, simpler setup, better save diagnostics and long-session stability |

**Download status:** [Anything Plays 3.0.0 is publicly released](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0) with four genuine offline installers and [original emulator sources](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources). Stable 2.0 and 1.5 remain available in previous releases.

## Version 3.0 — Shipped features

The public stable 3.0 release expands from four supported console profiles to 18, with integrated Nintendo 64 and GameCube alongside handhelds and classic systems.

**Implemented**

- Eleven native emulator cores from pinned original upstream sources, including Dolphin and GPL-2.0-or-later Tia.
- Offline desktop packages for Windows x64, Linux x64, macOS Apple Silicon and macOS Intel.
- ROM-library browsing, per-console settings and flexible input-zone layouts.
- Local camera and keyboard controls, a control-label sizing slider and volume controls.
- Improved N64 game unload/reload behavior and GameCube initialization.
- Packaged original emulator notices and corresponding-source provenance.

**Verified**

- The original four-platform source-built [integration run](https://github.com/MasynNay/anything-plays/actions/runs/42686588072) passed native emulator, frozen UI, graphics/audio, and seven-session switching checks.
- The [source correspondence audit](https://github.com/MasynNay/anything-plays/actions/runs/42717944132) matched 44 compiled emulator libraries to eleven pinned upstream source trees, including 37 Dolphin Git-linked source dependencies.
- The maintainer has personally tested N64 game switching and GameCube, including testing on Windows, Linux and Apple Silicon. These reports count as valuable real-world testing.
- The [genuine stable 3.0.0 installer build](https://github.com/MasynNay/anything-plays/actions/runs/42718569352) passed all four operating-system targets. The [source-first public publisher](https://github.com/MasynNay/anything-plays/actions/runs/42724633466) also completed successfully, publishing original sources and SHA256 checksums before public installers.

**Known limitations**

Individual game compatibility, graphics performance, physical cameras, save types, and extended-session stability vary by computer and are not exhaustively certified. Unsigned Windows installers and macOS applications without Apple notarization may display operating-system warnings. No commercial ROMs or console firmware are included.

The distinction between technical source proof and upstream licensing obligations is explained in [the source audit](V3_0_EXACT_RUNTIME_LICENSE_SCOPE.md) and [release assessment](V3_0_SOURCE_FIRST_RELEASE_DECISION.md). These details belong in the engineering documentation, not the landing page.

### Preview 1 packaging and owner QA (unreleased)

- Four dedicated build jobs run on Windows x64, Linux x64, macOS Apple Silicon and macOS Intel. Each retains a SHA-256-recorded installer as a seven-day GitHub Actions artifact, **never a GitHub Release**.
- Preview 1 uses distinct application identifiers and a separate 3.1 settings directory. It cannot overwrite the stable 3.0 installation or the older 3.0 test-preview installation.
- This is deliberately an initial controller and GUI acceptance build containing only the mGBA native core (GB, GBC, GBA). Other system selections may be visible but their cores are not included, and the full 18-system offline package is **not** claimed.
- Test users should verify real controller recognition and button remapping first; complete physical-device and redistribution approvals remain future release gates.

## 3.1 — Controls and usability (development branch, unreleased)

**Development only:** Work is isolated on `feature/v3.1-controls-usability`.
No 3.1 installers or release tags have been published; 3.0 remains stable.

- Game Controls button replaces the old Keyboard shortcuts label above gameplay.
- Step 8 now has a dedicated Keyboard Shortcuts button; both open editable per-console keyboard keys.
- Keep one control-label sizing slider beside the camera preview; remove the redundant advanced right-side control.
- Add optional SDL2 gamepad input for embedded manual play, per-console configurable mappings, D-pad and analog stick directions, and connection/rescan status. Controller and keyboard holds remain independent.
- Add a small theme-matched controller graphic and one-click controller setup beneath Display & Sound on the right; group physical buttons visually by D-pad, face, menu, sticks and triggers. Keep keyboard shortcuts in their dedicated dialog rather than duplicating switches.
- **Hardware-free CI simulation:** Replay 18 console profiles, buttons, sticks, triggers, remapping, hotplug, focus changes and stale-input recovery on Linux, Windows, macOS Apple Silicon and macOS Intel, while also initializing each host's actual pygame SDL runtime. Physical hardware testing remains separate.
- **Release gates:** unit and UI tests; packaging smoke on Windows, Linux and both Mac architectures; physical Xbox/PlayStation gamepad hotplug, save/reload, focus loss, shutdown and long-session tests; and third-party LGPL/SDL redistribution review.
- 3.1 should not be promoted to a stable public release until hardware acceptance and packaging checks are complete.

## Next priorities

| Priority | Focus | Success criteria |
| --- | --- | --- |
| **Shipped** | 3.0 release and source distribution | Four public installers, original emulator sources, checksums and release notes verified November 9, 2026 |
| **P1** | Reliability and saved games | Repeatable save/reload, core switching and graceful recovery from failed ROM loads |
| **P2** | GameCube performance | Measure actual emulation FPS and rendered preview FPS separately; improve frame pacing without damaging correctness |
| **P2** | Camera usability | Faster color calibration, clearer multi-object indicators and accessible diagnostics |
| **P2** | Installation and updates | Better package verification, user-friendly update checks and straightforward offline usage |
| **P3** | Profiles and customization | Portable settings, easier controller layouts, cleaner multi-player mapping and theme consistency |
| **P3** | Long-session quality | Track memory growth, background worker cleanup, repeated game transitions and crash recovery |

Priorities are engineering directions, **not promises of a release date**. Changes should ship with focused regression tests and useful documentation rather than cosmetic churn.

## Contributing and tracking

Use [GitHub Issues](https://github.com/MasynNay/anything-plays/issues) to report reproducible problems or suggest features. Include the affected operating system and console when relevant. The [contribution guide](../.github/CONTRIBUTING.md) explains testing and code expectations.

For anyone who wants the original CI logs, source hashes, dependency notices or build procedure, start with the [technical documentation index](README.md). The detailed append-only [engineering checkpoint](development/CONTINUE_HERE.md) is retained for development recovery and is **not** the public product roadmap.
