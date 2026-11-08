# Anything Plays 3.0 — free educational portfolio distribution checklist

**Status: independent legal/source decision needed before a new public 3.0 installer.** Research prepared November 8, 2026. This is a practical review brief, **not** legal advice, an opinion granting a license, or a claim that any third party has authorized the combined application.

## Intended use and scope

The author intends to demonstrate personal programming and accessibility-oriented computer vision/emulation skills in a **free, strictly educational, non-revenue-generating career portfolio**. No games, proprietary BIOS, game downloads or firmware are included. The target remains **one offline installer** with **18 console profiles / 11 Libretro native cores** on Windows x64, Linux x64, macOS Apple Silicon and macOS Intel. The intended distribution has no purchase price; the author has stated they are not making money from the project. **Disclose that the portfolio may be shown to prospective employers**; do not misrepresent a hiring portfolio as an accredited classroom course.

A **source-only public showcase** of code owned by Anything Plays and demonstrations with original/authorized homebrew (without third-party emulator binaries, ROMs or proprietary BIOS) avoids many binary redistribution problems. It is **not equivalent** to an approved downloadable 3.0 full-offline installer. Keep the approved public 2.0.0 release unchanged and do not expose any unapproved 3.0 GitHub Actions preview ZIP as a stable download.

## Permission vs. license compliance: distinct obligations

