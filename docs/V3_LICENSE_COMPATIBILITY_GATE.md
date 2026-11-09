> **November 9, 2026 superseding correction:** This document's older ten-core/Stella snapshot is historical and must not be treated as the actual 3.0 release blocker. The current selected binary lineup uses all ELEVEN original source-built families, including GPL-2.0-or-later Tia (not Stella2014), and excludes Snes9x/Genesis Plus GX. See [the exact runtime/source/ELF linkage audit](V3_0_EXACT_RUNTIME_LICENSE_SCOPE.md), which verifies no direct ELF-to-ELF core dependency and checks real N64 build flags. Mixed GPL versions across **separately built and selected** emulator libraries do not automatically prove illegal combination; similarly, a source ZIP alone does not establish complete third-party compliance. Do not repeat historical claims as current facts.\n\n# 3.0 licensing compatibility — distribution decision required

**Status:** REQUIRES REVIEW — not a clearance or legal opinion.

## Why a green installer is not yet a distributable installer

The selected 3.0 **ten-original-source-built** test bundle contains 11 native
Libretro core families and 18 profiles, with the Python desktop frontend;
the retained Dolphin native family is the original archived buildbot binary.
Four-platform installer and native integration jobs passed. This establishes
technical function, not the license compatibility of the **exact binaries**
or complete corresponding-source rights.

The [Libretro upstream license index](https://docs.libretro.com/development/licenses/)
lists, among others:

- **Snes9x** and **Genesis Plus GX:** noncommercial restrictions apply to
  **historical unapproved preview variants**, but those binaries have been
  **replaced** by original source-built Supafaust and BlastEm in the selected
  3.0 production candidate. The final release must exclude both old libraries.
- **ParaLLEl-N64:** the upstream index and individual source components
  require a **revision-accurate GPL/LGPL/MIT notice and version review**;
  its pinned source-built 3.0 candidate retains eleven original notices.
- **BlastEm:** GPLv3-or-later; Supafaust and other Mednafen-derived cores
  need file-level review of GPLv2-only versus GPLv2-or-later grants.
- **FCEUmm, Dolphin, Stella, ProSystem, Beetle PCE Fast, NeoPop and WonderSwan:**
  GPL-family licenses, with the version and dependency terms to be checked at
  each exact source revision.
- **mGBA:** MPL 2.0.

### Core issue: separate works or combined software?

Anything Plays dynamically loads native Libretro cores through a shared
interface. The [GNU GPL FAQ](https://www.gnu.org/licenses/gpl-faq.html.en#GPLPlugins)
explains that dynamically linked plug-ins exchanging function calls and data
structures may be considered part of a combined program. Its
[aggregation discussion](https://www.gnu.org/licenses/gpl-faq.html.en#MereAggregation)
distinguishes that from distributing genuinely separate programs together.

This is **not** a conclusion that Anything Plays' exact packaging is unlawful:
the answer depends on how the host and cores are actually combined, how they
interact and the precise upstream permissions. It is a **material release
question**, because GPLv2-only and GPLv3-only components may be incompatible **if
they actually combine into one work**. The selected ten-source build removes
the earlier Snes9x/Genesis Plus GX noncommercial restriction question by
excluding those libraries entirely. Do not imply such excluded permissions
are still mandatory for the selected stable installer.

### Clarification for a free educational hiring portfolio

The project's author confirms that the intended 3.0 showcase is free, educational and **not a revenue-generating product**. The fact that the source is shown to prospective employers should be disclosed as a use case; it should not be automatically classified as commercial, nor assumed to satisfy all custom noncommercial grants without checking the relevant wording. The original Snes9x/Genesis Plus GX license texts still matter **only to
historical preview archives or future different variants that actually ship
them**, not to the chosen Supafaust/BlastEm release composition. See the
[updated exact eleven-core review](V3_PORTFOLIO_LICENSE_CLEARANCE.md).
Older [Snes9x/Genesis Plus GX permission drafts](V3_PORTFOLIO_PERMISSION_REQUESTS.md)
are retained as historical research; **do not send them** to unrelated
upstream authors for components excluded from this release.

Do not claim that the recent shared-memory 2D isolated worker prototype fixes copyleft linking by itself. GNU's GPL FAQ explicitly warns shared memory with complex interoperation may amount to a combined program. Independent, qualified license/architecture review still decides whether an approved 3.0 offline installer can be shipped in its current form.

### Required decision and evidence before public 3.0 binary publication

1. Verify that the final source-built installer actually **excludes**
   Snes9x and Genesis Plus GX binaries. These absent noncommercial cores are
   **not** a reason to contact upstream authors or block the selected build.
   Review the permissions of the *actual* eleven selected native families.
2. Review the actual core-host linking/invocation design and GPL/other
   copyleft obligations. Resolve whether a separate process/IPC architecture,
   a documented legally permissible aggregation, or specific rights-holder
   approval is required. Do not assume a renamed DLL or separate ZIP by
   itself changes the underlying combined-work analysis.
3. Match **every** shipped native binary to its corresponding source, patches,
   build scripts, component notices and permitted redistribution terms. Include
   access to the complete corresponding source as required.
4. Publish verified immutable inputs and installer checksums; disclose
   unsigned Windows and unnotarized macOS limitations accurately.
5. Confirm real-device GameCube/other emulation compatibility and preserve
   honest known-limitations text. Do not call CI homebrew footage the same as
   broad retail-game compatibility.
6. Only after the documented release decision should the deliberately
   fail-closed `config/v3.0-release-acceptance.json` record be completed and
   the `tools/check_v30_release.py` gate run **without** `--report-only`.

The [four-Sega-console source/license history](V3_SEGA_LICENSE_OPTIONS.md)
records why source-built GPLv3 BlastEm replaced Genesis Plus GX in the
selected ten-source installer; other trial substitutions are **not** the
current release lineup. The
reviewer must not substitute cores or approve a separate-process design
solely because CI demonstrated original homebrew video/audio.

### Options that preserve the user's product scope

The product decision is **no additional emulators for 3.0** and all core
functionality integrated without first-run external downloads. If the
license compatibility review requires a change, an *offline bundled*
separate-process core worker with narrow IPC could be evaluated instead of
dropping support; however, that is engineering work and **not** itself a
legal safe harbor. Alternatively, obtain compatible permissions only if an **actually selected**
component requires them. Do not reintroduce excluded noncommercial cores,
silently drop console profiles, or require users to install separate emulators.

### Progress already established

- [Full 3.0 four-platform bundle CI](https://github.com/MasynNay/anything-plays/actions/runs/42432952359)
- [Exact preview binary integrity and provenance record](../config/v3.0-preview-candidate-integrity.json)
- [3.0 distribution evidence](V3_DISTRIBUTION_READINESS.md)
- [Release readiness issue #28](https://github.com/MasynNay/anything-plays/issues/28)

The current app remains usable as a developer preview. The public **stable**
3.0 binary release remains withheld pending these determinations. This review
does not apply retroactively to the already published, separately scoped v2.0
installer decision.
