# 3.0 licensing compatibility — distribution decision required

**Status:** REQUIRES REVIEW — not a clearance or legal opinion.

## Why a green installer is not yet a distributable installer

The 3.0 test bundle contains **11** native Libretro cores and the Python desktop
frontend, and **18** console profiles. All four installer builds passed automated
packaging tests. That establishes neither license compatibility nor compliance
for the *exact binaries* shipped.

The [Libretro upstream license index](https://docs.libretro.com/development/licenses/)
lists, among others:

- **Snes9x** and **Genesis Plus GX:** noncommercial use restrictions. The exact
  upstream copies are preserved in `licenses/Snes9x-LICENSE.txt` and
  `licenses/Genesis-Plus-GX-LICENSE.txt`.
- **ParaLLEl-N64:** GPLv3, including components with their own notices.
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
question**, because a noncommercial restriction is not automatically
compatible with GPL permissions if both licenses apply to one combined work.

### Required decision and evidence before public 3.0 binary publication

1. Review the exact Snes9x and Genesis Plus GX permissions and any artwork
   restrictions against the intended portfolio distribution (free vs promotional
   or commercial use). No payment does not necessarily decide the meaning of
   every noncommercial clause.
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

### Options that preserve the user's product scope

The product decision is **no additional emulators for 3.0** and all core
functionality integrated without first-run external downloads. If the
license compatibility review requires a change, an *offline bundled*
separate-process core worker with narrow IPC could be evaluated instead of
dropping support; however, that is engineering work and **not** itself a
legal safe harbor. Alternatively, acquire specific upstream redistribution
permission where needed. Do not silently replace one of the supported
cores or require users to download separate emulators.

### Progress already established

- [Full 3.0 four-platform bundle CI](https://github.com/MasynNay/anything-plays/actions/runs/42432952359)
- [Exact preview binary integrity and provenance record](../config/v3.0-preview-candidate-integrity.json)
- [3.0 distribution evidence](V3_DISTRIBUTION_READINESS.md)
- [Release readiness issue #28](https://github.com/MasynNay/anything-plays/issues/28)

The current app remains usable as a developer preview. The public **stable**
3.0 binary release remains withheld pending these determinations. This review
does not apply retroactively to the already published, separately scoped v2.0
installer decision.
