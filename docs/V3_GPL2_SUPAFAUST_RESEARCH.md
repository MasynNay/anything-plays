# 3.0 — GPLv2-or-later SNES replacement feasibility

**Status: source-built research only. No emulator switch, approval, public
3.0 distribution or physical hardware test is implied.**

The working 3.0 preview uses `snes9x` for SNES. That native core has a
noncommercial license, which complicates public redistribution alongside
GPL-family emulators. Earlier candidate [bsnes](V3_GPL_PINNED_SOURCE_BUILDS.md)
is licensed **GPL version 3 only**. Its successful native tests do not
solve possible GPLv2-only/GPLv3 combining conflicts.

Another candidate is
[Beetle Supafaust](https://docs.libretro.com/library/mednafen_supafaust/),
which Libretro reports as **GPLv2-or-later**. Unlike the license summary
alone, its actual original upstream source explicitly grants **GPL version 2
or any later version** in
`mednafen/snes_faust/snes.cpp`. Its root `COPYING` supplies the
original GPL version 2 license text.

## Pinned original source

- Repository:
  [libretro/supafaust](https://github.com/libretro/supafaust)
- Immutable source commit:
  `642d1d1b6684aa7e306a02a89885f3f5456a5157`
- Original license: `COPYING` (GPL version 2)
- Original source-level grant:
  `mednafen/snes_faust/snes.cpp`, GPL version 2 **or later**
- Expected compiled Linux core:
  `mednafen_supafaust_libretro.so`

This source tree contains no Gitlink submodules at that revision. The
`.github/workflows/v30-supafaust-gpl2-source.yml` GitHub Actions lab
checks out **that exact commit**, recompiles its own native ELF from
source with `make platform=unix`, and runs the app's original SNES
PPU animated-image and SPC sound homebrew via the same Libretro frontend
used by the desktop program.

`tools/capture_v30_supafaust_source.py` captures the actual newly
compiled ELF, its checksum and byte size, the matching **full original Git
source archive**, the original GPL notice and a SHA256SUMS record. It
checks the immutable checkout revision, source repo URL, unchanged tracked
files, Linux ELF header, exact expected filename, source-level GPL
permission and exact archived `Makefile`/license/source. The output is
saved privately in GitHub Actions research artifacts marked **UNAPPROVED**,
not added to the application or published in a GitHub release.

The source-only regression
`tests/test_v30_supafaust_gpl2_source.py` uses a temporary real Git repo
and tests legitimate native/source hash capture, modified source
rejection, wrong target architecture, output path safety, and the
required false rights/compliance flags.

## Why consider it instead of bsnes?

If the exact effective terms of all other required components permit
distribution under GPLv2, a GPLv2-or-later SNES core may be **more
compatible** than a GPLv3-only one. This is only an engineering/review
option, not a legal determination. Different files may have additional
copyright/redistribution grants. Another GPLv3-only Sega core such as
BlastEm may still create a combined-work incompatibility with GPLv2-only
cores even if Supafaust works.

**Do not switch SNES to Supafaust yet.** Linux source-built native
video/audio passing is only the first stage. The same core must be
source-built and tested on Windows x64, macOS ARM64 and Intel Mac, preserve
SNES saves, gamepad/camera controls and ROM switching, and pass sustained
real installed-game compatibility testing. Independent corresponding
source and legally reviewed combined-program distribution decisions remain
mandatory. See [release blocker #28](https://github.com/MasynNay/anything-plays/issues/28).

## Four-platform source-built follow-up (separate research gate)

The second independent research lab,
`.github/workflows/v30-supafaust-four-os-source.yml`, runs **four**
freshly compiled, immutable upstream native candidates from the SAME
GPLv2-or-later source commit on different actual operating systems:

| Native target | Real GitHub runner | Expected original core |
| --- | --- | --- |
| Windows x64 | `windows-2025` with MSYS2 MINGW64 | `mednafen_supafaust_libretro.dll` |
| Linux x64 | `ubuntu-24.04` | `mednafen_supafaust_libretro.so` |
| Apple Silicon | `macos-15` | `mednafen_supafaust_libretro.dylib` |
| Intel Mac | `macos-15-intel` | `mednafen_supafaust_libretro.dylib` |

The `capture_v30_supafaust_source` utility now validates native file
name **and platform-specific PE/ELF/Mach-O header**, immutable Git source
commit, unchanged upstream tracked source, exact original GPL license
text/grant and archive hash. It records the actual new native bytes and
an original source snapshot for *each OS*, with distinct architecture
metadata and all public distribution and substitution approvals FALSE.
The source-only regression uses each OS binary signature plus a real
source archive and SHA256SUMS; the actual workflow requires authentic
moving SNES PPU video and nonzero SPC audio in the same Libretro frontend
on the runner, not just that a library was built.

This cross-platform lab may require compiler compatibility fixes on
modern Apple and MSYS2 runners. Such fixes must not silently alter
upstream GPL source, suppress a failing platform, skip playback or
relabel research-only binaries as approved shipping emulator cores.
Passing the lab is **not** evidence of real keyboard/camera/save, physical
speaker, retail game compatibility, or the legal compatibility of the
entire combined 11-core 3.0 installer. Research only.
