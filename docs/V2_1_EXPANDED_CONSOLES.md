# 2.1 expanded built-in console support

The 2.1 alpha extends the original eight consoles with ten more **in-app**
ROM libraries. All are implemented using Libretro native cores included
by the desktop installer builder; there is no external emulator picker or
user-side core-download requirement.

| Console | Internal core | Firmware notes |
| --- | --- | --- |
| Sega Master System | Genesis Plus GX (already bundled) | Regular cartridges only; optional original BIOS not supplied |
| Sega Game Gear | Genesis Plus GX (already bundled) | Regular cartridges only |
| Sega SG-1000 | Genesis Plus GX (already bundled) | `.sg` cartridges |
| Atari 2600 | Stella 2014 | Cartridge games |
| Atari 7800 | ProSystem | Some games require a user-supplied optional BIOS |
| TurboGrafx-16 / PC Engine | Beetle PCE Fast | HuCards only, **not** CD games needing copyrighted system card |
| Neo Geo Pocket and Pocket Color | Beetle NeoPop | Distinct libraries, shared core |
| WonderSwan and WonderSwan Color | Beetle WonderSwan | Distinct libraries, shared core |

**No commercial ROMs or firmware are bundled.** Users supply legally usable
game files. Avoid adding a system that requires BIOS/firmware before verifying
the build's runtime behavior, and do not auto-download copyrighted firmware.

The original Game Boy, Game Boy Color, Game Boy Advance, NES, SNES, Genesis,
N64, and GameCube remain available. GameCube's accelerated in-panel rendering
is still a development blocker.

These ten new system entries are intentionally **not marked as
real-game-verified** in `config/v2.1-release-acceptance.json`.
Release approval requires clean installs, user-facing controls, audio,
save/load behavior, long-running stability, third-party license review,
and in-panel video on all four supported operating-system targets.

### Core updates

`Check updates` must show one entry per **unique native core**, not
one download per console. Master System, Game Gear, SG-1000, and Genesis
share one Genesis Plus GX update; Neo Geo Pocket variants and WonderSwan
variants similarly share their binary. Future independent core updates must
not mutate signed app resources, install unchecked nightly DLLs/dylibs,
or overwrite a library currently loaded by a running game.
