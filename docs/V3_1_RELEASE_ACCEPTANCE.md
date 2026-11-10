# Anything Plays 3.1 — Release acceptance

**Status: NOT READY FOR A STABLE RELEASE.** This document tracks evidence,
not a promise of a release date. Stable 3.0 stays public and untouched.

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
