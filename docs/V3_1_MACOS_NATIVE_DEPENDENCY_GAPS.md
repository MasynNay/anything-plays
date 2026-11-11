# Anything Plays 3.1 — Original macOS native dependency gaps

**Status: independent read-only QA review, not stable release acceptance.**

The signed 18-console macOS RC1 bundles contain many pygame/SDL native
libraries. The existing [native linkage inspection](../.github/workflows/v31-macos-native-linkage-review.yml)
records each candidate's SHA-256, otool-linked library names, architecture and
signature. This follow-up combines both architecture reports into an
actionable list of unresolved dependency names rather than treating an
official wheel code match or one successful extension swap as complete LGPL
correspondence.

## Inputs and reproducibility

The exact previously successful dual-Mac installed inspection is
[Actions run 42906227613](https://github.com/MasynNay/anything-plays/actions/runs/42906227613),
pinned to revision 01123565029f1397cbd472538b95d8f8173a2a97.

Download its two artifacts:

- AnythingPlays-3.1-RC1-MACOS-arm64-SDL-LINKAGE-REVIEW-UNAPPROVED
  containing MACOS_NATIVE_LINKAGE_arm64.json
- AnythingPlays-3.1-RC1-MACOS-x64-SDL-LINKAGE-REVIEW-UNAPPROVED
  containing MACOS_NATIVE_LINKAGE_x64.json

From the repository root, run:

    python -m tools.report_v31_macos_native_dependency_gaps \
      --arm-report input/arm/MACOS_NATIVE_LINKAGE_arm64.json \
      --intel-report input/intel/MACOS_NATIVE_LINKAGE_x64.json \
      --output review/MACOS_NATIVE_DEPENDENCY_GAPS_UNAPPROVED.json

    python -m unittest discover -s tests \
      -p 'test_v31_macos_native_dependency_gaps.py' -v

The [separate read-only workflow](../.github/workflows/v31-macos-native-dependency-gaps.yml)
performs the same steps against both immutable original QA artifacts and
retains the resulting JSON temporarily. It does not rebuild installers,
modify signed DMGs, grant redistribution rights or publish releases.

## Review classifications

- observed_system_library_path: the recorded name explicitly starts with
  a macOS system location; this is only a path observation.
- audited_basename_match_only: the dependency basename appears in the
  inspected library subset with one unique hash. This is not proof of
  which binary dyld loads, a compile-source match or a license conclusion.
- ambiguous_same_basename_different_binaries: a dependency basename
  appears with multiple different binary hashes. Review loader paths.
- not_found_in_audited_native_subset: the referenced library was not
  included among the pygame/SDL files originally inventoried; not
  necessarily absent from the complete app. Examine the wider bundle.
- external_absolute_path_requires_review: a recorded non-system absolute
  location that needs manual inspection.

This report intentionally fails closed on altered 3.1 source identity,
incorrect target architecture, duplicate or unsafe native paths, malformed
SHA-256, missing otool inspection, incorrect inventory counts or any attempt
to mark licensing or release permission approved in the source report.

## What this work does and does not settle

This gives maintainers an auditable dependency checklist and repeatable
tests for ambiguity and omissions in actual signed-bundle evidence. It
does not resolve rpath/loader_path against the signed app, inventory every
other native file, verify original corresponding source and compiler flags
for all native libraries, supply complete end-user rebuild/replacement
instructions, or determine applicable LGPL obligations.

Next: resolve actual dyld runtime paths on both Mac architectures, extend
the inventory to transitive libraries including codecs, collect exact source
and notice material, verify user-rebuilt library substitution where
applicable, and independently complete the physical controller/camera/game
acceptance and stable installer checks. All six
[3.1.0 release gates](../config/v3.1-release-readiness.json) remain
unapproved. [Public RC1](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc1)
and stable [3.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0)
remain unchanged.
