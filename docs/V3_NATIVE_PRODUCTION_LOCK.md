# Immutable native release mode for Anything Plays 3.0

The public 2.0 release uses **two** approved Libretro cores and the existing
[2.0 release lock](../config/v2.0-core-lock.json). Keep it unchanged.

The separate 3.0 **11-core** production input checker is implemented in
[tools/v30_release_lock.py](../tools/v30_release_lock.py) and
[config/v3.0-core-lock.json](../config/v3.0-core-lock.json).
**The checked-in 3.0 lock is deliberately UNAPPROVED**, with no native targets.
It must not be hand-marked ready merely because a CI build passed.

## Exact candidate source

The original four-architecture source ZIP bundle set and a *test-only*
reproducible candidate manifest are available from the [native archive capture
run](https://github.com/MasynNay/anything-plays/actions/runs/42437133733)
and `tools/create_v30_candidate_lock.py`. This manifest carries complete
source archive SHA-256, exact native library SHA-256, size and reported source
identities for **44** libraries and **4** Dolphin Sys ZIPs. It does **not**
approve any copyright or licensing obligations.

Before a production candidate can be built, the release owner and qualified
reviewers must verify the license compatibility/source obligations in
[V3_LICENSE_COMPATIBILITY_GATE.md](V3_LICENSE_COMPATIBILITY_GATE.md),
explicitly review matching sources for all 11 cores (particularly unversioned
Beetle PCE Fast), and complete the platform/real-game QA matrix.

Only after documented review may a PR populate the approved 3.0 lock for all
four target architectures with **source_commit_sha**, complete immutable
hashes, exact source identity, and per-core redistribution/source flags.
The top-level `license_compatibility_reviewed`,
`corresponding_source_inventory_verified` and
`approved_for_binary_distribution` values must remain false until genuine
approval. No automatic tool sets these flags.

## Automated draft corresponding-source review matrix

A manual, research-only GitHub workflow
`.github/workflows/v30-source-review-matrix.yml` now joins the 48 previously
captured original inputs (44 platform-specific libraries + four Dolphin Sys
archives) to the ten preserved upstream Git source tarballs. It rechecks all
original ZIP/native SHA-256 identities and every source tarball SHA-256 and
reported Git revision prefix before producing an **unapproved** four-platform
source-review inventory. It flags the missing Beetle PCE Fast source revision,
Dolphin submodule contents, transitive licenses and binary-to-source mapping
instead of inventing source approval. The output is an Actions artifact,
not a new public release and not the final reviewed
`config/v3.0-corresponding-source-inventory.json`.

Run it from GitHub Actions using the successful
[original native archive run 42437133733](https://github.com/MasynNay/anything-plays/actions/runs/42437133733)
and [source snapshot run 42441448884](https://github.com/MasynNay/anything-plays/actions/runs/42441448884).
The exact generated source-review matrix must be independently examined,
completed with source and license evidence, and reviewed before it can be
proposed for the approved production path. Its automatically produced flags
are deliberately **all false**.

## Source-built PCE Fast integrated preview trial (no release approval)

The separate [four-platform PCE source-build lab](https://github.com/MasynNay/anything-plays/actions/runs/42444367068)
passed authentic native video and nonzero PSG audio on all four targets.
The new pinned-source binary is tied to the original upstream GPL-2.0 Git
commit `2de1ce1c3f237b161c126c54ba407990bb86d1e9`. Windows has a
different Git-source archive SHA-256 because of checkout line endings;
its exact per-target archive identity is recorded separately.

The frozen **unapproved** source-built candidate identity file is
[config/v3.0-pce-pinned-source-candidates.json](../config/v3.0-pce-pinned-source-candidates.json).
[tools/v30_pce_candidate.py](../tools/v30_pce_candidate.py) verifies the
original test artifact's native core bytes, corresponding source archive,
GPL notice, platform magic and real native audio/video report.
[tools/stage_v30_pce_trial_inputs.py](../tools/stage_v30_pce_trial_inputs.py)
checks all **12** original stored ZIPs (11 cores plus Dolphin Sys), retains
**10** unchanged native core ZIPs and unchanged Dolphin Sys, and substitutes
only a new deterministic ZIP containing the source-built PCE binary. Only
unapproved 3.0 preview mode is accepted; it never touches the real 3.0 core
lock, production inputs, or the existing successful preview installers.

The separate four-target workflow
`.github/workflows/v30-pce-offline-integration.yml` builds complete
18-profile, 11-core test previews using those strictly verified local
archives and executes the original HuCard native PSG/video probe against
the newly integrated PCE core. The workflow retains **evidence only**, not
unapproved installer binaries. Approval fields remain false.

**No public GPL/noncommercial mixed-license redistribution approval or full
retail-game/hardware acceptance is implied.** The technical core swap is
evaluated in isolation and may be adopted for a future reviewed release
only after independent evidence and rights decisions.

## Distinct release and development modes

| Mode | Build environment | Effect |
| --- | --- | --- |
| v2.0 historical | `AP_RELEASE_BUILD=1`, no 3.0 flag | Original two-core lock and release rules |
| 3.0 preview | `AP_RELEASE_BUILD=0 AP_V30_TEST_CORES=1` | Unapproved four-platform 11-core test workflow |
| 3.0 approved native input | `AP_RELEASE_BUILD=1 AP_V30_APPROVED_RELEASE=1 AP_CORE_ARCHIVE_DIR=/pinned/platform-inputs` | Eleven cores, original local ZIP checks and exact Dolphin Sys, only after rights approval |

For 3.0 production native mode the downloader verifies the original ZIP SHA
**before extraction**, checks each library SHA **before loading with ctypes**,
and validates the entire staged bundle after copying. Dolphin Sys uses only
reviewed local `Dolphin.zip` and rejects changed bytes; network fallback is
prohibited. Windows, Linux, and Mac build scripts must carry all eleven core
libraries and Dolphin Sys in this mode.

The controlled GitHub workflow `.github/workflows/v30-production-candidates.yml`
now defines the **four-platform approved production artifact producer**. It
requires explicit owner confirmation, a fully reviewed immutable native lock,
`config/v3.0-corresponding-source-inventory.json`, an independently approved
`docs/V3_LICENSE_COMPATIBILITY_APPROVED.md` rights decision, strict QA
acceptance and original matching ZIP archives. These files and approvals
are not yet complete, so the workflow intentionally cannot produce public
approved binaries. It emits exactly one canonical stable installer and one
`PRODUCTION_PROVENANCE.json` per target after rechecking source, lock, bundle
and installer hashes. The separate manual publisher reads these four artifacts.

**Additional production tasks remain:** independent approval and population
of the immutable 11-core lock, corresponding-source inventories (including
submodules and an identifiable PCE Fast source), GPL/noncommercial rights review,
final signing/notarization disclosures, and actual platform/audio/gameplay
acceptance. The Windows/macOS/Linux packaging scripts now have separate stable
production identities alongside unchanged preview mode, and the four-platform
candidate producer exists, but both fail closed until all evidence is reviewed.
The distinct manual [publication runbook](V3_PUBLICATION_RUNBOOK.md) controls
the final release, not these build scripts.
