# Experimental pinned GPLv3 alternatives on all four host architectures

**UNAPPROVED research only. No actual emulator core replacement or stable
public binary distribution permission is asserted.**

The independently verified Linux originals from
[run 42459386197](https://github.com/MasynNay/anything-plays/actions/runs/42459386197)
prove bsnes and BlastEm can be built from exact pinned source and tested
with original SNES/Sega source-generated video/audio homebrew. To avoid a
false assumption that Linux Libretro compatibility automatically means
working desktop versions, this **separate** workflow now attempts both
pinned GPLv3 candidate cores on **four actual native OS runners**:

| Native target | GitHub host runner | Native output |
| --- | --- | --- |
| Windows x64 | windows-2025 + MSYS2 MINGW64 | `bsnes_libretro.dll`, `blastem_libretro.dll` |
| Linux x64 | ubuntu-24.04 | `bsnes_libretro.so`, `blastem_libretro.so` |
| macOS Apple Silicon | macos-15 ARM64 | `bsnes_libretro.dylib`, `blastem_libretro.dylib` |
| macOS Intel | macos-15-intel x86_64 | `bsnes_libretro.dylib`, `blastem_libretro.dylib` |

New [workflow](../.github/workflows/v30-gpl-four-os-source-build.yml):
`Anything Plays 3.0 | Four-platform pinned GPL candidate research`.
Each of **eight independent jobs** checks out the same immutable official
source revision, builds with the platform-native compiler, rejects wrong
native file identities and missing original GPLv3 notices, archives the
**actual pinned Git source TAR plus newly compiled platform-native binary,
original GPL text, SHA256SUMS and reviewer JSON**, then runs the genuine
Libretro `CoreSession` video/audio homebrew path from the application.

The test conditions are **identical in purpose across hosts**: bsnes
SNES SPC/PPU, and BlastEm Genesis with only original source-generated
optional TMSS register write NOPed, plus Master System/Game Gear/SG-1000
separate original homebrew test cartridges. No games/BIOS from third
parties, no end-user core download, no files merged into the *working*
3.0 app and no public GH release. The per-host core/source archive SHA
values are saved separately so compiler/build differences are not hidden.

**Research failures must remain actual failures**, not converted into
unsupported profiles or falsely marked green. Native input/PCM/video
in CI are stronger than package-only tests, but they are NOT real
physical webcam/speaker/retail game testing.

GPL **version 3 only** may still be incompatible with GPLv2-only code
in a combined, dynamically loaded application. Independently approved
actual legal redistribution permissions, final corresponding sources
for all 44 native cores + Dolphin Sys, production code/asset hashes and
four-platform physical QA remain mandatory even after eight green jobs.

See [GPL source-built research](V3_GPL_PINNED_SOURCE_BUILDS.md) and
[unresolved release blocker #28](https://github.com/MasynNay/anything-plays/issues/28).
