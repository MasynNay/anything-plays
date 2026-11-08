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

### Reproducing the exact macOS compatibility change

The first untouched upstream macOS source builds correctly **failed**
because `mednafen/config.h` defined `HAVE_SEM_TIMEDWAIT` for Darwin,
although the Apple SDK has no `sem_timedwait`. The same upstream
`mednafen/mthreading/MThreading_POSIX.cpp` already implements a
pthread-condition-variable-backed semaphore fallback.

`tools/patch_v30_supafaust_macos_semaphore.py` performs exactly this
single-line source modification **only** in the temporary checked-out
Git source for the two Mac builds:

```diff
-#if !defined(__SWITCH__) && !defined(HAVE_LIBNX)
+#if !defined(__SWITCH__) && !defined(HAVE_LIBNX) && !defined(__APPLE__)
```

The script refuses the wrong upstream commit, origin URL, dirty original
tree or unexpected header contents. Before original source/native
preservation, `tools/capture_v30_supafaust_source.py` **independently
compares the entire changed header to the pristine original Git blob with
only that one replacement**, rejects any other changed tracked file,
retains the authentic original source `git archive` **plus** exact
`git diff` as `SUPAFAUST_MACOS_SOURCE_PATCH_UNAPPROVED.diff`,
and adds the patch SHA-256 to its unapproved native/source manifest.
That makes the modified research build reproducible without falsely
claiming that unpatched upstream source built the Mac binary. The patch
is GPL-licensed source research and is **not** legal approval to bundle
that emulator with Anything Plays.

The independent Windows source build also found that native
`Path.write_text()` created CRLF `SHA256SUMS.txt` lines, which GNU
`sha256sum -c` interpreted as \r in filenames. The research capture
writes **byte-exact LF-only checksums** on all platforms now and tests
the actual raw checksum bytes. Neither platform issue is masked or
excluded from the four-platform required native audio/video matrix.

### Completed original four-platform source-built experiment — November 8, 2026

[Original eight-stage research/test workflow run 42494297281](https://github.com/MasynNay/anything-plays/actions/runs/42494297281)
ended **SUCCESS on all four operating system jobs**, source
`ca0e1a1b3ad98ae30402be6c7151b19d5fffac57`, with matching
[Python 3.12, Python 3.13 and native mGBA source checks 42494297280](https://github.com/MasynNay/anything-plays/actions/runs/42494297280)
and [Linux source research 42494297305](https://github.com/MasynNay/anything-plays/actions/runs/42494297305)
also **SUCCESS**. The experiment was merged in
[PR #82](https://github.com/MasynNay/anything-plays/pull/82)
at `41314e3e810e6cbedc8207e80f2a4b88dd7cc4d3`.

The **original actual GitHub Actions research artifacts** were downloaded
and independently rehashed against every SHA256SUMS entry, the native
source/build manifest, actual original SNES homebrew results, and the
retained source-license files. Mac original source and the one-line
modification are archived **separately**, with the patch's own SHA256.

| OS target | Artifact ID | Fresh source-built native SHA256 | Real SNES frames | Nonzero SPC PCM values |
| --- | --- | --- | ---: | ---: |
| Windows x64 | `13623345619` | `c7aecb572dacde989be8fd8014bed9d04794b8090add4277229d5c7541f9bdbe` | 718 | 131,888 |
| Linux x64 | `13623230854` | `4345cfa1bcf805b9e47dd533d8e2a8344c6517ed55e35db6eb350aba3b396599` | 720 | 131,888 |
| macOS ARM64 | `13622424690` | `2a398a74f0294187bf7bc1394b3d0cfb91db2f9827abb210135eb16312fc6d95` | 721 | 131,888 |
| macOS Intel | `13622777341` | `7a85c00751b338c9770398eaf0890a42e6db796b172f09c4e9aa29a848ec7506` | 722 | 131,888 |

All four source archives identify the **same original upstream Git commit**,
`642d1d1b6684aa7e306a02a89885f3f5456a5157`, and contain the
same 138 original Git files. Original Windows `git archive` stores
CRLF-transformed text files; its source TAR SHA
`db60b1c7a1ffd8f6a7d435a8d0d8ad9641131a444bfd0cd64688c9bf3ad3f544`
differs from the Unix/macOS source archive SHA
`c8ef200e50d562bf4ac6b7c9a242beab0491e68d423d473f321f28a59ecb10d5`.
**This is not a different source revision:** all 138 source file payloads
were independently compared after normalizing only CRLF/LF differences
and matched, including original root GPL2 license and source-level GPL2+
permission. Windows had 137 files differing in raw line-ending bytes.
All original per-platform archive digests remain correctly recorded,
not forcibly overwritten with a guessed cross-platform common digest.

The two Mac research outputs each include the **same exact one-line
source compatibility patch**:
`940e9377949c4bb7bdc015278d358a6a793408f043b5c88f069f6c1f92c7f4f6`.
The actual upstream original source archive remains preserved separately.

**Research passed does not mean approved shipment.** All candidates
continue to carry `public_binary_redistribution_approved=false`,
`replaces_current_snes9x_in_app=false`,
`complete_combined_core_license_reviewed=false`, and
`real_4_os_hardware_gameplay_approved=false`. Next technical tests would
need application integration, real-controller and camera input, multiple
ROM changes, real game saves, performance and physical endurance before
considering a shipping replacement. The legal compatibility of the
complete combined GPL/noncommercial application and full native sources
still requires qualified independent review.

