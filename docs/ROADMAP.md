# Anything Plays — Roadmap

**If it moves, it plays.** This roadmap tracks what has shipped, what has been verified in development, and where the project is going. It deliberately separates completed engineering work from public release availability.

[Website](https://anythingplays.masynnay.com/) · [Latest public release](https://github.com/MasynNay/anything-plays/releases/latest) · [Issues](https://github.com/MasynNay/anything-plays/issues) · [Architecture](ARCHITECTURE.md)

## Progress at a glance

| Milestone | Status | Result |
| --- | --- | --- |
| **1.5** — Original desktop application | Released | Camera-driven controls and local emulation |
| **2.0** — Expanded studio | Released | Game Boy, Game Boy Color, GBA, SNES; ROM libraries, themes and configurable zones |
| **3.0** — Unified offline console library | **Released · November 9, 2026** | 18 console profiles using 11 original-source-built cores, including Nintendo 64 and GameCube |
| **3.1** — Stream Mode, optional gamepads and themed bezels | **Public RC2 prerelease · November 11, 2026** | [Four-platform RC2](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc2); customizable dual-screen OBS output, separate stream settings, live controller tester; hardware and full native source/relinking review still open |
| **3.x** — Compatibility and polish | Planned | Smooth 3D performance, simpler setup, better save diagnostics and long-session stability |

**3.1 Windows modified-source native C milestone:** [Genuine Windows MSVC compile and copied RC1 runtime](https://github.com/MasynNay/anything-plays/actions/runs/42953456034) **PASSED**. The upstream pinned SDL2 2.32.10 SDK, source changes, PE AMD64 identity, observable native method, and actual frozen Tk desktop were checked. Combined with prior Linux and Mac tests, **all four platforms** pass source-modified pygame C tests, not just official-wheel swaps. All stable-release licensing, source correspondence, and real-device requirements remain open. [Full Windows evidence](V3_1_LGPL_ACTUAL_MODIFIED_PYGAME_WINDOWS_SOURCE_QA.md).

**3.1 full modified-C source test, all four OS:** [Mac Apple Silicon and Intel](https://github.com/MasynNay/anything-plays/actions/runs/42951159759) now pass full native source recompilation, in-app SDL relinking, ad-hoc code signing and copied 18-console RC1 frozen desktop startup. Linux and Windows source-modified C tests have also passed. Complete LGPL correspondence, other covered dependencies, physical controllers and final stable acceptance remain open. [Mac evidence](V3_1_LGPL_SOURCE_MODIFIED_MACOS_QA.md).

**3.1 genuinely modified LGPL source:** [Native pygame-ce C source rebuild and copied Linux RC1 runtime PASSED](https://github.com/MasynNay/anything-plays/actions/runs/42949949019) — changed source compiled, new C method executed from installed replacement, original frozen Tk desktop booted. Windows and both Mac source-modified tests now pass too; complete legal/source acceptance remains open. [Details](V3_1_LGPL_ACTUAL_MODIFIED_PYGAME_LINUX_SOURCE_QA.md).

**3.1 verified four-platform upstream native swap:** [Windows and Linux frozen installed-app tests](https://github.com/MasynNay/anything-plays/actions/runs/42937982305) and [Mac upstream replacement/signing](https://github.com/MasynNay/anything-plays/actions/runs/42936779875) now pass on all four platforms. Linux and Windows original wheel bytes are identical to the installed native files; a genuinely **source-modified pygame.base** has now also been verified on all four platforms, but full LGPL legal acceptance remains open. [Evidence](V3_1_LGPL_FOUR_PLATFORM_UPSTREAM_REPLACEMENT_QA.md).

**3.1 actual macOS native replacement test:** [Both original RC1 Mac installers passed](https://github.com/MasynNay/anything-plays/actions/runs/42936779875) when pygame's native base extension was replaced in a **disposable app copy** by a matching official wheel slice, re-signed, dynamically loaded and started with the actual frozen Tk smoke test. A source-modified pygame C library has now also been compiled and loaded on all four OSes; full legal LGPL review remains open.

**3.1 signed Mac provenance:** [Read-only genuine RC1 Mac audit](https://github.com/MasynNay/anything-plays/actions/runs/42925583942)
and [official OpenCV follow-up](https://github.com/MasynNay/anything-plays/actions/runs/42926295393) mapped **241/241**
pygame/SDL native executable text sections to pinned upstream wheels.
The complete source and LGPL relinking reviews remain open.

**3.1 RC2 verification:** The independent RC2 build and installed Stream Mode
startup checks were added across all four native CI hosts, with a complete
18-console original-source installer set, isolated 3.0/RC1 settings and
exact SHA-256 provenance. See the [RC2 four-platform acceptance run](https://github.com/MasynNay/anything-plays/actions/runs/43079085633) and
[Stream Mode design and limitations](V3_1_STREAM_MODE.md).
Physical camera/controller testing and full corresponding-source/relinking
review are not certified. 3.0.0 remains the most recent *stable* release.

**Historical RC1 verification:** The 3.1 RC1 application, 18-console QA
installers and installed GUI checks passed on all four OS targets;
[six pinned pygame/SDL original-source candidates](https://github.com/MasynNay/anything-plays/actions/runs/42909893531)
were also preserved. The hardware gameplay, full LGPL source/relinking and
final stable release requirements remain open. The original public [3.1 RC1 prerelease](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc1) remains available; the new [3.1 RC2 prerelease](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc2) contains Stream Mode. Stable 3.0.0 remains latest until final 3.1.0 acceptance.
**3.1 endurance QA:** [Three-minute Linux source soak](https://github.com/MasynNay/anything-plays/actions/runs/42909405091) passed with 10,371 synthetic game frames, active SDL input polling, and 0.05 MB
measured RSS growth. This does not certify a physical gamepad or
retail ROM endurance. Five original SDL license texts were also preserved
in the [six-source upstream companion](https://github.com/MasynNay/anything-plays/actions/runs/42909893531).

**3.1 owner testing:** The four-source-built, 18-console RC1 installers, original-source candidates and checksum reports are retained in a [90-day QA collection](https://github.com/MasynNay/anything-plays/actions/runs/42911996640) (through February 8, 2027). The 3.1 RC1 prerelease is publicly available; final stable 3.1.0 has not been published. Stable installer identity, precise native licensing, and physical controller acceptance remain open.

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

See the [3.1 release acceptance checklist](V3_1_RELEASE_ACCEPTANCE.md) before considering a **stable 3.1.0** release.

### Preview 1 packaging and owner QA (unreleased)

- Four dedicated build jobs run on Windows x64, Linux x64, macOS Apple Silicon and macOS Intel. Each retains a SHA-256-recorded installer as a seven-day GitHub Actions artifact, **never a GitHub Release**.
- Preview 1 uses distinct application identifiers and a separate 3.1 settings directory. It cannot overwrite the stable 3.0 installation or the older 3.0 test-preview installation.
- This is deliberately an initial controller and GUI acceptance build containing only the mGBA native core (GB, GBC, GBA). Other system selections may be visible but their cores are not included, and the full 18-system offline package is **not** claimed.
- Test users should verify real controller recognition and button remapping first; complete physical-device and redistribution approvals remain future release gates.

## 3.1 — Stream Mode and controls (public RC2 prerelease; stable acceptance ongoing)

**What RC2 adds:** The real desktop Stream Mode mirrors current embedded
gameplay and annotated camera tracking into a dedicated, resizable OBS Window
Capture surface with an original DS-inspired dual-screen bezel. A separate
settings window customizes portrait/landscape arrangement, game/camera order,
16 themes, border color/thickness, screen proportions, labels and
15/24/30 FPS refresh; Stream Mode never opens a second webcam or emulator.
Output settings migrate safely into the independent RC2 preferences space.
The source-level dual-screen renderer, Tk smoke and four-platform installed
acceptance tests are documented in [Stream Mode](V3_1_STREAM_MODE.md).
External emulators may need their own OBS capture. Audio comes from OBS,
not from a new streaming/recording service within Anything Plays.

**Historical RC1 scope:** Public RC1 introduced controller mapping, visual
button feedback, hotplug recovery, and isolation from stable 3.0. The record
below captures its verified test milestones and is retained for provenance.

**Newest verified 3.1 RC1 (November 10, 2026):**
four platform-native application builds with the atomic settings fix
[passed 4/4](https://github.com/MasynNay/anything-plays/actions/runs/42892417937); complete original-source 18-console
installers [passed 4/4](https://github.com/MasynNay/anything-plays/actions/runs/42894172881); **actual installed Tk
startup and 3.0-to-RC preference copy** [passed 4/4](https://github.com/MasynNay/anything-plays/actions/runs/42895538165).
The seeded disposable-home tests prove the original stable
preferences and profiles remained byte-for-byte unchanged.
Four-platform concurrency, symlink and interrupted-copy tests
[passed 4/4](https://github.com/MasynNay/anything-plays/actions/runs/42893632730).
[Atomic settings migration details](V3_1_ATOMIC_SETTINGS_MIGRATION.md).
Physical gamepad/camera integration and new SDL/LGPL rights review
remain **OPEN**; this is not a stable 3.1 release.


**New verified native RC1 audits:** SDL source/wheel checks, signed Mac
library inspection, duplicate SDL2 detection, two-architecture
dynamic loading and native SDL virtual joystick button press/release
all passed against the *refreshed current RC1*.
Mac original-wheel binary correspondence and physical hardware acceptance
remain **OPEN**. [Updated SDL native QA](V3_1_REFRESHED_SDL_NATIVE_QA.md).



**Newest verified development candidate (November 10, 2026):** The
updated 3.1 source app includes local Copy diagnostics, full
four-platform camera/controller integration tests, and persistent
clipboard feedback. [New source apps](https://github.com/MasynNay/anything-plays/actions/runs/42885525444) passed 4/4,
[full 18-console owner-QA installers](https://github.com/MasynNay/anything-plays/actions/runs/42886791394) passed
4/4, and [installed GUI boots](https://github.com/MasynNay/anything-plays/actions/runs/42887470580) passed 4/4.
[Pixel-tracking plus synthetic SDL input](https://github.com/MasynNay/anything-plays/actions/runs/42884824976)
passed on all four OSes with 18 profiles and 1,000 frames, while
[private controller report tests](https://github.com/MasynNay/anything-plays/actions/runs/42885687277)
passed four-platform clipboard and redaction checks.
All packages remain temporary nonrelease QA, and hardware, native
corresponding-source/LGPL and stable-release gates remain OPEN.


**Release channels:** Stable 3.0 installers and original core sources remain
available. Public RC1 and RC2 are distinct, genuinely built 3.1 prereleases;
they are **not** approved stable 3.1.0 installers. The RC2 development branch
and source-pinned QA receipts track the current release candidate separately.

- Game Controls button replaces the old Keyboard shortcuts label above gameplay.
- Step 8 now has a dedicated Keyboard Shortcuts button; both open editable per-console keyboard keys.
- Keep one control-label sizing slider beside the camera preview; remove the redundant advanced right-side control.
- Add optional SDL2 gamepad input for embedded manual play, per-console configurable mappings, D-pad and analog stick directions, and connection/rescan status. Controller and keyboard holds remain independent.
- Add a small theme-matched controller graphic and one-click controller setup beneath Display & Sound on the right; group physical buttons visually by D-pad, face, menu, sticks and triggers. Keep keyboard shortcuts in their dedicated dialog rather than duplicating switches.
- **Hardware-free CI simulation:** Replay 18 console profiles, buttons, sticks, triggers, remapping, hotplug, focus changes and stale-input recovery on Linux, Windows, macOS Apple Silicon and macOS Intel, while also initializing each host's actual pygame SDL runtime. Physical hardware testing remains separate.
- **Live input diagnostics:** The controller setup now identifies physical button/stick inputs without loading a ROM; Rescan immediately clears any held controller buttons. A new regression suite covers detection, lost focus, disconnects and invalid preferences, and is configured for the four operating-system CI runners. Physical HID acceptance remains separate.
- **Full-library QA packaging:** 18 profiles / 11 source-built emulator
  cores passed across Linux x64, Windows x64, macOS ARM64 and Intel, with
  exact 3.0 binary provenance and package verification. [Evidence](V3_1_RELEASE_ACCEPTANCE.md).
  The packages remain unreleased QA artifacts, not stable installers.
- **Updated controller build and frozen-runtime audit:** Newer QA candidates
  replace the old frozen controller executable with the version containing
  live button diagnostics and immediate Rescan release, preserving original
  3.0 native-core hashes. A byte-verified pygame-ce LGPL notice now ships
  alongside an explicit JSON audit of actual frozen pygame/SDL libraries.
  [Audit method](V3_1_SDL_RUNTIME_AUDIT.md). All four updated
  Windows/Linux/macOS QA packages passed checks, including installed SDL
  native inventory and pinned LGPL text.
  [Verified runs](V3_1_RELEASE_ACCEPTANCE.md). This is **not yet stable
  release readiness**; real-device gameplay, corresponding native SDL source
  and true 3.1.0 stable-identity installers remain open.
- **Fresh 3.1 RC1 application and complete library: Verified.** Separate,
  truly source-built 3.1 applications (not renamed frozen Preview 1 code)
  passed Windows, Linux, Apple Silicon and Intel
  [run 42863846059](https://github.com/MasynNay/anything-plays/actions/runs/42863846059).
  Each was then combined with exactly the reviewed public 3.0 original-source
  eleven-core set, and all four new **full 18-console RC1 QA packages passed**
  [run 42865608433](https://github.com/MasynNay/anything-plays/actions/runs/42865608433),
  with checksummed installer, native-core verification and SDL inventory.
  [New test downloads](V3_1_RC_QA_DOWNLOADS.md). Candidate installation IDs
  and preferences are isolated from 3.0. This does not pass hardware,
  corresponding-source/rights or final stable release approval.
- **pygame/SDL source-review evidence:** Original pygame-ce 2.5.8 git
  sources (pinned commit `c8200a9`) now archived; official Python 3.13
  release-wheel hashes verified and compared to the full RC1 packages.
  Linux has **74/74** byte matches, Windows **62/62** for the audited
  native files. The two signed, architecture-specific Mac packages
  are still unmatched against wheel bytes; their **121 ARM and 120 Intel**
  native dylibs now have separate validated `otool`, `lipo` and
  `codesign` reports.
  [Source correspondence investigation](V3_1_SDL_SOURCE_REVIEW.md).
  This advances traceability, **not** legal approval; additional native
  source build provenance and LGPL replacement/relinking review are open.
- **Actual installed desktop UI QA: Verified 4/4.**
  The complete Windows, Linux and two Mac RC1 installers now pass
  independent **real frozen Tk window/App startup and event-loop tests**
  on clean native CI runners
  ([run 42880420023](https://github.com/MasynNay/anything-plays/actions/runs/42880420023)).
  This is stronger than packaging-only verification but does not
  certify actual camera, gamepad or game ROM operation.
  [Startup QA details](V3_1_INSTALLED_UI_QA.md).
- **SDL2 source/loader evidence expanded:** Apple Silicon contains
  two different signed `libSDL2-2.0.0.dylib` versions sharing a library
  name (Mach-O 3201.8.0 and 3201.10.0); Intel has no equivalent
  audited basename collision. Full
  [dual-library audit](https://github.com/MasynNay/anything-plays/actions/runs/42879312220)
  passed. Original-source references for **both SDL2 versions** plus
  SDL2_image, SDL2_mixer and SDL2_ttf are now pinned and archived from
  authentic Git commits
  ([source QA run 42879614179](https://github.com/MasynNay/anything-plays/actions/runs/42879614179)).
  The next [signed native macOS dynamic-loader test](https://github.com/MasynNay/anything-plays/actions/runs/42881412802)
  **PASSED both architectures**. On Apple Silicon the actual 2.32.8
  and 2.32.10 dylibs loaded in both orders and reported the expected
  versions; Intel's 2.32.10 also loaded. Keep simultaneous actual
  OpenCV camera/controller gameplay and exact binary-to-source
  correspondence OPEN until measured independently.
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
