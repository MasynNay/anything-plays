# Anything Plays 3.1 — Release acceptance

**Status: RC2 PUBLIC PRERELEASE, NOT READY FOR FINAL STABLE 3.1.0.** This document tracks evidence,
not a promise of a release date. Stable 3.0 stays public and untouched.

## Current release state — November 11, 2026

The public [3.1 RC2 test release](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc2) offers four checked platform installers with customizable dual-screen Stream Mode, camera/emulator bezels and optional gamepad controls. The [complete RC2 native and installed-GUI acceptance run](https://github.com/MasynNay/anything-plays/actions/runs/43079085633) passed for Windows x64, Linux x64, macOS Apple Silicon and macOS Intel. It covers 18 console profiles using the 11 original source-built core families. These are CI and installed-app tests, **not** general physical webcam/controller, retail-game, save or long-session certification.

The post-RC2 source hardening in [PR #197](https://github.com/MasynNay/anything-plays/pull/197) has also been merged after Python 3.12, Python 3.13, native mGBA and GUI smoke checks passed: an unplugged webcam whose status probe fails no longer leaves its private last frame visible in Stream Output. **This later fix is on main, not inside the immutable public RC2 installer assets.** It must be included in a newly built and revalidated candidate before being claimed as shipped.

## Owner Linux RC2 installation check — November 11, 2026

**User-reported PASS, limited scope:** The project owner installed the public 3.1 RC2 Linux `.deb` package on a real Linux desktop and confirmed the application **launches successfully**. This is a useful real-device installation/startup check in addition to the four-platform automated installed-app acceptance. It is not independent CI evidence or proof of sustained compatibility.

**Owner follow-up, Stream Mode visual check (user-reported PASS):** After being asked to open Stream Mode and confirm its DS-style dual-screen game/camera layout, the owner reported that it **works perfectly** on the installed Linux RC2 build and expressed satisfaction with the experience. This supports an owner-observed positive first-look of the Stream Mode window and layout. It does **not** independently verify live webcam tracking, camera device capture, OBS recording/Window Capture output, controller hardware, or game content within those panes.

**Not tested or not yet reported in this session:** a physical controller, live webcam, actual OBS capture, sustained gameplay, game audio, saves, long sessions, other platforms, or native dependency relinking. Those remain open; do not mark them as passed based solely on the successful launch and Stream Mode visual report.

**Still required before stable 3.1.0:** real cameras and controllers on supported hardware; actual gameplay, audio, save and extended-session checks; complete native corresponding-source and LGPL relinking/replacement review; fresh stable-version binaries, signed/notarization limitations and exact checksum/source receipts; final release notes and explicit stable-release decision. All six existing stable release gates remain false.

**New verified native RC1 audits:** SDL source/wheel checks, signed Mac
library inspection, duplicate SDL2 detection, two-architecture
dynamic loading and native SDL virtual joystick button press/release
all passed against the *refreshed current RC1*.
Mac original-wheel binary correspondence and physical hardware acceptance
remain **OPEN**. [Updated SDL native QA](V3_1_REFRESHED_SDL_NATIVE_QA.md).


## All four operating systems: real source-modified pygame C extension — PASSED

The [Windows original RC1 modified-source Windows CI](https://github.com/MasynNay/anything-plays/actions/runs/42953456034) **PASSED**.
An actual Visual C compiler built an AMD64 CPython 3.13 native
`pygame.base` from the same **changed** pinned pygame-ce 2.5.8
`src_c/base.c` used on Linux and both Macs, with the published
SHA-verified SDL2 2.32.10 developer SDK. The native binary differs
from the original upstream wheel; its new C method was loaded and
executed **from a disposable copy of the actual Windows RC1**.
The copied genuine 18-console frozen desktop successfully started its
Tk event loop and preserved isolated stable 3.0 preferences.

Together with the [Linux source build](https://github.com/MasynNay/anything-plays/actions/runs/42949949019)
and [both Mac source builds](https://github.com/MasynNay/anything-plays/actions/runs/42951159759),
a genuine **source-modified pygame native extension** has now been
compiled and executed on **all four supported platforms**. The
original RC1 installer, signed Mac DMGs, stable 3.0, 2.0 and user
settings were not modified.

These tests cover **one native extension**, not all covered dependencies,
a full GNU LGPL 2.1 Section 6 compliance determination, actual
physical controllers, or final stable 3.1.0 acceptance. [Detailed
Windows and four-platform evidence](V3_1_LGPL_ACTUAL_MODIFIED_PYGAME_WINDOWS_SOURCE_QA.md).

**All six stable-release gates remain false.**

## Historical milestone: genuine source-modified pygame C on both Macs — PASSED

[Source-build and real signed RC1 runtime workflow](https://github.com/MasynNay/anything-plays/actions/runs/42951159759) **PASSED
Apple Silicon and Intel Mac**. Both runners compiled exact upstream
SDL2 **2.32.10** from commit
`5d249570393f7a37e037abf22cd6012a4cc56a71` (matching the
app's bundled SDL), then built the **actually changed** pygame-ce
2.5.8 native C extension with Meson/Ninja. The compiled native binary
differed from original signed wheel code. An isolated disposable copy
of the original signed 18-console RC1 DMG had the extension replaced,
its loader relinked to the existing in-app SDL2, and the changed
binary and app ad-hoc signed and verified.

Actual native CPython 3.13 imported the copied native extension and
invoked its new C method successfully. Both copied original frozen
desktop applications started the real Tk GUI, while 3.0 settings
fixtures remained unchanged. Original DMGs, user data and public
releases were not modified.

At this intermediate stage, Linux and both Mac architectures had
passed and Windows was still pending. **Windows has since passed**;
see the four-platform result above. Complete LGPL source/relinking,
real controller testing, and stable 3.1.0 remain open. [Detailed two-Mac report](V3_1_LGPL_SOURCE_MODIFIED_MACOS_QA.md).

## Verified genuine source-modified LGPL pygame-ce on Linux

[Build and runtime QA](https://github.com/MasynNay/anything-plays/actions/runs/42949949019) **PASSED** against the authentic 3.1 RC1 Linux installer. CI pinned the original pygame-ce 2.5.8 Git commit and LGPL license, patched C source `src_c/base.c` to add a callable method, compiled the changed native CPython 3.13 extension with Meson/Ninja, and swapped its different bytes into a disposable 18-console RC1 app copy. External CPython loaded **the copied app's native file** and invoked the new method; the real frozen RC1 desktop also booted and stable preferences stayed untouched.

Unlike the earlier Linux byte-identical upstream wheel swap, **this proves a changed-source native extension can run**. It does NOT yet prove compiled changes on the other three OSes, actual controller use, all LGPL library replacement/relinking or full corresponding-source/legal compliance. [Evidence and limitations](V3_1_LGPL_ACTUAL_MODIFIED_PYGAME_LINUX_SOURCE_QA.md). All stable 3.1 release approval flags remain false.

## Four-platform original pygame wheel swap and real desktop startup

**All four operating systems passed** limited upstream pygame extension
swap acceptance against genuine pinned full 3.1 RC1 installers. Linux
and Windows had byte-identical original native wheel bytes, and copied
installations passed actual frozen desktop Tk startup plus isolated
legacy settings tests: [two-platform workflow](https://github.com/MasynNay/anything-plays/actions/runs/42937982305).
Apple Silicon and Intel Mac copies replaced differently signed/thinned
compiled base extensions, were ad-hoc re-signed, loaded through the
actual Python native loader and passed frozen GUI startup:
[Mac workflow](https://github.com/MasynNay/anything-plays/actions/runs/42936779875).

These demonstrate practical installation layout and certain native
replacement mechanisms, **not modified-from-source LGPL binaries, complete
corresponding source, legal clearance or final 3.1.0 stable approval.**
[Full limitations and upcoming tests](V3_1_LGPL_FOUR_PLATFORM_UPSTREAM_REPLACEMENT_QA.md).

## New verified macOS LGPL native extension replacement test

The independent [macOS replacement workflow](https://github.com/MasynNay/anything-plays/actions/runs/42936779875) PASSED on both
Apple Silicon and Intel on genuine RC1 builds. A disposable app copy
received the exact SHA-verified official pygame-ce wheel's
`pygame.base` native extension; each copied app was ad-hoc
re-signed, passed a live native loader test, and successfully ran
the **actual frozen Tk desktop GUI smoke**. The readonly original
DMG remained unchanged. See
[step-by-step evidence](V3_1_LGPL_UPSTREAM_EXTENSION_REPLACEMENT_QA.md).

This verifies a practical **upstream ABI-compatible extension swap**,
not a recompiled user modification, complete LGPL compliance or
full native corresponding source. All six final 3.1.0 stable gates
and production release approval remain **false**.

## Verified signed macOS wheel code provenance — November 10, 2026

The original signed 3.1 RC1 Mac installers were independently compared
against official pinned pygame-ce and OpenCV wheels: **241/241** compiled
native `__TEXT,__text` sections matched. Apple Silicon: pygame **120/121**,
OpenCV SDL **1/1**; Intel: pygame **120/120**. These are *code section*
matches, not whole-file binary, corresponding-source or LGPL relinking
approval. [Two-Mac audit](https://github.com/MasynNay/anything-plays/actions/runs/42925583942) · [OpenCV follow-up](https://github.com/MasynNay/anything-plays/actions/runs/42926295393) ·
[Technical details](V3_1_SIGNED_MACOS_WHEEL_CORRESPONDENCE.md).

All six stable 3.1.0 gates and public final-release approval remain false.

## Public RC1 release completed, stable acceptance remains open

**[Anything Plays 3.1 RC1 is publicly downloadable](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc1)** as a prerelease with authentic Windows x64, Linux x64, Mac ARM and Mac Intel packages, original SDL/pygame source candidates and matching asset SHA-256 checksums. The controller-enabled app and packaging files on main were independently checked to match the exact source used for RC1 builds. Public release workflow [42920357069](https://github.com/MasynNay/anything-plays/actions/runs/42920357069) PASSED.

The original GitHub 403 was caused by targeting a development commit containing workflow changes not yet present on the default branch. Creating a *private draft* targeted at main resolved the write-permission failure; the full 3.1 source was then merged and publication succeeded. Stable 3.0/2.0 releases were untouched.

**Do not confuse RC1 publication with stable 3.1.0 approval.** Physical hardware, real gameplay and complete LGPL source/relinking certification remain open. The six stable gates and the owner stable-release approval flag remain false.

## Current owner QA handoff: all four real packages preserved

The [90-day combined QA collection](https://github.com/MasynNay/anything-plays/actions/runs/42911996640) succeeded on November 10, 2026,
retaining 472 MB of the genuine four-platform full RC1 installers,
SHA-256 checksums and original-source candidate report. The artifact
expires **February 8, 2027**. It is not a newly built production
3.1.0 installer, and existing public 3.0.0/2.0 are unchanged.

**Historical publishing access issue (resolved for RC1):** An earlier
GitHub Actions run with `Contents: write` received HTTP 403 when
creating a release. That attempt produced no draft. The separate
source-matched publication workflow subsequently succeeded and public
3.1 RC1 is available above. Stable 3.1.0 publication still requires
all outstanding release acceptance evidence.

### Current original-source candidate bundle (technical QA only)

[Six-source archive and checksum companion](https://github.com/MasynNay/anything-plays/actions/runs/42909893531) **PASS**.
All five pinned SDL upstream source candidates plus the pinned pygame-ce
Git-tag source are retained with an SHA-256 list and the current frozen
runtime audit. Source-to-compiled-binary and LGPL relinking review remain
**OPEN**; this result does not close the third-party source release gate.

## Latest source-built 3.1 RC1 acceptance — November 10, 2026

- **Fresh source-built 3.1 application 4/4 PASS:**
  [42904937464](https://github.com/MasynNay/anything-plays/actions/runs/42904937464), from exact controller-recovery
  revision `26de1e1ad1b701d0735e085158347f8c213ce437`.
- **Fresh 18-console, 11-original-core full QA installers 4/4 PASS:**
  [42905694504](https://github.com/MasynNay/anything-plays/actions/runs/42905694504), with all four nonrelease installers,
  verified native 3.0 source-built core hashes and SDL audits retained.
  The four-platform assembly configuration commit is
  `c67fab048d7e44f371f2589a6d73b9d556de84d0`.
- **Real frozen installed Tk startup and stable-preference migration
  4/4 PASS:** [42906122307](https://github.com/MasynNay/anything-plays/actions/runs/42906122307); original test-file
  SHA-256 digests remained unchanged, and RC settings were created in a
  different namespace.
- **Controller source regression and native mGBA PASS 4/4:**
  [42905694745](https://github.com/MasynNay/anything-plays/actions/runs/42905694745), including new SDL failure, hotplug
  retry, missing-name and safe-shutdown tests.
- **Exact latest upstream pygame-ce/SDL source/wheel candidate review PASS:**
  [42906334464](https://github.com/MasynNay/anything-plays/actions/runs/42906334464).
- **Exact latest signed macOS native linkage PASS 2/2:**
  [42906227613](https://github.com/MasynNay/anything-plays/actions/runs/42906227613).
  Dual SDL2 library collision detection
  [42906533420](https://github.com/MasynNay/anything-plays/actions/runs/42906533420),
  actual signed SDL2 loader checks
  [42906533407](https://github.com/MasynNay/anything-plays/actions/runs/42906533407) and
  native **virtual** joystick press/release
  [42906533323](https://github.com/MasynNay/anything-plays/actions/runs/42906533323) passed their technical
  checks on the current binaries.

**Unresolved release responsibilities:** physical USB/Bluetooth controller
hotplug and physical camera/gameplay/audio/save/long-session acceptance;
complete native runtime corresponding-source identification and
LGPL notices/relinking/replacement review; true stable 3.1.0 installer
identity and final stable asset checksums; public documentation and
explicit approval. Historical 3.1 milestones below remain valid for
their *own* pinned older binaries only. **All six stable release gates
stay FALSE, and stable public 3.0.0 is untouched.**

### Sustained real Tk/SDL controller and synthetic-camera session

The [180-second source endurance run 42909405091](https://github.com/MasynNay/anything-plays/actions/runs/42909405091) **PASSED**
on Linux x64. It ran the actual Tk UI, pygame SDL polling, synthetic camera
and changing game frames together for 180 seconds, producing **10,371
synthetic frames** and **0.05 MB measured post-warmup RSS growth**.
Controller initialization/polling remained active; canvas/cache and
pending-timer resource bounds passed. The report explicitly states
that no physical controller, camera, retail game or native emulator
save/audio endurance was tested. This is useful engineering evidence
but **does not close physical or final-stable gameplay acceptance**.

## Latest four-platform upgrade safety milestone — VERIFIED 4/4

A new atomic, create-only 3.1 settings importer prevents incomplete
copy files and concurrent overwrites. It rejects malicious symlinks
and leaves existing RC settings intact. The real frozen 18-console
RC1 apps, built from `cdbd647fa8ef3f3db0a8d419f0396f6b191599d6`, have been independently
packaged on all four hosts
([run 42894172881](https://github.com/MasynNay/anything-plays/actions/runs/42894172881)) and then launched using a disposable
home seeded with known stable settings
([run 42895538165](https://github.com/MasynNay/anything-plays/actions/runs/42895538165)).
**All four installed GUI + settings-copy jobs PASSED.**

Each tested host imported the known `Plum Dark` theme into a separate
RC namespace while original stable preference and profile SHA-256
digests stayed unchanged; no actual user's home was modified.
The [new atomic/race/symlink source tests](https://github.com/MasynNay/anything-plays/actions/runs/42893632730) also PASSED
4/4 on Windows, Linux, Apple Silicon and Intel.
[Read detailed migration acceptance](V3_1_ATOMIC_SETTINGS_MIGRATION.md).

**Still OPEN:** physical USB/Bluetooth/camera/gameplay/save/endurance
acceptance, exact *current* SDL native corresponding source and LGPL
replacement/relinking review, reviewed stable 3.1.0 upgrade identity
and explicit release authorization. Never use the success above
to flip any of the six public release gates.

## Current reviewed source and full RC1 milestone — 4/4 PASS

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

The new 18-console installer source app is pinned to commit `fe0da0b8b5f478cf1172734ef38546c4f1e86229` and preserves the eleven verified original-source emulator core families. The earlier SDL/Mach-O source comparison was conducted on an **older** pinned RC1 installer and does not automatically prove correspondence for the newly signed full packages. Do not change the six release gates or mark public 3.1 approved.

## What is already working

- [x] The 3.1 source branch includes Game Controls, per-console mapping,
  manual SDL gamepad input, and theme-aware controller settings.
- [x] Windows, Linux, Apple Silicon, and Intel Mac synthetic gamepad
  simulations passed through real input handling on
  [the four-platform run](https://github.com/MasynNay/anything-plays/actions/runs/42771771434).
- [x] Python 3.12/3.13 unit tests, real Tk GUI smoke, and native mGBA
  compatibility passed at
  [the latest 3.1 source run](https://github.com/MasynNay/anything-plays/actions/runs/42822880056).
- [x] Four *unreleased*, isolated 3.1 Preview 1 installers built and retained
  as **GitHub Actions artifacts**, not GitHub Releases:
  [the preview run](https://github.com/MasynNay/anything-plays/actions/runs/42822217817).
- [x] Each first preview provides checksum receipts and isolates installer
  identities and settings from stable 3.0.


## Four-platform full-library QA milestone: PASS (not a stable release)

All four isolated QA installers have passed native library identity checks
and packaging. Each contains the original 11 source-built emulator families
used by the publicly released 3.0.0 package, preserving the 18-console map,
alongside the 3.1 controller-enabled preview application. The input packages
and compiled cores are checked against their recorded SHA-256 values.

| System | Full 18-console QA run | Result |
| --- | --- | --- |
| Linux x64 | [42842903097](https://github.com/MasynNay/anything-plays/actions/runs/42842903097) | Passed; DEB installed and core hashes checked |
| macOS Apple Silicon | [42843346985](https://github.com/MasynNay/anything-plays/actions/runs/42843346985) | Passed; re-signed QA app and DMG contents verified |
| macOS Intel | [42843346985](https://github.com/MasynNay/anything-plays/actions/runs/42843346985) | Passed; re-signed QA app and DMG contents verified |
| Windows x64 | [42847847307](https://github.com/MasynNay/anything-plays/actions/runs/42847847307) | Passed; real Inno Setup install plus native DLL check in isolated process |

These are **Preview 2 QA binaries**, assembled from the exact published 3.0
native payload and frozen 3.1 Preview 1. They may still display "Preview 1"
inside the application; they are not an independently rebuilt 3.1.0 stable
release. They are retained as temporary Actions artifacts for 7 days.
[How to obtain and test them](V3_1_QA_DOWNLOADS.md).

The remaining stable release gates (physical controller hardware,
corresponding source for new SDL runtime, final native gameplay acceptance,
final reproducible installer builds, and exact release notes) remain open.
A green CI check does not replace those responsibilities.

## Latest development candidate: updated 3.1 controller application

The prior full-library QA packages used the old 3.1 Preview 1. A newer
[successful four-platform preview build](https://github.com/MasynNay/anything-plays/actions/runs/42853582632),
pinned to `d176ff54de90a3cc5e585c6fc6ffd4f68388c104`, includes the
live physical button tester, focus-safe readout, and instant controller
release on Rescan. Three full-library workflows now assemble 18-profile
test packages with that application and the same independently verified
source-built public 3.0 native cores.

These new workflows also attach an
[SDL native/notice evidence report](V3_1_SDL_RUNTIME_AUDIT.md).
The initial audit revealed that the packaged pygame-ce wheel inventory
exposes **no license files**. The QA assembly now copies a verbatim LGPL 2.1
document from pygame-ce's pinned upstream 2.5.8 source tag and rejects
any incorrect document SHA-256. It records the wheel-license omission
rather than disguising it. This adds inspectable compliance evidence,
but leaves the broader LGPL native linkage/relinking/source gate **open**.

**Updated full-console QA packages: PASS on all four targets.** Exact successful
runs for the newer controller application and pinned SDL license inventory:

| Target | Verified workflow | Outcome |
| --- | --- | --- |
| Linux x64 | [42856511632](https://github.com/MasynNay/anything-plays/actions/runs/42856511632) | Passed installed DEB and frozen SDL notice audit |
| Windows x64 | [42857106220](https://github.com/MasynNay/anything-plays/actions/runs/42857106220) | Passed installed Inno Setup, native runtime, and notice audit |
| macOS Apple Silicon | [42856511639](https://github.com/MasynNay/anything-plays/actions/runs/42856511639) | Passed signed final DMG and frozen SDL audit |
| macOS Intel | [42856511639](https://github.com/MasynNay/anything-plays/actions/runs/42856511639) | Passed signed final DMG and frozen SDL audit |

All four QA artifact ZIPs contain an installer, full-console SHA-256
receipt and `SDL_RUNTIME_AUDIT.json`, retained until roughly November 17,
2026. The application source receipt is pinned to
`d176ff54de90a3cc5e585c6fc6ffd4f68388c104`. The pinned
LGPL attribution document uses LF line endings on all targets, preserving
upstream bytes. [Latest successful source test run
42857231009](https://github.com/MasynNay/anything-plays/actions/runs/42857231009)
covers Python 3.12/3.13 and all new audit regression tests.

**This passes updated full-library QA packaging only, not the stable
3.1.0 release gate.** Physical device acceptance, actual gameplay and
endurance on the new artifacts, full LGPL native dependency/source/relinking
review, and a new genuine stable-identity installer rebuild remain open.
Stable public 3.0.0 is unchanged.

## New source-built 3.1 RC1 application and full-library QA lane

Unlike the frozen Preview 1 application used in earlier 3.1 QA packages,
the [new RC1 source-app workflow](https://github.com/MasynNay/anything-plays/actions/runs/42863846059)
builds fresh 3.1 executables on each native host with reviewed RC1
window titles, app identifiers, own settings namespaces and installer IDs.
The first source-built stage contains only mGBA and **is not** a full
release candidate.

The [full RC1 QA workflow](../.github/workflows/v31-full-rc1-qa.yml)
combines those precisely hashed applications with the independently
verified eleven original-source emulator binaries from public 3.0.0.
It revalidates the resulting installed full packages, original core
manifest and SDL runtime. Its [four-platform QA run 42865608433](https://github.com/MasynNay/anything-plays/actions/runs/42865608433)
**PASSED all four hosts** and retained the complete installable RC1 QA
artifacts, original native-library integrity receipts, and SDL audit
manifests. This closes the source-built, full-console **candidate packaging
milestone only**. It cannot publish a GitHub Release, and is not a
license/physical hardware acceptance or a final stable-identity build.
See the [RC1 source-build runbook](V3_1_RC_SOURCE_BUILD.md)
and [latest owner QA downloads](V3_1_RC_QA_DOWNLOADS.md).

## New pygame-ce source and macOS linkage evidence — technical checks PASS

The
[SDL upstream source review 42874882808](https://github.com/MasynNay/anything-plays/actions/runs/42874882808)
has successfully preserved the precise pygame-ce 2.5.8 tagged source
commit, verified its official 3.13 release wheel SHA-256 hashes and
compared all four installed full RC1 native-library audit reports. The
exact audited native file sets match wheel bytes on Linux (74) and
Windows (62). Both Mac architectures still have zero exact original
wheel-byte matches, including universal2 single-architecture slices.

The
[macOS signed-native inspection 42875616776](https://github.com/MasynNay/anything-plays/actions/runs/42875616776)
then independently verified the 121 Apple Silicon and 120 Intel
packaged native hashes and obtained their actual `otool`, `lipo`
and `codesign` evidence. All 241 examined Mac files are
architecture-specific and report ad hoc signatures. The matching SDL2
dylibs have Mach-O `current version 3201.10.0`.
This **documents** signing and architecture transformations but does
not yet prove wheel-to-installed source correspondence or LGPL
replacement compliance.

The source and dependency review ZIPs are temporary 14-day GitHub
Actions artifacts, available through approximately November 24, 2026.
[Review details](V3_1_SDL_SOURCE_REVIEW.md).

**Licensing/relinking and corresponding-source release gates remain
OPEN.** The upstream pygame-ce source tree by itself does not prove
that every packaged SDL2, image, mixer, TTF and transitive dependency
is covered by the correct original-source inputs and notices.

## New completed candidate acceptance checks — November 10, 2026

The four-platform
[installed frozen RC1 graphical startup run 42880420023](https://github.com/MasynNay/anything-plays/actions/runs/42880420023)
**PASSED all 4 native operating systems**. The actual full 18-console
Linux DEB, Windows Setup and both signed Mac DMGs were installed or
mounted on clean hosted runners, and their embedded executable
initialized the real Tk window and application, ran a GUI event-loop
interval, and exited with an independently authenticated receipt.
All installer hashes, pinned 3.1 RC1 app identities, eleven original
emulator cores and 18 profiles were verified before granting this
limited startup result.

[Installed RC1 UI acceptance runbook](V3_1_INSTALLED_UI_QA.md).
Actual physical controllers, webcams, retail games, saves, graphics,
sound and long-duration sessions are **not** established by startup
alone, and those release gates remain open.

A separate
[macOS signed SDL2 collision audit 42879312220](https://github.com/MasynNay/anything-plays/actions/runs/42879312220)
found two distinct bundled SDL2 builds with the same basename on
Apple Silicon, representing Mach-O current versions `3201.8.0`
and `3201.10.0`; Intel had no equivalent conflicting basename
in its audited native files. This is a potential loader ambiguity, not a verified failure.
The
[native dylib loading test 42881412802](https://github.com/MasynNay/anything-plays/actions/runs/42881412802)
subsequently **PASSED both Macs**: Apple Silicon successfully loaded the
actual signed SDL2 versions 2.32.8 and 2.32.10 in **both orders** and
confirmed their runtime versions; Intel's 2.32.10 library also loaded.
The `ctypes` evidence now also includes a separate
[hardware-free SDL joystick/controller subsystem initialization test
42882184466](https://github.com/MasynNay/anything-plays/actions/runs/42882184466)
which **PASSED both macOS architectures**: the actual signed SDL2
2.32.8 and SDL2 2.32.10 variants initialized joystick and
gamecontroller support in both load orders on ARM64, and the Intel
pygame SDL2 version did the same. This does **not** replace a
simultaneous real camera and USB/Bluetooth controller integration
test, or close LGPL and original-source requirements.

The
[original SDL2 source-candidate run 42879614179](https://github.com/MasynNay/anything-plays/actions/runs/42879614179)
also **PASSED**, providing authenticated Git-tag source archives for
SDL2 2.32.8 and 2.32.10, SDL2_image 2.8.12,
SDL2_mixer 2.8.2 and SDL2_ttf 2.24.0. These are
source **candidates**, not yet proven exact binary-to-source
correspondence, complete LGPL license materials or legal approval.
[Native SDL source review](V3_1_SDL_SOURCE_REVIEW.md).

## What is still required before a full 3.1 stable release

- [x] **Build full-library QA candidates:** all 18 profiles with the exact
  eleven native source-built cores from published 3.0, including Dolphin,
  their core manifests and licenses, verified on all four OS targets.
  **This closes packaging parity for QA only, not final stable approval.**
- [ ] **Final 3.1.0 stable rebuild and gameplay verification:** turn the
  verified source-built QA installers into true 3.1.0 native builds, confirm
  stable title and install identity, and exercise N64/GameCube game switching,
  save/reload, real native audio/video, and long-session behavior across all
  supported targets. Full-library QA package hashes are passed, but final
  stable identity and real-game end-to-end acceptance are not.
- [ ] **Actual controller testing:** at least one real USB or Bluetooth
  SDL-compatible gamepad on accessible hardware; test recognition,
  remapping, disconnect/reconnect, focus loss, startup/shutdown and
  keyboard/camera coexistence. Simulated devices prove logic, not HID drivers.
- [ ] **SDL/pygame-ce distribution review:** review LGPL-2.1-or-later
  notices, native wheel/SDL contents, original-source access, and
  applicable dynamic-library replacement/relinking obligations.
- [ ] **3.1 corresponding-source package:** preserve third-party emulator
  sources and newly bundled runtime source/attribution alongside release
  artifacts. Reusing a 3.0 source zip cannot by itself establish that new
  3.1 runtime components are covered.
- [ ] **Final release QA and documentation:** verify the actual four
  stable 3.1.0 installer hashes and update release notes, website, README,
  and post-release support/rollback instructions.

## Release constraints

The test artifacts are only valid for development and may expire. The current
public [3.0.0 release](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0)
has full offline console functionality; it must not be replaced by mGBA-only
3.1 Preview 1. **Neither a CI green check nor a GitHub draft PR is proof that
the untested physical controller or redistribution requirements are satisfied.**

The four-platform full-library packaging milestone is now complete.
The next steps are a final source-built **stable-identity** candidate,
real-game/physical-controller acceptance, and SDL/pygame-ce redistribution
review before any public stable release.
