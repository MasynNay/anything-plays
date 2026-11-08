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

**Additional production tasks remain:** a separately approved immutable 11-core
input lock, final stable OS installer identities (the current scripts still
default to preview branding), a four-platform reviewed production build
workflow, final signing/notarization disclosure and the manual
[publication runbook](V3_PUBLICATION_RUNBOOK.md). These are release gates;
this native preflight does not itself generate or publish a public release.
