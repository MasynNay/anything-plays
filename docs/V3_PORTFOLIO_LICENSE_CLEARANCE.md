> **November 9, 2026 superseding correction:** The historical selected ten-original-source lineup below has been replaced by the verified eleven-original-source `gpl-source-built-eleven-tia` lineup. Tia (GPL-2.0-or-later) replaces GPLv2-only Stella2014; source-built Dolphin replaces the older buildbot Dolphin. All four full offline installers passed native and GUI CI [run 42686588072](https://github.com/MasynNay/anything-plays/actions/runs/42686588072) and actual four installer files plus eleven original emulator source trees are preserved on private draft `v3.0.0-rc.1`. The current file-grant, native linkage and source review is [here](V3_0_EXACT_RUNTIME_LICENSE_SCOPE.md). Historical core identities below are no longer authoritative for the intended stable 3.0.0 build. Remaining legal questions need review without misidentifying excluded libraries or erasing the user's hardware tests.\n\n# Anything Plays 3.0 — free educational portfolio distribution checklist

**Status: independent legal/source decision needed before a new public 3.0 installer.** Research prepared November 8, 2026. This is a practical review brief, **not** legal advice, an opinion granting a license, or a claim that any third party has authorized the combined application.

## Intended use and scope

The author intends to demonstrate personal programming and accessibility-oriented computer vision/emulation skills in a **free, strictly educational, non-revenue-generating career portfolio**. No games, proprietary BIOS, game downloads or firmware are included. The target remains **one offline installer** with **18 console profiles / 11 Libretro native cores** on Windows x64, Linux x64, macOS Apple Silicon and macOS Intel. The intended distribution has no purchase price; the author has stated they are not making money from the project. **Disclose that the portfolio may be shown to prospective employers**; do not misrepresent a hiring portfolio as an accredited classroom course.

A **source-only public showcase** of code owned by Anything Plays and demonstrations with original/authorized homebrew (without third-party emulator binaries, ROMs or proprietary BIOS) avoids many binary redistribution problems. It is **not equivalent** to an approved downloadable 3.0 full-offline installer. Keep the approved public 2.0.0 release unchanged and do not expose any unapproved 3.0 GitHub Actions preview ZIP as a stable download.

## Actual selected 3.0 production lineup — verified November 8, 2026

The intended public 3.0 native composition was **changed** from the early
11-core Snes9x/Genesis Plus GX buildbot previews. [PR #102](https://github.com/MasynNay/anything-plays/pull/102)
proved the **ten original-source-built core family** variant inside full
18-profile/11-core desktop installers on all four OSes. [PR #103](https://github.com/MasynNay/anything-plays/pull/103)
aligned the release-mode builder with that same exact composition. The
[verified four-platform ten-source run](https://github.com/MasynNay/anything-plays/actions/runs/42540053758)
passed four of four native jobs; that **does not approve binary rights**.

**Neither Snes9x nor Genesis Plus GX is included in the selected source-built
3.0 production lineup.** They were present in earlier historical full offline
developer previews and remain under their own licenses; those old test
archives cannot be relabeled 3.0 stable. The intended selected 3.0 core
families are mGBA, Mednafen Supafaust, FCEUmm, BlastEm, ParaLLEl-N64,
Dolphin Libretro, Stella 2014, ProSystem, Beetle PCE Fast, Beetle NeoPop
and Beetle WonderSwan. All 11 must remain included offline.

**A new permission request for Snes9x/Genesis Plus GX is not required for
binaries that are not distributed.** Do not contact unrelated upstream
maintainers, pursue noncommercial exceptions for the excluded libraries,
or tell the user those obsolete permissions are a 3.0 shipping dependency.
The selected actual GPL/MPL component and corresponding-source obligations
are still open; nothing in this update waives them.

## Permission vs. license compliance: distinct obligations

1. **Permission for each component.** MIT is only for the application's original code and does not relicense GPL/MPL/noncommercial emulator code. Existing licenses can already grant certain permissions; the question is whether this *particular use and combined distribution* meets them. Free-of-charge and educational are important facts but are not blanket permission. The U.S. Copyright Office explicitly says nonprofit educational/noncommercial purposes do not automatically establish fair use.
2. **Noncommercial restrictions are excluded from the selected 3.0 core pair.** Snes9x and Genesis Plus GX appeared in historical unapproved test variants, but **neither library enters the ten-source release composition**. Their custom noncommercial terms must still be honored for any *different distribution* containing them; the selected 3.0 release has no need for a speculative Snes9x/Genesis Plus GX permission campaign. Retain exact notices and rights review for all libraries actually distributed, rather than treating the project's free/educational purpose as a universal license exception.
3. **GPL-family copyleft across plugins.** The [GNU GPL FAQ's plugin discussion](https://www.gnu.org/licenses/gpl-faq.html#GPLPlugins) treats dynamically loaded code invoking functions and exchanging data structures as potentially a **single combined program**. It explicitly cautions that shared memory exchanging complex structures can be equivalent to dynamic linking. The source-built [experimental 2D child-process bridge](V3_ISOLATED_CORE_RESEARCH.md) does **not** establish legal separation, merely a technical working test. Combining **GPLv2-only** code with **GPLv3-only** code is not generally permitted without additional licensing choices/permissions, while **GPLv2-or-later** might allow version 3: inspect actual file-level grants rather than assuming a label in an index decides the whole binary.
4. **Corresponding source + notices.** For distributing GPL binaries, arrange license copies, attribution, complete corresponding source, build/installation scripts and equivalent access or appropriate offers as required by each exact GPL version and distribution method. For MPL 2.0, retain notices and make covered source files, including modifications, available per the applicable terms. For custom NC components, preserve the original copyright/license text and any source obligations. A source commit matching a *reported* buildbot revision is **not** proof that the binary was built from that source.
5. **Exact third-party assets and runtimes.** Audit Dolphin Sys data (and full submodules), compiler/build inputs, frozen native dependencies, OpenCV/Python wheel notices, artworks and icons against their actual provenance. No ROMs/BIOS; use original or otherwise authorized homebrew media for screenshots/demos.
6. **Independent signoff + QA.** Document a reasoned rights/combined-work decision for this exact arrangement, the 44 native platform binaries and 4 Dolphin Sys snapshots, user-facing attribution and source links, actual four-platform camera/audio/save/endurance results and owner authorization. Signing/notarization limitations must be accurately disclosed. Keep `config/v3.0-core-lock.json`, `config/v3.0-release-acceptance.json`, the final corresponding-source inventory, and all other release flags UNAPPROVED until evidence actually exists.

## Inventory of the selected actual eleven 3.0 production core families

| Native core | Console profiles | Source/license review still required |
| --- | --- | --- |
| mGBA | GB, GBC, GBA | Original pinned-source MPL 2.0 library; bundle original MPL notice, matching covered source and exact four-platform build inputs |
| Mednafen Supafaust | SNES | Original source-built GPLv2-family replacement for Snes9x; verify exact file-level version options and compiler/dependency terms |
| FCEUmm | NES | Source-built GPLv2-family library; file-level grant, corresponding source and notices |
| BlastEm | Genesis, Master System, Game Gear, SG-1000 | Original GPLv3-or-later source-built replacement for Genesis Plus GX; independently review in-process GPL2/GPL3 combination and exact bundled dependencies |
| ParaLLEl-N64 | N64 | Original pinned source-built library with eleven original mixed GPL/LGPL/MIT notices; preserve and reconcile every applicable source component |
| Dolphin Libretro | GameCube | Only historical buildbot native family left in the selected trial; original GPL source, runtime dependencies and Dolphin Sys correspondence still unproven for shipped binary |
| Stella 2014 | Atari 2600 | Original source-built GPLv2-family library; exact notices and matching compiled inputs |
| ProSystem | Atari 7800 | Original source-built GPLv2-family library; exact notices and matching compiled inputs |
| Beetle PCE Fast | PC Engine / TurboGrafx-16 HuCard | Original source-built GPLv2-family replacement for historical unversioned buildbot core; match exact source archive and native checksums |
| Beetle NeoPop | NGP, NGPC | Original pinned source-built GPLv2-family library; notices, original audio evidence and precise compiled runtime |
| Beetle WonderSwan | WS, WSC | Original pinned source-built GPLv2-family library; precise source/archive identity and rights |

The source-built package is **technically tested**, not legally cleared. The
core license labels above are summary identifiers, not verified conclusions
about every file, vendored dependency or compatible version. The upstream
[Libretro license index](https://docs.libretro.com/development/licenses/)
provides initial triage; the source-level notices, produced archive SHA and
actual runtime graph control a real redistribution decision.

The Dolphin corresponding-source trail now includes the
[unapproved source-only archive with the pinned parent and all 37 Gitlinks](https://github.com/MasynNay/anything-plays/actions/runs/42542696226)
from [PR #104](https://github.com/MasynNay/anything-plays/pull/104).
It is **not** proof that the old archived native was built from these source
files. [PR #105](https://github.com/MasynNay/anything-plays/pull/105)
opens a separate original, unmodified Dolphin source-build research path;
do not substitute a new untested GameCube binary into the already
owner-verified working preview.

## Release-compliance decision path for the selected eleven sources

**A — Verify the exact native compositions.** Only the source-built
Supafaust/BlastEm alternatives, not the old noncommercial Snes9x/Genesis
Plus GX, may enter the intended 3.0 production installers. The production
lock, 44 core binaries, 4 Dolphin Sys archives, notices and source archive
hashes must describe the **actual** installed contents on all four targets.

**B — Determine GPL version compatibility from the real invocation graph.**
The frontend is originally MIT licensed and native cores are separate
Libretro shared libraries, but dynamic plugin loading can constitute a
combined program. For each core, evaluate the exact file-level
GPLv2-only/v2-or-later/GPLv3-or-later grants, any linked code and the
actual host/core coupling. A GPL license itself can grant redistribution
rights without seeking individual permission **when its conditions are
satisfied**. Do not automatically conclude that GPLv2 and GPLv3 code are
combined across unrelated core files, or that merely keeping DLLs separate
guarantees compatibility. Record the reasoning and exact source evidence.

**C — Provide corresponding source and build scripts for every actual
distributed core.** Original Dolphin is the remaining independent
binary-to-source gap. Its preserved 38 source candidates help but do not
demonstrate the original buildbot binary's exact compiler inputs, Sys
rights or all transitive dependencies. Preserve third-party notices and
required source access alongside the full application installers.

**D — Verify the exact production artifacts and publish only after the
source/license review is complete.** Preserve the maintainer's previously
successful N64 and GameCube gameplay reports; do not ask them to replay
the same functionality. New/replaced binaries still require their own
relevant checks. Record true signing limitations, install hashes and
any hardware coverage gaps. Run the strict 3.0 approval workflow without
setting unsupported release flags.

## Things this review cannot do

- This document and GitHub Actions cannot grant rights on a copyright holder's behalf or turn a GPL-incompatible binary into a GPL-compatible one.
- It cannot prove a job portfolio is noncommercial under every third-party custom license.
- It cannot waive 44 native binary/source plus Dolphin asset obligations, disclose unverified source correspondence as fact, or replace owner hardware testing.
- "Educational only," "not for profit," and "I included a disclaimer" are **not** independently sufficient licenses to distribute third-party program binaries.

**References consulted:** [Snes9x LICENSE](https://github.com/snes9xgit/snes9x/blob/master/LICENSE), [Genesis Plus GX LICENSE](https://github.com/libretro/Genesis-Plus-GX/blob/master/LICENSE.txt), [GNU GPL FAQ: plugins/combined works](https://www.gnu.org/licenses/gpl-faq.html#GPLPlugins), [GNU GPL FAQ: GPL2/GPL3 compatibility](https://www.gnu.org/licenses/gpl-faq.html#v2v3Compatibility), [Libretro licenses](https://docs.libretro.com/development/licenses/), [U.S. Copyright Office fair-use information](https://www.copyright.gov/fair-use/more-info.html).
