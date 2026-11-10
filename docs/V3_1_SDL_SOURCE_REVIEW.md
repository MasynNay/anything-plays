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

<escape>|</escape> System <escape>|</escape> Exact full-file or Mach-O slice matches <escape>|</escape> Unmatched native candidates <escape>|</escape>
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

It retains unapproved `MACOS_NATIVE_LINKAGE_*.json` review files,
without modifying or re-signing the packages. Those records help
locate the exact mismatched native libraries and may clarify which
upstream SDL2 sources must be preserved.

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
