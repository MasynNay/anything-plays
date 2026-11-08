# CONTINUE HERE — Anything Plays 3.0 public release

Last verified November 7, 2026. This is the durable handoff/checkpoint if a conversation or tool stream fails. Do not reset 3.0 work or re-add emulators.

## Product decision (frozen)

- **No new emulator/core/console integration in 3.0.** Supported test inventory stays **18 console profiles and 11 native Libretro cores**. No Wii.
- User confirmed Linux GameCube/Dolphin works on their machine, after the writable Sys fix. Their last screenshot exposed **oversized camera control labels**; label fix now merged.
- User wants a public version **3.0.0** first; only after that, announce/publish the *future* versioned roadmap. Do **not** prepublish a new 3.1–4.0 roadmap.
- Preserve the original artwork, theme support and all existing emulator functionality; keep stable v2.0.0 untouched.

## Verified complete work

1. PR [#31](https://github.com/MasynNay/anything-plays/pull/31) merged into `feature/v3.0-unified-test` (squash commit `43cc14b572b039b0d0074fa4726ed4d65ffd764b`). Restored camera-left label-size slider, reset button, per-console persisted size, and fit-to-zone render constraint; added regression test.
2. The **complete** four-platform offline installer lab passed on the slider-fix commit: [workflow 42426209611](https://github.com/MasynNay/anything-plays/actions/runs/42426209611). Windows x64, macOS arm64, macOS x64 and Linux x64 all passed. Linux job includes unprivileged installed-app startup and readonly-Dolphin GameCube native smoke.
3. Source checks succeeded on the PR commit (and preceding development commit).
4. PR [#32](https://github.com/MasynNay/anything-plays/pull/32) merged (squash commit `21557ddf3f7af73cd8966e4da2645c18088cf685`) with [3.0 distribution evidence audit](docs/V3_DISTRIBUTION_READINESS.md), [draft 3.0 release notes](docs/V3_RELEASE_NOTES_DRAFT.md), and README links. The future version-number roadmap was intentionally **not** announced.
5. Linux hardware follow-up recorded in [issue #25](https://github.com/MasynNay/anything-plays/issues/25). Stable public download remains [v2.0.0](https://github.com/MasynNay/anything-plays/releases/tag/v2.0.0).

## Additional confirmed work — November 7/8 (latest)

6. [PR #33](https://github.com/MasynNay/anything-plays/pull/33) merged (commit `17fb5e3bada6edb8ab83d48587a868049c97d0ed`) to repair stale CI build paths (`packaging/`), Mac bundle inventory path, all-core release-branch verification and rebuild triggers. Source checks passed. The corrected `release/v3` package checks were exercised by [run 42432700011](https://github.com/MasynNay/anything-plays/actions/runs/42432700011): **all seven jobs passed** (Windows, Linux, both Macs, Python 3.12/3.13, native mGBA).
7. Downloaded and independently SHA-256 verified all four full test installers from [run 42426209611](https://github.com/MasynNay/anything-plays/actions/runs/42426209611). Unpacked Linux DEB: all **11** core binary SHA and byte sizes matched `CORE_PROVENANCE.json`, Dolphin Sys present. Ten short reported revisions resolved to exact 40-character Git commits; Beetle PCE Fast lacked a reported revision. The **test-only** candidate evidence was merged in [PR #34](https://github.com/MasynNay/anything-plays/pull/34) (commit `3dc7c772fc5d5251555f890ba3e3fd0c796c6045`), in `config/v3.0-preview-candidate-integrity.json`. All four artifacts are marked **not approved for public release**.
8. [PR #35](https://github.com/MasynNay/anything-plays/pull/35) merged (commit `dd622b388cbc03fcc90250fa2f5c3f855cd8f530`) five additional verbatim upstream GPLv2 notice files into `licenses/` (ProSystem, NeoPop, WonderSwan, Stella 2014, Beetle PCE Fast). Four tie to resolved source commits; PCE is explicitly provisional because the core does not report a revision. Source checks passed on final PR head. Full installer rebuild now watches license/notice changes.

**Remaining high-priority blocker:** The 3.0-specific complete binary/source license and compatible distribution review is **not complete**, particularly ParaLLEl-N64 components, Dolphin license/source dependencies, PCE source correspondence, the complete third-party native dependency and system-file inventories, plus real hardware test matrix. `tools/check_v30_release.py` must pass unmodified; do not rewrite flags without real evidence. No final stable 3.0 tag/release exists yet. Future versioned roadmap remains unannounced.

## PUBLIC 3.0 IS NOT YET PUBLISHED — true blockers

- [3.0 release issue #28](https://github.com/MasynNay/anything-plays/issues/28) remains open for per-core license/source/redistribution and architecture-by-architecture official binary approval, and end-to-end real-device acceptance.
- `config/v3.0-release-acceptance.json` still has numerous intentionally false per-console/per-platform/rights statuses. Never manufacture true values to enable publication.
- Full **test-only** installers are built from `AP_RELEASE_BUILD=0`, `AP_V30_TEST_CORES=1`, optionally changing Libretro `latest` native inputs. No immutable reviewed eleven-core release lock / source inventory yet. Prior v2.0 approval applies only to the older exact binaries.
- `tools/check_v30_release.py` must pass **without** `--report-only` after documented review; latest full bundle intentionally uses report-only and is NOT a release authorization.
- Need exact four immutable production installers, corresponding license/source notices and hashes, cross-platform QA evidence, packaging inspection, signed/notarized limitations, final manual release approval.
- The currently available connected GitHub tool set has branch/file/PR issue writes and GitHub Actions reads, **but no release-create/publish or workflow-dispatch action**. Do not claim any GitHub release was published without actually checking releases. The one-time publish mechanism may need an intentionally gated GitHub Actions workflow and owner-approved trigger if tool capabilities do not change.

## Next practical actions

1. Complete eleven-core third-party licenses and provenance, including Snes9x noncommercial conditions and GPL/LGPL dependencies and exact Dolphin Sys assets; preserve source snapshots and notices.
2. Make an immutable archive for 3.0 on four targets (not nightly fetch at release time) and verify final installed hashes. Keep source/technical files accessible without cluttering the four main downloads.
3. Finish real device matrix and long-run checks, especially GameCube, plus actual game audio/input/save evidence.
4. Set evidence-backed release gate flags, ensure `python tools/check_v30_release.py` succeeds, and run final 3.0 candidate builds.
5. Publicly publish four verified installers plus `SHA256SUMS.txt` and required source/license access documentation. Update README/main and website to stable 3.0.
6. **Only after successful public 3.0:** publish the proposed forward roadmap, with version labels treated as tentative.

## Safety

- Do not delete stable 2.0 or replace main downloads with unapproved 3.0 binaries.
- Do not distribute copyrighted game ROMs or BIOS.
- Do not call developer-test CI success a blanket emulator compatibility certification or third-party redistribution authorization.