1. **Permission for each component.** MIT is only for the application's original code and does not relicense GPL/MPL/noncommercial emulator code. Existing licenses can already grant certain permissions; the question is whether this *particular use and combined distribution* meets them. Free-of-charge and educational are important facts but are not blanket permission. The U.S. Copyright Office explicitly says nonprofit educational/noncommercial purposes do not automatically establish fair use.
2. **Noncommercial restrictions.** [Snes9x's original license](https://github.com/snes9xgit/snes9x/blob/master/LICENSE) grants copying/distribution for noncommercial purposes with its license and notices, but also uses the phrases **PERSONAL USE** and **promotional use for a commercial product**. [Genesis Plus GX's original license](https://github.com/libretro/Genesis-Plus-GX/blob/master/LICENSE.txt) prohibits sales and use in commercial products/activities, requires notices and complete source for modified distributions. An educational hiring portfolio is not *automatically* commercial or noncommercial under all these terms; request clarification from copyright holders if the precise scope is disputed. Do not assume the repository maintainer alone owns or can relicense all contributions.
3. **GPL-family copyleft across plugins.** The [GNU GPL FAQ's plugin discussion](https://www.gnu.org/licenses/gpl-faq.html#GPLPlugins) treats dynamically loaded code invoking functions and exchanging data structures as potentially a **single combined program**. It explicitly cautions that shared memory exchanging complex structures can be equivalent to dynamic linking. The source-built [experimental 2D child-process bridge](V3_ISOLATED_CORE_RESEARCH.md) does **not** establish legal separation, merely a technical working test. Combining **GPLv2-only** code with **GPLv3-only** code is not generally permitted without additional licensing choices/permissions, while **GPLv2-or-later** might allow version 3: inspect actual file-level grants rather than assuming a label in an index decides the whole binary.
4. **Corresponding source + notices.** For distributing GPL binaries, arrange license copies, attribution, complete corresponding source, build/installation scripts and equivalent access or appropriate offers as required by each exact GPL version and distribution method. For MPL 2.0, retain notices and make covered source files, including modifications, available per the applicable terms. For custom NC components, preserve the original copyright/license text and any source obligations. A source commit matching a *reported* buildbot revision is **not** proof that the binary was built from that source.
5. **Exact third-party assets and runtimes.** Audit Dolphin Sys data (and full submodules), compiler/build inputs, frozen native dependencies, OpenCV/Python wheel notices, artworks and icons against their actual provenance. No ROMs/BIOS; use original or otherwise authorized homebrew media for screenshots/demos.
6. **Independent signoff + QA.** Document a reasoned rights/combined-work decision for this exact arrangement, the 44 native platform binaries and 4 Dolphin Sys snapshots, user-facing attribution and source links, actual four-platform camera/audio/save/endurance results and owner authorization. Signing/notarization limitations must be accurately disclosed. Keep `config/v3.0-core-lock.json`, `config/v3.0-release-acceptance.json`, the final corresponding-source inventory, and all other release flags UNAPPROVED until evidence actually exists.

## Inventory of the CURRENT 11 native cores, not research-only alternatives

| Bundled core | Current profiles | Upstream license indicator | Specific release review |
| --- | --- | --- | --- |
| mGBA | GB, GBC, GBA | MPL 2.0 | Retain MPL and covered-source obligations; verify actual binary/source and notices |
| Snes9x | SNES | Custom noncommercial | Clarify free hiring-portfolio / promotional scope, notices and combined plugin rights |
| FCEUmm | NES | GPLv2 in Libretro index | Corresponding source, precise GPL version/options, notices, plugin compatibility |
| Genesis Plus GX | Genesis, Master System, Game Gear, SG-1000 | Custom noncommercial | Clarify free hiring-portfolio scope and combined GPL licensing, notices; source if modified |
| Stella 2014 | Atari 2600 | GPLv2 in upstream notice | Corresponding source/dependencies, exact binary, GPL compatibility |
| ProSystem | Atari 7800 | GPLv2 in upstream notice | Same |
| Beetle PCE Fast | PC Engine HuCard | GPLv2 in upstream notice | Do **not** attribute old unversioned nightly source to newer pinned source-built research binary |
| Beetle NeoPop | NGP / NGPC | GPLv2 in upstream notice | Matching source/dependencies and compiled rights, not just native A/V |
| Beetle WonderSwan | WS / WSC | GPLv2 in upstream notice | Same |
| ParaLLEl-N64 | N64 | Libretro license **index says GPLv3**, core library page says GPLv2; nested parts vary | Resolve discrepancy at exact Git revision and compiled components, incl. Mupen64Plus, RSP/plugin notices; check GPLv2-only/GPLv3 combinations |
| Dolphin Libretro | GameCube | Libretro docs say GPLv2; upstream includes GPL-2.0-or-later files and other terms | Match exact native build, its own nested components and Dolphin Sys assets, source/build scripts and GPL choices |

Upstream summary: [Libretro license index](https://docs.libretro.com/development/licenses/). Existing captured original notices: [third-party notices](THIRD_PARTY_NOTICES.md). Exact archived source review: [production source schema](V3_CORRESPONDING_SOURCE_REVIEW_SCHEMA.md). An index is a **triage aid**, not a substitute for the file-level license corresponding to a compiled binary.

**Research substitutions are NOT in the app:** source-built GPLv2-or-later Supafaust SNES and GPLv3-only bsnes/BlastEm have genuine four-OS native A/V research evidence, but no approved final redistribution architecture or replaced 3.0 core. The candidate alternatives do not silently clear the current binary.

## Lowest-friction decision path for this exact noncommercial portfolio

**A — Immediately publish the showcase/source of original work, not the unapproved 3.0 binaries.** Present own original camera controls, architecture, screenshots using original/authorized homebrew, tests, roadmap and licenses. Do not claim end users can install all 18 consoles from a public approved 3.0 download yet.

**B — Ask copyright holders for targeted confirmation before distributing this combined installer.** Use [prepared outreach](V3_PORTFOLIO_PERMISSION_REQUESTS.md) for Snes9x and Genesis Plus GX: disclose that a free project can be used to seek employment, that the libraries are linked as Libretro cores, and that no ROMs/BIOS are bundled. Ask whether their already-granted license covers this use and, if not, whether they can grant a specific exception. Collect **written, attributable replies** and assess whether respondents hold enough rights. A permission from a noncommercial core cannot override a conflicting GPLv2-only vs GPLv3-only obligation in another core.

**C — Obtain a qualified combined-work review of the precise software and intended release.** In-process Libretro callbacks, shared memory, official GPL FAQ and exact GPL version choices matter. Do not label a separate process or different folder "safe" by assumption. The reviewer may conclude compatible combinations are possible, request additional permissions, or require more architectural changes.

**D — Once B/C and source audit are complete, build and physically verify the approved 4OS production installers** with the existing strict source/rights and 600-observation owner QA gates. Only then use the controlled public publisher. See [publication runbook](V3_PUBLICATION_RUNBOOK.md).

## Things this review cannot do

- This document and GitHub Actions cannot grant rights on a copyright holder's behalf or turn a GPL-incompatible binary into a GPL-compatible one.
- It cannot prove a job portfolio is noncommercial under every third-party custom license.
- It cannot waive 44 native binary/source plus Dolphin asset obligations, disclose unverified source correspondence as fact, or replace owner hardware testing.
- "Educational only," "not for profit," and "I included a disclaimer" are **not** independently sufficient licenses to distribute third-party program binaries.

**References consulted:** [Snes9x LICENSE](https://github.com/snes9xgit/snes9x/blob/master/LICENSE), [Genesis Plus GX LICENSE](https://github.com/libretro/Genesis-Plus-GX/blob/master/LICENSE.txt), [GNU GPL FAQ: plugins/combined works](https://www.gnu.org/licenses/gpl-faq.html#GPLPlugins), [GNU GPL FAQ: GPL2/GPL3 compatibility](https://www.gnu.org/licenses/gpl-faq.html#v2v3Compatibility), [Libretro licenses](https://docs.libretro.com/development/licenses/), [U.S. Copyright Office fair-use information](https://www.copyright.gov/fair-use/more-info.html).
