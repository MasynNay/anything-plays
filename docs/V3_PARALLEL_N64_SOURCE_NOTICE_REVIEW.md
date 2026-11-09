# ParaLLEl-N64 3.0: exact source notice and Gitlink audit

**Status: original upstream source evidence only, NOT corresponding-source
proof for the distributed native binaries, legal permission or public 3.0.**

The current 3.0 *preview* bundles ParaLLEl-N64 as a native Libretro
library. The original archived Linux binary reported source revision
`e0ef5d673257e2e83bf9b7cffe62eda141af8493` from
`https://github.com/libretro/parallel-n64`. The four native binary
SHA-256 fingerprints are pinned in
`config/v3.0-parallel-n64-source-notice-candidates.json` and
the prior [source review 42444450521](https://github.com/MasynNay/anything-plays/actions/runs/42444450521).

## Confirmed source tree correction: zero Gitlinks

Earlier general release notes grouped ParaLLEl-N64 with Dolphin as
requiring missing contents of Git submodules because the source includes
`.gitmodules`. That was too broad. The **exact pinned N64 Git tree** contains
**1970 entries** and **0 real Gitlink objects** (`type=commit`,
`mode=160000`). Its `.gitmodules` is the **empty Git blob**
`e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` of **0 bytes**.
There is no ParaLLEl-N64 nested Gitlink archive left to acquire
at this reported revision.

That conclusion is limited to Git submodules. The compiler toolchain,
system libraries, build configuration, platform-specific code and
other generated or externally fetched dependencies are still subject
to independent corresponding-source and license review.

## Eleven original embedded license/notice candidates

The pinned source tree contains exactly these eleven file paths matching
the source-code notice naming patterns:

| Original source path | Evidence scope |
| --- | --- |
| `gles2n64/src/COPYING` | One original component notice |
| `mupen64plus-core/LICENSES` | Mupen core license inventory |
| `mupen64plus-rsp-cxd4/COPYING` | cxd4 RSP notice |
| `mupen64plus-rsp-hle/LICENSES` | HLE RSP notices |
| `mupen64plus-rsp-paraLLEl/LICENSE` | ParaLLEl RSP component |
| `mupen64plus-rsp-paraLLEl/LICENSE.LESSER` | Component copyleft/license text |
| `mupen64plus-rsp-paraLLEl/LICENSE.MIT` | Component permissive-license text |
| `mupen64plus-rsp-paraLLEl/lightning/COPYING` | Lightning component main notice |
| `mupen64plus-rsp-paraLLEl/lightning/COPYING.DOC` | Lightning additional notice |
| `mupen64plus-rsp-paraLLEl/lightning/COPYING.LESSER` | Lightning copyleft/license text |
| `mupen64plus-video-paraLLEl/parallel-rdp/LICENSE` | Parallel RDP component notice |

Each entry has an immutable **Git blob SHA-1 and byte length** in
`config/v3.0-parallel-n64-source-notice-candidates.json`. The original
[reported source archive capture](https://github.com/MasynNay/anything-plays/actions/runs/42441448884)
preserved the actual upstream compressed source TAR,
`source-parallel_n64-e0ef5d673257e2e83bf9b7cffe62eda141af8493.tar.gz`,
with **6,877,459 bytes** and SHA-256
`a8beb0a4aef9636479457237d3e12393c65425068e30c6d98f8f36faa4cb723e`.
This TAR was independently re-downloaded from the original CI source
artifact and inspected: **1971 TAR members** (including the root
directory), the actual empty `.gitmodules` and all eleven original
notice files with expected sizes. No additional game content, native
core or redistributed installer was included in the source review.

## Repeatable archive and revision validation

`tools/audit_v30_parallel_n64_source.py` checks the original source
review against **four native SHA-256 identities** and the reported Git
commit and original source TAR SHA-256/length. It fetches the *exact*
GitHub revision's tree and rejects nonempty/unexpected Gitlinks,
truncated responses, an unexpected number of entries, changed or
missing source notice blobs and changed empty `.gitmodules`.
It streams the original archived source TAR **without extraction**,
computes the exact original Git blob SHA-1 from each of eleven notice
file contents, and creates an `UNAPPROVED` JSON containing the actual
SHA-256/byte length of each notice. The separate workflow
`.github/workflows/v30-parallel-n64-source-audit.yml`
downloads the *original* preserved source and source-review artifacts
from successful runs `42441448884` and `42444450521`,
validates their reviewer checksums, then executes this audit using
the original source TAR. It stores only reviewer JSON and SHA256SUMS,
not the source TAR a second time.

The current repo already includes five consolidated ParaLLEl license
copies under `licenses/`. The eleven original source-tree file
candidates are **not proof** that all eleven files must apply to each
particular platform's compiled library: a build-option and transitive
dependency audit must determine which components and notices are
required, and the in-process GPL/noncommercial combined-work problem
must be independently reviewed.

## Release scope not changed

- Authentic Git snapshot identity and zero submodules **can** be verified.
- Exact binary-to-compiler/source correspondence for the four packaged
  N64 core binaries **is not yet independently proven**.
- Whether the generated/reviewed notices and relevant GPL/LGPL
  source obligations are legally fulfilled is **not determined**.
- Mixed-license bundling with Snes9x and Genesis Plus GX, physical
  four-platform real-game/video/audio/camera/save QA, notarization and
  final immutable production approval remain unresolved.

All source/rights flags stay **false**. A green research job must not
change `config/v3.0-core-lock.json` or
`config/v3.0-release-acceptance.json`, nor be used to publish 3.0
test installers as stable binaries.

## Verified original archived-source run — November 8, 2026 UTC

[PR #71](https://github.com/MasynNay/anything-plays/pull/71)
**merged** at `4937a4cc1e38e4b5daa7c52fdd0b8c1ca93cefb4`
after [source regression CI 42454235141](https://github.com/MasynNay/anything-plays/actions/runs/42454235141)
**SUCCESS** and [real original N64 source/archive audit CI
42454235212](https://github.com/MasynNay/anything-plays/actions/runs/42454235212)
**SUCCESS** on reviewed PR commit
`b0339f9c659cf1af23e67110d1e26ddea0e5af0b`.
Source regressions were Python 3.12, Python 3.13 and native mGBA
success; unaffected platform packaging checks correctly skipped.
The real source workflow downloaded the original 6,877,459-byte
TAR from source capture run `42441448884` and original four-platform
binary review `42444450521`, verified the SHA256SUMS and actual pinned
Git tree and rehashed **all 11 notice contents** as original Git blobs.

The actual reviewer-only GitHub Actions artifact
`AnythingPlays-3.0.0-PARALLEL-N64-SOURCE-LICENSES-UNAPPROVED`
(artifact ID `13606623497`) was downloaded and independently checked:
it contains exactly **two files**, the unapproved report JSON and
SHA256SUMS.txt; the report's SHA-256 matched the checksum file.
The machine-generated evidence verifies **0 Gitlinks, empty real
`.gitmodules`, 11 notice SHA256 values and the four original core
SHA256 identities**, while these source/rights flags remain explicitly
**false**: binary-to-source correspondence, compiled notice selection,
GPL/cross-license review, public distribution and production release.

This clears only the previously inaccurate statement that additional
N64 Git submodule archives needed to be retrieved. It does **not**
allow the in-process GPL/noncommercial bundle to be published, declare
the nightly binary reproduced from this source, or substitute automated
tests for physical user gameplay/saving/long-run evidence.
