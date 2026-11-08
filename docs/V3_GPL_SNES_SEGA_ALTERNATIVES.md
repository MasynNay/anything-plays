# 3.0 — GPL SNES/Sega alternative emulator feasibility

**Research only. No binary redistribution permission or release approval.**

The current 18-console/11-core 3.0 preview continues to bundle **Snes9x**
for SNES, plus **Genesis Plus GX** for Genesis, Master System, Game Gear and
SG-1000. Both have **noncommercial restrictions** in their actual
upstream license texts:

- [Snes9x upstream license](https://github.com/libretro/snes9x/blob/master/LICENSE):
  copy/distribute for noncommercial purposes with attribution; warns that
  commercial use includes promotion of a commercial product, with restrictions
  particular to the Libretro port.
- [Genesis Plus GX upstream license](https://github.com/libretro/Genesis-Plus-GX/blob/master/LICENSE.txt):
  redistributions may not be sold or used in a commercial product or
  activity; modified versions impose additional complete-source obligations.

This creates an unresolved compatibility question for an application that
loads its Libretro cores through the same API in-process as GPL-family cores.
A free portfolio and absence of a payment requirement do **not** prove
the license terms are satisfied. Any release needs qualified/rightsholder
review of the actual linked implementation.

## Possible GPL-licensed alternatives without removing consoles

| Existing system profile | Old bundled core | GPL source candidate | Independent license reference |
| --- | --- | --- | --- |
| `snes` | Snes9x | `bsnes` | [Libretro bsnes](https://docs.libretro.com/library/bsnes/), GPLv3 |
| `genesis` | Genesis Plus GX | `BlastEm` | [Libretro BlastEm](https://docs.libretro.com/library/blastem/), GPLv3 |
| `mastersystem` | Genesis Plus GX | `BlastEm` | [BlastEm core info](https://github.com/libretro/libretro-core-info/blob/master/blastem_libretro.info), extension `.sms` |
| `gamegear` | Genesis Plus GX | `BlastEm` | [BlastEm core info](https://github.com/libretro/libretro-core-info/blob/master/blastem_libretro.info), extension `.gg` |
| `sg1000` | Genesis Plus GX | `BlastEm` | [BlastEm core info](https://github.com/libretro/libretro-core-info/blob/master/blastem_libretro.info), extension `.sg` |

BlastEm's Libretro metadata lists original Sega 8-bit cartridges in addition
to Genesis. **Advertised extension support is not proof** the emulation is
functional in this application with full graphics, PSG audio, controller
mapping and saves, nor that four host-native builds are available. bsnes also
has hardware performance and some optional firmware concerns for certain
enhancement-chip games.

`tools/stage_v30_gpl_alternative_candidates.py` acquires temporary
**test-only, unapproved** Linux native cores from the upstream nightly
buildbot and validates single-path ELF ZIP payloads with bounded size and
SHA-256. It does not ship or upload native libraries.

`.github/workflows/v30-gpl-alternative-research.yml` then runs
source-authored homebrew using the **actual production CoreSession frontend**
against *all five* SNES/Sega original test systems, in isolated processes:
`tools/probe_snes_homebrew.py`, `tools/probe_genesis_homebrew.py` and
`tools/probe_sega8_homebrew.py`. It rejects broken game video/audio and
native crashes, and retains only checksum/JSON/png evidence without
copyrighted games or distribution of binaries.

**Possible outcomes:** If **every** native test passes, start a separate
four-platform, independently pinned *source-built* replacement build
for bsnes and BlastEm and repeat core version, saved SRAM, in-panel camera,
input, multiple ROM switching, long-run and real hardware acceptance. A
failed original test means we must investigate and retain the existing
working core until the replacement meets parity; it is **not** evidence
that removing Sega 8-bit support is acceptable.

**Legal limitation:** GPLv3 bsnes and BlastEm could resolve the specific
Snes9x/Genesis Plus GX noncommercial restriction *if* properly reviewed
and substituted, but some other required Libretro cores are GPLv2-only,
the main program has its own dependencies, and **GPLv2-only and GPLv3 may
be incompatible when distributing one combined work**. Different dynamic
libraries or public source code alone are not necessarily a solution.
Investigate the actual architecture, effective GPL versions, alternatives
and legal interpretations; no one may set any source/redistribution/public
approval flag to true based on a candidate test. Full embedded offline
installation across **all 18 profiles** remains nonnegotiable.

The public 3.0 release blocker [#28](https://github.com/MasynNay/anything-plays/issues/28)
remains open and the last publicly approved stable version remains 2.0.
