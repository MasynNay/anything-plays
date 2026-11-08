# Anything Plays 3.0 — exact corresponding-source reviewer contract

**Status: reviewer template and gate schema only. This document does not
approve a core, a combined GPL/noncommercial binary distribution, or 3.0.**

The approved production path now requires an explicit, independently reviewed
**44-native-binary / four-platform** source inventory. A GitHub commit or a
source tarball cannot prove how an upstream buildbot binary was compiled.
Similarly, including a license file is not permission to redistribute an
in-process combination of components with potentially incompatible terms.

## Independent evidence that must precede the final inventory

For each Windows x64, Linux x64, macOS Apple Silicon and Intel Mac target,
review the **exact eleven native library payload SHA-256 values and their
original distribution ZIP SHA-256 values**, and each target's original Dolphin
Sys ZIP. Inspect the original Git source revision, the corresponding archive
SHA-256 and byte length, submodules and nested dependencies, compiler commands,
patches, build flags, transitive library rights, license notices and any
source-access requirement. The unapproved original candidate and captured
upstream archives can guide this work, but cannot substitute for it.

The existing review tools remain intentionally candid about their evidence:

- `tools/create_v30_candidate_lock.py` captures original library/archive
  identities, not permission to redistribute them.
- `tools/create_v30_source_review_inventory.py` joins 44 actual native
  library hashes to ten upstream reported-source snapshots; Beetle PCE Fast
  lacked a reported revision in the **old** buildbot binary.
- `tools/create_v30_pce_source_review_delta.py` records a newly *source-built*
  PCE candidate for each OS with an identified upstream source revision.
  This is a different binary, so substituting the source of that candidate
  for the old nightly binary is invalid.
- `tools/reconcile_v30_dolphin_source_archives.py` independently verifies
  all 34 original pinned Dolphin Gitlink **source candidates**. It does not
  prove all nested dependencies are complete, how Dolphin was compiled, or
  whether its binary matches those sources.
- `docs/V3_LICENSE_COMPATIBILITY_GATE.md` describes the unresolved
  GPL-family and noncommercial Snes9x/Genesis Plus GX combined-program
  rights question. A non-commercial portfolio distribution is **not**
  automatically granted permission by all licenses.

## Required production records

The final reviewed `config/v3.0-corresponding-source-inventory.json` is
**not yet present**. Do not create it as approved until a reviewer can support
every claim below, including relevant rights-holder authorizations.

All these fields must be explicitly supported by external evidence before
the **approved** `tools/emit_v30_production_provenance.py` accepts them:

| Scope | JSON field | What must be verified |
| --- | --- | --- |
| Entire inventory | `schema_version = 1`, `native_core_count = 11` | Correct frozen review version and all 11 core families |
| Entire inventory | `approved_for_public_binary_distribution = true` | Independent distribution review completed |
| Entire inventory | `corresponding_source_inventory_verified = true` | Corresponding sources and dependencies independently checked |
| Entire inventory | `independent_binary_to_source_match_proven = true` | All 44 native binaries have reviewed source/binary correspondence |
| Entire inventory | `source_commit` | Exactly equals immutable native lock's build-input revision |
| `targets` | All four native target keys | `windows-x86_64`, `linux-x86_64`, `macos-arm64`, `macos-x86_64` |
| Each target/core | `source_commit_sha`, `source_repository` | Exact source identity matching the approved native lock |
| Each target/core | `native_sha256`, `original_native_archive_sha256` | Exact shipped payload and original upstream native ZIP identities |
| Each target/core | `source_archive_sha256`, `source_archive_size_bytes` | Exact archived corresponding-source bytes, positive byte length |
| Each target/core | `source_build_dependencies_reviewed = true` | Complete build inputs, flags, transitive dependencies, notices reviewed |
| Each target/core | `source_to_binary_verified = true` | Independent determination that that source corresponds to that **particular** library |
| Each target/core | `redistribution_license_reviewed = true` | Core-specific license obligations and any necessary permissions reviewed |
| Each target/`dolphin_sys` | Original ZIP SHA-256 and size | Exact reviewed Dolphin system asset archive matches approved lock |
| Each target/`dolphin_sys` | `source_and_license_reviewed`, `source_correspondence_verified`, `redistribution_approved` | All independently true for those assets |
| Outside JSON | `docs/V3_LICENSE_COMPATIBILITY_APPROVED.md` | Independently completed combined-work distribution decision with explicit `APPROVED-3.0-DISTRIBUTION` signoff |
| Outside JSON | `config/v3.0-core-lock.json` | Reviewed 11-core four-platform immutable ZIP/payload/source identities and distribution approvals |
| Outside JSON | `config/v3.0-release-acceptance.json` | Actual real-device game/audio/camera/save/endurance test evidence, not only CI synthetic or source-built homebrew |

A matching SHA **is not itself** an independent correspondence conclusion.
The `source_to_binary_verified` and `redistribution_license_reviewed`
decisions are distinct. An unresolved rights decision or a missing source
archive blocks that specific core and therefore all stable 3.0 installers.

## How the gate works

```bash
# Expected to FAIL on the present development feature branch:
python -m tools.check_v30_source_gate

# The final production workflow invokes this as a strict preflight before
# building any Windows EXE, macOS DMG or Linux DEB.
# The emitter validates the full source record a second time after build.
```

`.github/workflows/v30-production-candidates.yml` requires both this
preflight and the original `tools/check_v30_release.py`, and independently
checks the source binary SHA identities through the production emitter.
The public publishing workflow must still run separately on reviewed
`main`; this gate is **not an automatic legal clearance or an instruction
to invent positive fields**.

## Remaining practical signoffs

The actual external/legal reviewer must resolve the in-process GPL and
noncommercial distribution compatibility, obtain any necessary rights-holder
permissions and verify any corresponding-source offer. The release owner
must obtain real physical four-platform gameplay and camera tests, save
and long-run results, production signing/notarization disclosures and final
versioned release notes. Keep the existing public v2.0 unaffected and
retain the eleven built-in cores and eighteen profiles.
