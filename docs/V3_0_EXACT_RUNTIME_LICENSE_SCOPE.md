# Anything Plays 3.0: exact embedded-core interaction and release decision

**Recorded 2026-11-09. Technical evidence, not a legal clearance, not permission to falsely mark an unreviewed production input as reviewed.**

## Verified concrete release state

- Actual four-platform 18-console/11-source-core offline installers were successfully compiled, frozen-GUI-started, video/audio-tested, and retained in GitHub Actions [run 42686588072](https://github.com/MasynNay/anything-plays/actions/runs/42686588072). The project owner additionally tested N64 repeated ROM loading and GameCube on Windows, Linux and Apple Silicon; preserve this evidence without soliciting duplicate user tests.
- Four executables plus checksums and a complete 11-emulator original-source ZIP currently live in **private** GitHub Release draft `v3.0.0-rc.1`, release ID `439693701`. They are visibly marked `alpha.1`. **No public stable `v3.0.0` exists yet.** The repository's public website showcases 3.0, but the public stable download remains v2.0.0.
- The exact selected built cores are mGBA, Supafaust, FCEUmm, BlastEm, ParaLLEl-N64, Dolphin, Tia, ProSystem, Beetle PCE Fast, NeoPop and WonderSwan. **Neither GPLv2-only Stella2014 nor historical noncommercial Snes9x/Genesis Plus GX is part of these four installers.** Do not repeat older licensing research as if these excluded components were in the actual selected build.
- The source companion includes eleven original upstream Git source archives, their SHA256 manifests, and all 37 Dolphin Gitlink sources (GitHub source run 42668367694). The application code, build scripts and original app license are in this repository. Having these files is substantial source evidence, not automatically complete corresponding-source compliance for every dependency.

## Actual runtime code: don't conflate distinct cores into one prelinked binary

- `anything_plays/gba_emulator.py` `NativeCore.__init__` opens **one selected native module** via `ctypes.CDLL(core_path)`, registers Libretro C ABI audio/video/input callbacks and enters that core through `retro_run`. Its `CoreSession` is scoped to one game and one selected system.
- `CoreSession.close` unloads the current game, calls `retro_deinit` and clears callbacks. `Emulator.start` calls `stop` before launching a new worker. (Some 2D modules remain mapped in memory for stability even after their session stops; distinguish this from a formal OS-level library unload.)
- N64 uses an independent child process for successive games on macOS; other systems normally use the core via the main Python host, and GameCube has its accelerated session. **Do not claim all eleven cores execute in fully isolated subprocesses.**
- The Python launcher in this repository carries the MIT license. The GPL-2.x and GPL-3.x emulator native libraries are **separately built**, rather than statically linked to one another.

### Independent check of the actual 3.0 Linux DEB libraries

Inspected `anything-plays-preview_3.0.0~alpha1_amd64.deb` from the genuine four-platform installer SHA proof at [run 42686588072](https://github.com/MasynNay/anything-plays/actions/runs/42686588072), extracted through `dpkg-deb -x` and examined each original compiled `cores/*_libretro.so` with `readelf -d`:

| Native original-source core | ELF DT_NEEDED direct dependencies |
|---|---|
| `blastem` | libm.so.6; libc.so.6 |
| `dolphin` | libXi.so.6; libudev.so.1; libEGL.so.1; libX11.so.6; libstdc++.so.6; libm.so.6; libgcc_s.so.1; libc.so.6; ld-linux-x86-64.so.2 |
| `fceumm` | libm.so.6; libc.so.6 |
| `mednafen_ngp` | libstdc++.so.6; libm.so.6; libgcc_s.so.1; libc.so.6 |
| `mednafen_pce_fast` | libm.so.6; libc.so.6 |
| `mednafen_supafaust` | libstdc++.so.6; libm.so.6; libgcc_s.so.1; libc.so.6; ld-linux-x86-64.so.2 |
| `mednafen_wswan` | libc.so.6 |
| `mgba` | libm.so.6; libc.so.6 |
| `parallel_n64` | libm.so.6; libmvec.so.1; libc.so.6 |
| `prosystem` | libm.so.6; libc.so.6 |
| `tia` | libc.so.6 |

**Result: none of the eleven ELF modules directly imports another `*_libretro.so` as a dynamically linked dependency.** This removes a simplistic claim that GPLv2 and GPLv3 original emulator code is necessarily combined into the *same core binary*. It does **not** decide whether individual cores and the MIT frontend form a combined work under GPL, whether the whole distributor's installed package is an aggregate, or whether every bundled non-core runtime satisfies its license. No whole-distribution legal clearance is inferred.

## Evidence from original source-file grants

Original source files from the checked SHA256 original source archives, not merely the generic `COPYING` documents:

- `blastem/blastem.c` grants GNU **GPL version 3 or greater**.
- `mednafen_supafaust/mednafen/ExtMemStream.cpp`, `mednafen/snes_faust/cpu.cpp`, `fceumm/src/boards/218.c`, `mednafen_pce_fast/mednafen/cdrom/CDAccess_CCD.c` and `mednafen_wswan/mednafen/wswan/rtc.c` expressly say **either GPL version 2 or any later version**. These grants are not GPLv2-only. This is a sampling, not a complete file-by-file scan of every compiled object.
- Original `tia/README.md` plus `src/libretro.c` identify **GPL-2.0-or-later**; Tia replaced the historical old Stella 2014 source and preserves Atari 2600 console profile.
- `mgba` has an MPL 2.0 grant.
- The optional ParaLLEl RSP GNU Lightning code is GPLv3/LGPLv3 according to the original `mupen64plus-rsp-paraLLEl/LICENSE` and Lightning C file headers; **the pinned original source-built N64 workflow explicitly passes `HAVE_PARALLEL_RSP=0` and `HAVE_PARALLEL=0` on Windows, Linux and macOS** in `.github/workflows/v30-parallel-n64-original-native.yml`. Do not assert that the GPLv3/LGPLv3 Lightning static link is necessarily present in the shipped module without contradicting this actual build configuration. Compiler/output source verification remains essential.

The GNU GPL FAQ at https://www.gnu.org/licenses/gpl-faq.html#GPLPlugins distinguishes dynamic plugins with rich data exchange from independent subprocesses. It does **not** establish that all plugins included in an installer form one GPLv2-and-v3 combined program, and it does **not** categorically clear all Libretro plugins. GPLv2-only and GPLv3-only code cannot normally be merged into one program absent additional permission, while GPLv2-or-later source may select GPLv3. See https://www.gnu.org/licenses/gpl-faq.html#v2v3Compatibility.

## Exact release action, not an endless new test loop

1. Review the **actual compiled** original source grants and third-party build/runtime dependencies for each of eleven modules, including the N64 chosen conditional source and Dolphin's 37 Gitlinks. Decide if these separate native modules and the MIT host constitute independently distributable works. Document the applicable source and notice obligations using real license text. No special authorization from absent old Snes9x/Genesis GX maintainers is required.
2. Retain the genuine source archive, original upstream license notices, the associated build/install scripts and verifiable native inputs. Confirm source-to-binary correspondence and needed redistribution terms. Don't turn incomplete evidence into a blanket claim that GPL code may never be distributed.
3. Replace the preview internal version identity by producing and verifying genuine `3.0.0`-named four-platform stable installers. Do not merely rename `alpha.1` EXE/DEB/DMG; Windows installer/App metadata must actually reflect 3.0.0 and its native sources.
4. Publish verified source companion **before** the public four installers, check actual GitHub release SHA256 bytes and names, point `anythingplays.masynnay.com` to public `v3.0.0`, and keep stable 2.0.0 unchanged.

**Do not conflate the broad user-acceptance matrix with license obligations.** Commercial retail-game testing on all 18 consoles and every supported machine is a *project policy*, not a GPL license term. The maintainer can amend that QA policy with honestly reported homebrew, real owner tests and known limitations; the maintainer's repeated N64/GameCube tests must not be erased. Publication still requires a truthful combined-source/rights decision and real production-identity installers. Never mark a test or legal review "passed" solely to bypass a check.
