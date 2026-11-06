# Anything Plays v2.0.0 · release candidate

Anything Plays turns real-world movement into game controls. Version 2.0 expands
from its original Game Boy Advance experience to four classic consoles and adds
independent layouts, a more expressive ROM shelf, and improved desktop builds.

## Highlights

- Game Boy, Game Boy Color, Game Boy Advance, and Super Nintendo support
- Gambatte, mGBA, and Snes9x core selection based on the chosen system
- Independent profiles, button mappings, and ROM folders per console
- Even control grids, optional button disabling, custom drawing, and Shuffle
- Sixteen application themes and console-specific cartridge artwork
- Camera tracking, manual keyboard play, game audio, and battery-backed saves
- Refactored application architecture and expanded automated regression coverage
- Per-build SHA-256 provenance manifest for downloaded Libretro cores

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

Complete the real-device and installer testing in `QA_CHECKLIST.md`, verify the
new refactor on each supported platform, and resolve the exact third-party
copyright, license, and corresponding-source obligations in
`THIRD_PARTY_COMPONENTS.md`. **The source package is not yet an authorized
public v2.0 installer release.**
