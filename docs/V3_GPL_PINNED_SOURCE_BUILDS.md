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

## Verified Linux source-build milestone — original artifacts rehashed

[PR #79](https://github.com/MasynNay/anything-plays/pull/79) **merged**
on November 8, 2026 UTC after
[full source regression 42459386203](https://github.com/MasynNay/anything-plays/actions/runs/42459386203)
**SUCCESS** (Python 3.12/3.13 + native mGBA), and the
[actual two-source Linux build and homebrew run 42459386197](https://github.com/MasynNay/anything-plays/actions/runs/42459386197)
**SUCCESS 2/2** from the exact reviewed PR head
`e6cbe271dd15226e3cd17ae21e6fdb48169d38e8`.

Unlike the first mutable buildbot alternatives, these are **freshly
compiled from their own exact pinned upstream repositories** with their
matching original complete Git source TARs and GPLv3 notices retained in
authenticated test-only GitHub Actions artifacts. Both zipped artifacts
were downloaded and independently SHA-256 verified **for every original
checksum entry and both native/source hash fields**.

| Exact Linux source-built candidate | Native .so size (bytes) | Original native SHA-256 | Original source TAR SHA-256 |
| --- | ---: | --- | --- |
| bsnes, source commit `63ee22f7...` | 2,645,656 | `9a851d8d2af077dd2348f51e5c9959430482034de6e0767ddae2fe75e74bf98b` | `592c32955435153a221400faf15b70cf7881dc3fe84f09158b29da2458e816e7` |
| BlastEm, source commit `2230addc...` | 12,983,672 | `a9a6c104c29f7b1c0725bbe8b6d0bbf06f8b5f50d74e12b456861b7a98277fa3` | `208b420abe72708e2e9f3dbd81a996e19c48b81a9d687f4f514b8fe22e48d868` |

Actual source archive sizes: bsnes **4,149,913 bytes**,
BlastEm **2,101,747 bytes**. Actual native source research
Artifacts: `13608134617` (bsnes) and `13609406024` (BlastEm).
Each contains original source `tar.gz`, native Linux `.so`,
original GPL notice, full manifest, `SHA256SUMS.txt` and its
native audio/video reports (plus diagnostic screenshots).

Native original homebrew results in those exact authenticated artifacts:
**SNES** original PPU/SPC pass using new bsnes; **Genesis** original
source-authored *no-unconditional-TMSS* variant, **Master System**,
**Game Gear**, and **SG-1000** each pass real nonblank/changing video,
nonzero audio, and child exit 0 using new BlastEm. As documented above,
the *unmodified* Genesis startup on hardware without TMSS fails, and
that is neither concealed nor asserted to pass.

**This does not make stable 3.0 publishable:** the original preview still
uses unmodified Snes9x and Genesis Plus GX; newly compiled versions are
research alternatives. This study covers Linux only and cannot prove
their Windows/macOS builds or actual user ROM/save/peripheral compatibility.
No independent complete build-chain/source reproduction or combined
GPLv2-only and GPLv3 distribution rights determination has been issued.
All source/rights/public release/physical QA boolean approvals stay FALSE.
