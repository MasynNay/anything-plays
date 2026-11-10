# Anything Plays — Technical documentation

This directory holds the engineering, packaging, source, and test details behind [Anything Plays](../README.md). The root README is the public project introduction; the [roadmap](../ROADMAP.md) describes milestones and priorities.

## Start here

| Topic | Document |
| --- | --- |
| How the application works | [Architecture](ARCHITECTURE.md) |
| Building and validating releases | [CI workflows](V3_CI_WORKFLOWS.md) |
| Contributing and local tests | [Contributing](../CONTRIBUTING.md) |
| Security and responsible reporting | [Security policy](../SECURITY.md) |
| Current 3.0 original-source and binary audit | [Exact 11-core source assessment](V3_0_EXACT_RUNTIME_LICENSE_SCOPE.md) |
| Source-first distribution assessment | [3.0 source and release notes](V3_0_SOURCE_FIRST_RELEASE_DECISION.md) |
| Licensing and attribution | [Third-party notices](THIRD_PARTY_NOTICES.md) |

## Release and quality records

| Topic | Document |
| --- | --- |
| Release structure | [Versioned packages](V3_RELEASE_STRUCTURE.md) |
| Production preparation | [Publication runbook](V3_PUBLICATION_RUNBOOK.md) |
| Hardware and gameplay testing | [QA checklist](QA_CHECKLIST.md) |
| Physical-device test procedures | [3.0 QA runbook](V3_PHYSICAL_QA_RUNBOOK.md) |
| Known distribution constraints | [Distribution readiness](V3_DISTRIBUTION_READINESS.md) |
| Native source and licensing investigations | [Compatibility research](V3_LICENSE_COMPATIBILITY_GATE.md) |
| Full development recovery record | [CONTINUE_HERE.md](development/CONTINUE_HERE.md) |

The old Stella2014, Snes9x, Genesis Plus GX, and early ten-source experiments are retained as **historical research**, not the selected 3.0 native lineup. The current build selects eleven pinned original-source cores, including Tia and Dolphin. Consult [the current audit](V3_0_EXACT_RUNTIME_LICENSE_SCOPE.md) rather than inferring present-day release status from an old experiment.

## Development references

The complete [workflow catalog](../.github/README.md), [requirements](../requirements.txt), [packaging scripts](../packaging), [source-oriented tools](../tools), and [tests](../tests) are in the repository. Generated build output, commercial ROMs and proprietary console firmware must not be committed.

For the latest publicly downloadable version, use [GitHub Releases](https://github.com/MasynNay/anything-plays/releases/latest). A workflow's green checks and a private release draft are not equivalent to a published release.
