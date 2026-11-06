# Anything Plays v2.0.0 · release candidate

Anything Plays turns real-world movement into game controls. Version 2.0 expands
from its original Game Boy Advance experience to four classic consoles and adds
independent layouts, a more expressive ROM shelf, and improved desktop builds.

## Highlights

- Game Boy, Game Boy Color, Game Boy Advance, and Super Nintendo support
- mGBA for GB, GBC and GBA; Snes9x for SNES
- Independent profiles, button mappings, and ROM folders per console
- Even control grids, optional button disabling, custom drawing, and Shuffle
- Sixteen application themes and console-specific cartridge artwork
- Camera tracking, manual keyboard play, game audio, and battery-backed saves
- Refactored application architecture and expanded automated regression coverage
- Per-build SHA-256 provenance manifest for downloaded Libretro cores
- Removed Gambatte from the planned public installer to avoid GPLv2/noncommercial combination

## Planned downloads

| Platform | Planned installer |
| :-- | :-- |
| Windows x64 | `AnythingPlaysSetup-2.0.0.exe` |
| macOS Apple Silicon | `AnythingPlays-2.0.0-macos-arm64.dmg` |
| macOS Intel | `AnythingPlays-2.0.0-macos-x86_64.dmg` |
| Ubuntu/Debian x64 | `anything-plays_2.0.0_amd64.deb` |

All files and their final names must be verified before public release. These
names are **not a claim that new installers have already been published**.

## Installation and usage

Windows installers are unsigned and may trigger SmartScreen. macOS builds use
ad-hoc signing rather than Apple Developer ID notarization; Gatekeeper may
require explicit approval. No commercial ROMs or BIOS files are included.

Anything Plays is intended to be distributed completely free, without ads,
donations or other monetization. Third-party cores retain their independent
licenses and conditions, including Snes9x's non-commercial restrictions.

## Before publishing

The maintainer completed functional testing of Windows EXE, macOS DMG and
Linux DEB installers and confirmed the v2.0 application works on all three.
Those earlier builds used Gambatte for GB/GBC. On the revised mGBA integration,
a real native Linux core passed generated GB/GBC ROM loading and video checks.
Compatibility with existing GB/GBC save files and representative games still
requires separate verification before public binary distribution.
The remaining **public binary release** gates are third-party licensing
compatibility, corresponding-source materials, immutable binary provenance,
and confirmation of the updated installer notice packaging where applicable.
See `RELEASE_LICENSE_REVIEW.md`. **A source merge into `main` is not approval
to redistribute the bundled binaries.**
