# Anything Plays 3.0 — exact pinned GPL alternative source builds (research)

**Status: UNAPPROVED. No public 3.0 core replacement, binary redistribution
decision, or complete source/license compatibility conclusion.**

The existing 3.0 desktop app runs **18 profiles using 11 bundled Libretro
core families**. Two current native cores are under a noncommercial source
license (Snes9x and Genesis Plus GX). A candidate alternative is to build
the GPLv3 **bsnes** SNES core and GPLv3 **BlastEm** core covering Genesis,
Master System, Game Gear and SG-1000. The research must preserve all five
existing console profiles and must never download emulators at first run.

## Frozen upstream sources

| Candidate | Exact source repository | Immutable source commit | Original root license |
| --- | --- | --- | --- |
| bsnes | `libretro/bsnes` | `63ee22f7af8f5d1ada295c2c98fd7bf261fa62a7` | `LICENSE.txt`, GPL version 3 only |
| BlastEm | `libretro/blastem` | `2230addc4dd74dd094fd264987fd808abba32d0e` | `COPYING`, GPL version 3 |

The exact upstream Git commits were inspected directly, including original
source license files. Both use public Libretro make targets. Source commits
are research inputs, **not** source identities of existing 3.0 nightly
core binaries. The bsnes Git tree showed no Gitlinks at that commit.

The `.github/workflows/v30-gpl-pinned-source-build.yml` research workflow
checks out both pinned upstream revisions, compiles *new* Linux x64 native
libraries from the exact original trees, and creates a bounded source Git
archive plus original GPL notice, freshly compiled native library, JSON
SHA-256 source/native metadata and SHA256SUMS. It runs original
production Libretro frontend native playback:

- bsnes: original source-generated SNES PPU moving video and SPC sound
- BlastEm: original Genesis 68000 PPU/PSG cartridge with only the optional
  TMSS hardware write NOPed, plus independent real Master System, Game Gear
  and SG-1000 audio/video homebrews

That Genesis exception is recorded precisely and must not be mistaken for
unmodified cartridge compatibility or a real-game compatibility guarantee.

**This first lab is Linux research only.** Passing here means the core could
be tested on Windows x64, Mac ARM64 and Mac Intel from pinned source as a
possible later substitution, with actual saves, switching, gamepad/camera,
performance and platform-specific QA. The application core resolver is
**NOT modified** by this research.

## Independent publication blockers remain

An original source archive plus a newly compiled native binary make much
stronger corresponding-source *candidate* evidence than assigning a guessed
Git revision to an old nightly binary. It does **not** establish a
reproducible independent build, complete dependency rights, nor the
compatibility of **GPL version 3 only** bsnes and BlastEm with other
GPLv2-only native cores in a potentially combined in-process Libretro
application. Some core families may require a different architecture,
different legally compatible emulators or copyright-holder permissions.

Before any stable public 3.0 release, a qualified reviewer must establish
actual legal rights for the entire one-installer combined application,
complete corresponding sources of the exact 44 installed native binaries,
Dolphin system asset permissions, and signed-off four-platform physical
gameplay/keyboard/camera/sound/save/endurance tests. Do not set release
approval booleans based on this experimental research. See
[release blocker #28](https://github.com/MasynNay/anything-plays/issues/28)
and [V3 GPL alternatives](V3_GPL_SNES_SEGA_ALTERNATIVES.md).
