# 3.0 stable publication — controlled runbook

**Current status: NOT YET APPROVED.** This describes the exact publication process
after **all** independent source, license and hardware checks have been reviewed.
It does not authorize redistribution or turn preview ZIPs into production releases.

## Two distinct classes of builds

- **Developer preview**: the four-platform full-offline lab runs with
  `AP_RELEASE_BUILD=0` and 11 cores acquired from Libretro buildbot or preserved
  test snapshots. Artifacts are explicitly named `FULL-TEST-ONLY` and
  `NATIVE-INPUTS-UNAPPROVED`. They MUST NOT be publicly published.
- **Approved production candidate**: a separate, reviewed four-platform build
  based on immutable, approved native archives and matching corresponding
  source. Every platform installer must identify the exact source commit,
  independent license approval record, full 11-core lock, and source inventory.
  The existing 2-core `v2.0-core-lock.json` is not valid for 3.0.

## Publication inputs that must exist

The manual `.github/workflows/v30-publish-approved.yml` workflow downloads
**only** these four GitHub Actions artifacts from a successful
`Anything Plays 3.0 | Approved production candidates` workflow on the
**same reviewed `main` Git commit**:

- `AnythingPlays-3.0.0-PRODUCTION-windows-x64`
- `AnythingPlays-3.0.0-PRODUCTION-macos-arm64`
- `AnythingPlays-3.0.0-PRODUCTION-macos-x64`
- `AnythingPlays-3.0.0-PRODUCTION-linux-x64`

Each artifact must contain **exactly** its platform's canonically named
installer and a `PRODUCTION_PROVENANCE.json` containing the source commit,
installer SHA-256, approved immutable lock SHA-256, corresponding source
inventory SHA-256, release-mode designation, target, 18 profiles, 11 cores
and linked licensing review. No unexpected assets are accepted. The
`tools/collect_v30_production_assets.py` script verifies all four before
copying. The `tools/stage_v30_release_assets.py` stage then creates the
**exactly five** public-facing files:

```text
AnythingPlaysSetup-3.0.0.exe
AnythingPlays-3.0.0-macos-arm64.dmg
AnythingPlays-3.0.0-macos-x64.dmg
anything-plays_3.0.0_amd64.deb
SHA256SUMS.txt
```

This is the final **download organization**; required GPL corresponding source
must remain clearly linked and provided separately as the applicable licenses
require. Keeping a clean release page does **not** excuse source-distribution
obligations.

## Current technical release-input mismatch (November 8, 2026)

The full [ten-source desktop integration](https://github.com/MasynNay/anything-plays/actions/runs/42535823260) passed all four OS targets and preserved every one of the 18 profiles/11 native core families. It replaces historical buildbot mGBA and ParaLLEl-N64 binaries with new pinned original-source builds. **Dolphin remains an original archived binary**. This is engineering evidence, not redistribution approval.

**Do not release using the old eight-source production composition by accident.** The current `.github/workflows/v30-production-candidates.yml` and `tools/stage_v30_approved_source_inputs.py` still select eight original source-built families and preserve original buildbot `mgba`, `parallel_n64` and `dolphin` as the three unchanged families. Before selecting final production inputs, the engineering team must either (a) update the approved production path to validate the already demonstrated original-source mGBA and N64 artifacts as well, plus every notice/source hash in the 44-core lock, or (b) independently document why the *different* old binaries qualify as completely corresponding-source/rights-reviewed. Never treat a passing **ten-source trial** as proof that a different eight-source production binary was reviewed.

Existing owner reports of working N64 games and Dolphin/GameCube on Windows, macOS and Linux are preserved in the roadmap and acceptance notes. They are not an outstanding request to repeat gameplay; final production hash/release-mode identity and physical checks not observed before remain separately tracked.

## Blocking checklist

- [ ] Resolve third-party redistribution compatibility, including noncommercial
  Snes9x/Genesis Plus GX cores loaded in-process with GPL-family cores.
  The [assessment](V3_LICENSE_COMPATIBILITY_GATE.md) identifies the issue but
  does not settle it.
- [ ] Preserve, review, and link complete corresponding source for exact 3.0
  native binaries, bundled Sys data and relevant dependencies.
- [ ] Create and independently approve the immutable **11-core 3.0** lock.
  Distinguish published source rights and immutable test inputs.
- [ ] Complete and document the required **real hardware** and audio/video/input/
  save/endurance matrix; the source-built [NGP monochrome audio blocker #41](https://github.com/MasynNay/anything-plays/issues/41)
  is already technically closed after all four architectures passed native CI.
  Use the [offline physical QA evidence recorder](V3_PHYSICAL_QA_RUNBOOK.md)
  for actual installed gameplay and save/reload tests. CI homebrew success is not physical QA.
- [ ] Record signing/notarization limitations and complete a clean installation
  using the exact intended production installers.
- [ ] Only with evidence-backed values, make
  `python tools/check_v30_release.py` pass **without --report-only**.
- [ ] Prepare `docs/V3_RELEASE_NOTES_APPROVED.md` without draft warnings and
  with exact installer source links and known limitations.
- [ ] Merge the reviewed release source into `main`.
- [ ] Run the approved production-candidate build on that exact main commit,
  and verify four signed/unsigned-as-disclosed installer SHA-256 values.
- [ ] Manually dispatch the **Approved stable publication** workflow from
  `main`; specify the production run ID, stable version, the literal
  confirmation `APPROVED-3.0-DISTRIBUTION`, and explicit publication intent.

The workflow first performs the strict release gate, checks the candidate run's
source SHA and workflow identity, rejects previews and unknown directories,
checks file checksums, and prepares the public five-file release. It creates
a **draft** first and sets it public only if the operator deliberately selects
`publish_publicly`. The `stable-v3-publication` GitHub Actions environment
may additionally require repository-owner approval; configure reviewers in
GitHub environment settings before final launch.

**The publisher is intentionally unable to run successfully today**:
the 11-core approved production input set and rights/QA evidence do not yet
exist. Do not bypass this by renaming previews or flipping flags to force CI.

## After the real public 3.0 release

Only after GitHub confirms the public `v3.0.0` release and verified installer
hashes, update the stable README/site and publish the **future** roadmap. Leave
public v2.0 and its tags unchanged throughout the transition.
