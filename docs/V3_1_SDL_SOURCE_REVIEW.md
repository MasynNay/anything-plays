# Anything Plays 3.1 — SDL/pygame source correspondence investigation

**Status: PARTIAL TECHNICAL EVIDENCE, NOT APPROVED FOR REDISTRIBUTION.**
Stable public 3.0.0 and the draft-only 3.1 RC1 candidate are unchanged.

## Verified pygame-ce source evidence

The [successful 3.1 SDL source-review run
42874882808](https://github.com/MasynNay/anything-plays/actions/runs/42874882808)
consumes **all four** real installed-package `SDL_RUNTIME_AUDIT.json`
reports and full installer receipts from the
[successful 18-console RC1 QA build
42865608433](https://github.com/MasynNay/anything-plays/actions/runs/42865608433).
The inputs are pinned to the current-source application revision
`86baa6972ed923540f6ab49b636652a0f499d45c`.

It then verifies and retains a complete archive of the **official
pygame-ce 2.5.8 Git tag**, immutable commit
`c8200a9eaa530f884a0a4c3384cefc48006e58be`, and exact LGPL notice
SHA-256
`a190dc9c8043755d90f8b0a75fa66b9e42d4af4c980bf5ddc633f0124db3cee7`.

The review also checks official pygame-ce 2.5.8 CPython 3.13 release
wheels against their **upstream-published SHA-256 digests**:

| Wheel target | Published upstream SHA-256 |
| --- | --- |
| Linux x64 (manylinux2014) | `5bb966b610e161a8f6d908b4c62ef3a1f3e922bc7bed73bd70a3e15dc780b90e` |
| Windows x64 | `f495b0eb7a5c54c59da58e964bc7f68073c3f43cf307729fd48309104a04c190` |
| macOS universal2 (both architectures) | `56441a9bb75c2461750dc0e6e4a46e3833b3cf6339bfbaf16f93ecac037510f3` |

The published package is
[pygame-ce release 2.5.8](https://github.com/pygame-community/pygame-ce/releases/tag/2.5.8).
These official upstream wheel digests are **not in themselves proof**
that each specific wheel produced every installed library.

## Actual frozen-native comparison

`tools/prepare_v31_sdl_source_review.py` hashes compiled pygame and
SDL library candidates inside each complete RC1 installation, then
compares those records against the actual bytes in the independently
hashed release wheels. Universal macOS wheel files also have both
ARM and Intel Mach-O architecture slices compared byte for byte,
without stripping signatures, editing native code or falsely labelling
a rebuilt binary an exact match.

| System | Exact full-file or Mach-O slice matches | Unmatched native candidates |
| --- | ---: | ---: |
| Linux x64 | 74 | 0 |
| Windows x64 | 62 | 0 |
| macOS Apple Silicon | 0 | 121 |
| macOS Intel | 0 | 120 |

These counts apply only to **the audited pygame/SDL candidate set**,
not all native dependencies in the application or complete corresponding
source material. A file-by-file audit is archived.

Linux and Windows now have useful byte-level wheel matching evidence.
Both macOS architectures remain **unmatched even after trying
universal2 architecture slices**. The installed Mac packages include
`libSDL2-2.0.0.dylib`, SDL2 image, mixer and TTF libraries, and
pygame-linked native libraries. Possible packaging transformations
such as signing, architecture thinning or relocations must be
**demonstrated** before treating these as official-wheel matches.

## New separate Mac native-linkage inspection

The read-only
[macOS native dependency workflow](../.github/workflows/v31-macos-native-linkage-review.yml)
examines the actual already-verified RC1 Mac DMGs on native Apple
Silicon and Intel runners. It compares every dylib to its immutable
installed-package audit hash and records:

- `otool -L` dependencies and library compatibility/current versions
- `lipo -archs` CPU architecture metadata
- `codesign -dv` signing information on each library

The [macOS signed-native review run 42875616776](https://github.com/MasynNay/anything-plays/actions/runs/42875616776)
**PASSED on both architectures**. Its actual mounted-DMG reports give
these concrete facts:

| Measurement | Apple Silicon | Intel Mac |
| --- | ---: | ---: |
| Native SDL/pygame candidates independently re-hashed | 121 | 120 |
| Successful `otool -L` inspections | 121 | 120 |
| Files reporting `Signature=adhoc` | 121 | 120 |
| Files reporting only the target architecture via `lipo` | 121 ARM64 | 120 x86_64 |

The main `libSDL2-2.0.0.dylib` records the same Mach-O
`current version 3201.10.0` in both native builds. This is an
**observed dylib version string**, not by itself a certified upstream
source tag. Other linked libraries include SDL2 image, mixer, TTF,
FLAC, Ogg, JPEG, PNG, TIFF and WebP components; the full version,
dylib path and signature evidence is in the two JSON artifacts.

These results demonstrate architecture-specific, ad hoc signed
compiled libraries in the installed RC packages. **They do not yet
prove** that signing/thinning is the only difference from the published
universal2 wheel bytes; the original wheel-to-final-transformation
must still be independently established. No Mac source correspondence
or LGPL replacement permission was declared complete.

Open the successful run's **Artifacts** section for
`AnythingPlays-3.1-RC1-MACOS-arm64-SDL-LINKAGE-REVIEW-UNAPPROVED`
and
`AnythingPlays-3.1-RC1-MACOS-x64-SDL-LINKAGE-REVIEW-UNAPPROVED`.
These JSON evidence archives are available for about **14 days**,
through November 24, 2026, not public stable releases.

## Apple Silicon duplicate SDL2 loader identity confirmed

A new read-only
[SDL loader collision review 42879312220](https://github.com/MasynNay/anything-plays/actions/runs/42879312220)
**passed** its source/receipt safety tests and read both real signed
native-lib inspection artifacts. It detected one potentially ambiguous
SDL2 basename on Apple Silicon:

| Actual installed library | Mach-O current version |
| --- | --- |
| `Contents/Frameworks/cv2/__dot__dylibs/libSDL2-2.0.0.dylib` | `3201.8.0` |
| `Contents/Frameworks/pygame/__dot__dylibs/libSDL2-2.0.0.dylib` | `3201.10.0` |

Additional same-named SDL2 paths in the ARM package share the pygame
variant's exact hash. The Intel package showed **no conflicting SDL2
basename hashes** among its audited files. The project now has a
machine-readable `SDL_LIBRARY_COLLISIONS.json` report, stored for 14
days. Different libraries of the same basename can potentially be
resolved through different `@rpath` settings. This needs actual
loader and simultaneous camera/controller behavioral testing; it is
**not proof of a crash, regression or exploitable vulnerability**.

## Native dynamic-loader coexistence probe: PASSED on both Mac architectures

The
[actual signed SDL2 dynamic-loader run 42881412802](https://github.com/MasynNay/anything-plays/actions/runs/42881412802)
**PASSED** on Apple Silicon and Intel Mac. It used the original
read-only mounted 18-console RC1 DMGs and independently authenticated
signed dylib bytes against the previous immutable native-linkage reports,
then called SDL's real `SDL_GetVersion` through `ctypes.CDLL` on
the host's architecture.

On Apple Silicon the two audited SDL2 libraries reported their
expected versions, **2.32.8 and 2.32.10**, when loaded in
**both orders** in a single native process. On Intel, the signed
pygame SDL2 dylib successfully loaded and reported **2.32.10**.
The subprocess tests check for a mismatched version returned because
of potential dyld library coalescing. The result receipts
`SDL_DYLD_LOAD_arm64.json` and `SDL_DYLD_LOAD_x64.json`
are retained for 14 days.

This establishes successful direct native loading of both signed
libraries from the actual mounted candidate, **not** that OpenCV and
pygame's full camera/controller subsystems have been exercised together,
nor that all possible `@rpath` resolution scenarios in the compiled app
are safe. It does not establish corresponding-source or LGPL rights.

## Deeper hardware-free joystick/controller backend initialization

The existing signed native-loader workflow was extended to call
`SDL_InitSubSystem(SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER)` and
`SDL_NumJoysticks` against the actual 3.1 RC1 SDL libraries. It
checks the returned runtime SDL version and successful initialization,
then releases the subsystems. This tests SDL controller backend
initialization without claiming a physical gamepad exists.

[Extended native joystick/controller run 42882184466](https://github.com/MasynNay/anything-plays/actions/runs/42882184466)
has **PASSED Apple Silicon**: both SDL2 2.32.8 and SDL2 2.32.10
initialize those subsystems successfully in either library loading
order. The Intel Mac job was **queued as of the last verification**;
check the Actions job conclusion before claiming both are green.

The full GUI startup and physical device acceptance are **separate**:
a passing backend initialization in CI still does not prove an actual
USB/Bluetooth controller works concurrently with an active camera.
Source correspondence and LGPL rights are also still open.

## Five original SDL source trees preserved for comparison

The
[SDL2 pinned upstream source workflow 42879614179](https://github.com/MasynNay/anything-plays/actions/runs/42879614179)
**passed** and published one temporary, checksummed, original-source
candidate archive containing these exact Git-tag commit trees:

| Upstream candidate | Exact Git commit |
| --- | --- |
| SDL2 2.32.8 (observed in ARM OpenCV dependency) | `98d1f3a45aae568ccd6ed5fec179330f47d4d356` |
| SDL2 2.32.10 (observed in pygame dependency) | `5d249570393f7a37e037abf22cd6012a4cc56a71` |
| SDL2_image 2.8.12 | `12cb2e40330d256d9b1329647be8f366546d715c` |
| SDL2_mixer 2.8.2 | `b208916aed9250fe434360e6c6a95f0697bb7b01` |
| SDL2_ttf 2.24.0 (filename suggests version; Mach-O reports 0.0.0) | `2a891473eaf05ba1707a4b7913e6c4db7de7458a` |

The archive includes `SDL_CANDIDATE_SOURCE_MANIFEST.json` and
`SDL_SOURCE_SHA256SUMS.txt`; every component was fetched by tag and
verified against the pinned exact commit, its archived file structure
and SHA-256 digest. Find it in the run's **Artifacts** section as
`AnythingPlays-3.1-RC1-SDL2-CANDIDATE-SOURCES-UNAPPROVED`, retained
through approximately **November 24, 2026**.

These are *specific possible upstream source references*, based on
observed Mach-O library versions and names. They are **not yet proof**
that the final compiled dylibs were built from these precise checkouts,
nor a complete source and relinking companion for the static/dynamic
dependencies.

## How to obtain source-review artifacts

Open
[SDL source evidence run 42874882808](https://github.com/MasynNay/anything-plays/actions/runs/42874882808),
scroll to **Artifacts**, and download:

`AnythingPlays-3.1-RC1-SDL-UPSTREAM-SOURCE-REVIEW-UNAPPROVED`

This temporary ZIP is retained through roughly **November 24, 2026**.
Its contents are the pinned tagged pygame-ce source TAR.GZ,
`SDL_SOURCE_REVIEW.json` and `SHA256SUMS.txt`.
Run `sha256sum --check SHA256SUMS.txt` after extracting.

There are **no commercial games or ROMs** in this source record.

## Gates that remain OPEN

This archive is not yet a complete corresponding-source companion.
The pygame-ce source tag does not by itself identify the exact
third-party SDL2/SDL2_image/SDL2_mixer/SDL2_ttf build inputs or every
wheel's compiler options and patches. Some transitive native libraries
may require their own attribution and sources.

Before a public stable release, complete the native-library
correspondence assessment, document any LGPL source-access and
end-user replacement/relinking obligations applicable to the shipped
layout, complete real-device USB/Bluetooth/controller and game-save
acceptance, and separately build approved stable 3.1.0 installers.
All present evidence reports deliberately set
`redistribution_approved: false`, and the
[release gate](../tools/check_v31_release.py) remains blocked.

The development work is tracked in
[draft PR #156](https://github.com/MasynNay/anything-plays/pull/156)
and [release acceptance](V3_1_RELEASE_ACCEPTANCE.md).
