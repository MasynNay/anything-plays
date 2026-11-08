# Anything Plays documentation

This directory is the index for technical and release evidence. The [repository README](../README.md) is the public product overview.

## Start here

| Purpose | Document |
| --- | --- |
| Source code architecture | [Architecture](ARCHITECTURE.md) |
| CI and operating-system test workflows | [Workflow guide](V3_CI_WORKFLOWS.md) |
| Real-device and emulator QA | [QA checklist](QA_CHECKLIST.md) |
| Packaging policy | [Release structure](V3_RELEASE_STRUCTURE.md) |
| Third-party component attribution | [Notices](THIRD_PARTY_NOTICES.md) |
| Release dependencies | [Third-party components](THIRD_PARTY_COMPONENTS.md) |

## Version 3.0 release records

| Purpose | Document |
| --- | --- |
| Outstanding native source/rights checks | [Distribution review](V3_DISTRIBUTION_READINESS.md) |
| GPL and noncommercial license question | [Compatibility assessment](V3_LICENSE_COMPATIBILITY_GATE.md) |
| Draft release text (not published) | [3.0 release notes](V3_RELEASE_NOTES_DRAFT.md) |
| Neo Geo Pocket test ROM license evidence | [NGP test license](V3_NGP_TEST_LICENSE.md) |
| Exact recovery checkpoint | [CONTINUE_HERE.md](../CONTINUE_HERE.md) |
| Release acceptance flags and evidence | [Acceptance data](../config/v3.0-release-acceptance.json) |
| Controlled stable-release publication | [3.0 publication runbook](V3_PUBLICATION_RUNBOOK.md) |

The complete offline **3.0 preview** has passed four-platform packaging checks. It is not yet an approved public binary release. The [current stable release is 2.0](https://github.com/MasynNay/anything-plays/releases/tag/v2.0.0).

## Archives and continuity

Historical 2.0 release evidence includes [RC6 verification](RC6_VERIFICATION.md), the [distribution review](RELEASE_DISTRIBUTION_REVIEW.md) and [source access](RELEASE_SOURCE_ACCESS.md). Older superseded notes live in [history](history/README.md). Preserve development and audit records rather than deleting them to reduce file counts.

The original source is organized under [anything_plays](../anything_plays/), with narrowly scoped root entry points for application boot, native core downloads and installer verification. [packaging](../packaging/) contains platform installers; [tools](../tools/) contains diagnostics; [tests](../tests/) holds regression coverage.

Run **python tools/check_repository_hygiene.py** to verify that the Git index does not contain builds, downloaded emulators, proprietary ROMs or unexpected loose root files. Pull-request CI runs the same check.

The future versioned roadmap will be published only after public 3.0, not before.
