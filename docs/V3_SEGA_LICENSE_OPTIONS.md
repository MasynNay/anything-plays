# Anything Plays 3.0 — Sega four-console distribution options

**Status: Unapproved reviewer decision record. Not a legal clearance and not a
license to publish the existing source-built developer-preview binaries.**

## Required scope

The existing native `Genesis Plus GX` Libretro core covers **all four**
3.0 console profiles: `genesis`, `mastersystem`, `gamegear`, `sg1000`.
The user expects **one offline desktop installer**, no external emulator
downloads/RetroArch installation, and retention of all 18 working profiles.
The existing core has noncommercial restrictions. The 3.0 application also
loads GPL-family native libraries in-process, and the exact applicable
license families and derivative/aggregation treatment require independent
expert assessment. A technically working alternative cannot be silently
substituted or automatically approved as a GPL-compatible *combined work*.

## Reviewed first-party Libretro alternatives and what they do not solve

| Candidate | Upstream license as documented | Advertised console coverage | Missing for a straightforward approved four-profile 3.0 replacement |
| --- | --- | --- | --- |
| [Genesis Plus GX](https://github.com/libretro/Genesis-Plus-GX/blob/master/LICENSE.txt) (currently bundled) | Noncommercial/custom; exact notices must be reviewed | Genesis, Master System, Game Gear, SG-1000 | Redistribution permission/compliance of existing combined binary installer |
| [BlastEm](https://docs.libretro.com/library/blastem/) | GPLv3; original pinned GPL3 `COPYING` verified | All four original cartridge test paths now genuinely demonstrated | GPLv3-only with potential GPLv2-only combined-program conflicts, real games/SRAM/controller/endurance and source dependency review |
| [PicoDrive](https://docs.libretro.com/library/picodrive/) | **Noncommercial** in Libretro documentation | Genesis, Master System and other formats; core metadata includes `.gg` / `.sg` | Does **not** eliminate the NC rights decision; advertised formats are not actual proven four-system gameplay/rights |
| [Gearsystem](https://docs.libretro.com/library/gearsystem/) | GPLv3 | Master System, Game Gear, SG-1000 | Does not replace Genesis and may introduce the same GPLv2-only/GPLv3 combined-work issue |
| [SMS Plus GX](https://docs.libretro.com/library/smsplus/) | GPLv2 | Master System and Game Gear | Does not cover Genesis or SG-1000, so increases required core count and still needs lawful alternatives for both |
| [ClownMDEmu](https://docs.libretro.com/library/clownmdemu/) | AGPLv3 (or later per source) | Genesis/Mega Drive, Sega CD | Does not cover Sega 8-bit systems; AGPLv3 raises a separate compatibility review |

**Bottom line:** no single documented, independently demonstrated
**GPLv2-family** replacement for all four Sega cartridge profiles was found
in this shortlist. This is a scoped research finding, not a claim that no
other emulator or authorized license option exists. PicoDrive and Genesis
Plus GX do not remove NC questions; switching to GPLv3-only BlastEm or
Gearsystem is not automatically compatible with existing GPLv2-only
combined-work dependencies; changing the number of DLLs is not itself a
legal solution.

## Positive experimental work already completed

The [four-platform original source-built alternative lab
42491825162](https://github.com/MasynNay/anything-plays/actions/runs/42491825162)
passed **8/8** pinned-source bsnes and BlastEm job combinations on Windows,
Linux and both Mac architectures. BlastEm's four original source-generated
Sega video/audio paths passed in each host's native Libretro frontend.
For Genesis, the test uses an independently recorded **10-byte original
homebrew TMSS-safe variant**, not a modification to retail games or
proof of broad retail-game compatibility. All original SHA source/native
archives are retained with checksum evidence. The core is GPLv3, however,
so this is technical feasibility, **not** a binary release decision.

The separately source-built GPLv2-or-later
[Supafaust SNES](V3_GPL2_SUPAFAUST_RESEARCH.md) research passed **4/4**
native platform source builds and original SNES video/SPC audio in
[run 42494297281](https://github.com/MasynNay/anything-plays/actions/runs/42494297281);
it has its own independently rehashed original source archive and an exact
macOS compatibility patch. That could resolve the specific SNES
noncommercial core need after review, but it does not resolve the **Sega**
core and remaining license obligations by itself.

## Release decision paths for an independent reviewer

**Path A: rights-holder permissions or a documented compatible in-process
distribution.** Review exact current upstream 44 compiled core libraries,
Dolphin Sys, full dependent sources/build instructions/notices and
combined-program license terms. Obtain specific permission if needed from
noncommercial copyright holders. This retains the already working
18-profile/11-core frontend and avoids a risky emulator replacement.
Source and platform-specific hardware tests remain mandatory.

**Path B: independently reviewed, appropriately separated runtime
processes plus an offline aggregate installer.** If qualified licensing
review establishes that genuinely independent programs with narrow IPC
can be distributed as separate works, prototype a bundled process boundary
while retaining zero first-run downloads, front-end ownership of the same
camera/keyboard/video/audio UI, clean ROM switching and game saves. Be
prepared for substantial GameCube GPU/IPC complexity and another four-OS
physical acceptance cycle. **A subprocess, renamed library or static
folder split does not automatically establish lawful aggregation.**

**Path C: compatible source-built replacement cores with exactly the
required coverage.** Only pursue alternatives whose licenses and their
transitive dependencies are independently determined compatible in the
chosen architecture. Verify every physical console path, original native
source builds on all four hosts, real game video/audio, controller/camera,
SRAM/load/save, ROM switching, long-lived stability, and suitable equivalent
original source delivery. Do not silently drop any of the user's four Sega
profiles or advertise features that only passed a narrow homebrew probe.

All three paths still require the owner to perform and document the
original physical QA with the [SHA-pinned 3.0 QA
kit](V3_PHYSICAL_QA_RUNBOOK.md), independent source-to-binary
correspondence and rights/compatibility review for the entire bundled
product, source/package signing disclosures, an approved production lock,
and deliberate final publication.

**No path has been approved as of this record.** The existing 3.0
`feature/v3.0-unified-test` stays fully functional and **test-only**;
published stable v2.0.0 must not be changed retroactively. See
[issue #28](https://github.com/MasynNay/anything-plays/issues/28)
and [license gate](V3_LICENSE_COMPATIBILITY_GATE.md).
