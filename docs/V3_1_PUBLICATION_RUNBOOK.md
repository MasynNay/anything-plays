# Anything Plays 3.1.0 — Publication runbook

**State (November 11, 2026): PREPARED, NOT AUTHORIZED OR PUBLISHED.**
This is the release operator's ordered checklist. The goal is one genuine stable
`v3.1.0` GitHub Release with four already-built, version-correct full
installers, the exact source and notices, integrity checks and a working
portfolio link. This file does **not** approve third-party redistribution.

## Current clean four-platform candidate supersedes the older stock-OpenCV draft

The latest technical candidate is [the exact same-source 13/13 native QA
run 43140637755](https://github.com/MasynNay/anything-plays/actions/runs/43140637755):
four source builds, four full eleven-core/18-profile installers, four actual
installed desktop/DS Stream Mode checks and a settings/receipt contract.
Its source SHA is `104b96621ec4cb8dc39fde8c3fe96fc854c406ed`.
Every native package used source-built, FFmpeg-disabled OpenCV, with its
original upstream source SHA and platform-specific wheel fingerprint
preserved as described in [OpenCV source reproduction and distribution
materials](V3_1_CLEAN_OPENCV_SOURCE_REPRODUCTION.md).

A [new source-provenance-matched private bundle
43142249044](https://github.com/MasynNay/anything-plays/actions/runs/43142249044)
passed all four SHA256/installed-app/core/source-wheel receipt checks and
retains the **new four installers** as
`AnythingPlays-3.1.0-FOUR-CLEAN-FULL-18-SOURCE-VERIFIED-PRIVATE-REVIEW`.
This is an expiring private artifact, not a published release.
The **existing owner-only seven-asset GitHub draft** ID `442346875`
still contains the older **stock OpenCV** installer bytes and checksums.
Do not upload a new candidate over it or publish that draft until the
owner has completed independent licensing/source/relinking and physical
device acceptance, confirmed matching source and notices, and reviewed
the exact new checksums after any draft replacement.

**The older 43120583726 evidence below applies to the historical
stock-OpenCV private draft only.** It is preserved for provenance and
must not be confused with the new clean source-built candidate.

## Verified technical inputs

| Check | Exact evidence | State |
| --- | --- | --- |
| Windows and Linux and both Mac source identity builds | [Actions 43120583726](https://github.com/MasynNay/anything-plays/actions/runs/43120583726) | PASS 4/4 |
| All 11 original-source cores, 18 console profiles, four assembled installers | Same exact-source Actions run | PASS 4/4 |
| Four installed frozen desktop / Stream Mode / settings migration suites | Same run | PASS 4/4 |
| Python 3.12 and 3.13 plus cross-platform packages | [Actions 43120583722](https://github.com/MasynNay/anything-plays/actions/runs/43120583722) | PASS |
| Private SHA-256-verified four-installer bundle | [Actions 43123263034](https://github.com/MasynNay/anything-plays/actions/runs/43123263034) | PASS, not public |
| Stable 3.1.0 distribution permission | [Release-readiness gates](../config/v3.1-release-readiness.json) | **NOT YET APPROVED** |

**Source revision embedded in the four installer receipts:** 
`d852de9a513f83a329c14647ddc86bf3690fb5f5`.
That was merged by [PR #199](https://github.com/MasynNay/anything-plays/pull/199)
as `2b1567e86cb305a7bd10fc76c494d81b39aa77bd`.
Do **not** rebuild from some unrelated moving main commit, reuse RC2 binary
content, or claim the newer docs-only commits are the build source revision.

Private staging run 43123263034 retained artifact
`AnythingPlays-3.1.0-FINAL-FOUR-FULL-INSTALLERS-PRIVATE-REVIEW` with:

- `AnythingPlaysSetup-3.1.0.exe`
- `anything-plays-31_3.1.0_amd64.deb`
- `AnythingPlays-3.1.0-macos-arm64.dmg`
- `AnythingPlays-3.1.0-macos-x64.dmg`
- `FINAL_QA_MANIFEST.json`, `SHA256SUMS.txt` and `FINAL_SOURCE_ACCESS_REVIEW.md`

The GitHub Actions ZIP is **private review evidence**, not a public release.
Artifacts expire; if it expires, reproduce exact-input native packaging and
installed-acceptance evidence rather than claiming the old file still exists.

## Mandatory release-decision checks

The first two documented gates have supporting evidence. All remaining gates
require their own independent evidence and explicit approval. Do not change a
`false` value to `true` just to make an automated test pass.

1. **Physical controller / user experience.** Test a physical USB or
   Bluetooth pad on a real compatible machine: detect it, map buttons,
   actuate a built-in game, unplug/reconnect, check stuck inputs and
   save/restore. Document OS, controller and known exceptions. The owner
   previously tested RC2 Linux installation and Stream Mode appearance;
   these are *not* controller, camera, OBS recording or real gameplay passes.
2. **Third-party redistribution review.** The exact frozen dependency
   inventory is **now complete** on four OSes ([source-matched audit 43130496526](https://github.com/MasynNay/anything-plays/actions/runs/43130496526)),
   as is the public 3.0 versus private 3.1 OpenCV byte comparison
   ([43131176213](https://github.com/MasynNay/anything-plays/actions/runs/43131176213)).
   Both stable 3.0 and final 3.1 carry OpenCV FFmpeg-named native files
   on three OSes; Apple Silicon also includes x264 and x265. Review the
   [exact OpenCV source/codec evidence](V3_1_OPENCV_EXACT_RUNTIME_REVIEW.md),
   preserve the actual pygame-ce/SDL/OpenCV and transitive dependency
   notices and copyright texts;
   compare observed binary build flags and exact source to uploaded source
   archives. Pay special attention to pygame-ce 2.5.8 LGPL obligations and
   macOS OpenCV/pygame SDL2 2.32.8/2.32.10 duplication. Technical code-section
   matches and one modified `pygame.base` swap are **not** complete review.
3. **Corresponding source and user replacement path.** Publish or explicitly
   make available matching upstream+modified source, permitted build flags,
   notices and replacement instructions for all license-covered shipped
   libraries and their applicable dependencies; review whether modified
   bundled code and frozen/native linking satisfy applicable obligations.
   The separate [3.0 source companion](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources)
   and [3.1 source companion research](V3_1_SOURCE_COMPANION.md) are starting
   points, not automatic proof that every 3.1 native file corresponds.
4. **Release notes and rollout.** Independently approve
   [the user-facing 3.1.0 release notes](V3_1_RELEASE_DRAFT_NOTES.md),
   verify exact version strings, known limitations, destination links and
   that the website will be updated **only after** a successful public GitHub
   release. Keep a written rollback protocol and post-publish checks.

Use `python -m tools.check_v31_release` before considering public
publication. This must fail while any required evidence/approval remains open.
It does **not** replace independent license analysis.

## Reconfirm exact installer bytes before upload

On a trusted maintainer environment with GitHub CLI authenticated, obtain
the private bundle **after** confirming Actions run 43123263034 really
concluded `success`:

```bash
mkdir -p /tmp/anything-plays-31-review
cd /tmp/anything-plays-31-review
gh run download 43123263034 \
  --repo MasynNay/anything-plays \
  --name AnythingPlays-3.1.0-FINAL-FOUR-FULL-INSTALLERS-PRIVATE-REVIEW
sha256sum --check SHA256SUMS.txt
python - <<'PY'
import json
from pathlib import Path
m=json.loads(Path("FINAL_QA_MANIFEST.json").read_text("utf-8"))
assert m["schema_version"] == 1
assert m["source_revision"] == "d852de9a513f83a329c14647ddc86bf3690fb5f5"
assert m["qa_run_id"] == 43120583726
assert len(m["installers"]) == 4
assert m["actual_installed_gui_verified_on_four_platforms"] is True
assert m["stable_3_1_0_published"] is False
assert m["public_release_approved"] is False
assert set(m["installers"]) == {"windows-x64","linux-x64","macos-arm64","macos-x64"}
for platform, info in m["installers"].items():
    assert Path(info["filename"]).is_file(), platform
print("Exact full 3.1.0 installer inputs validated. Still PRIVATE.")
PY
```

The final published release must retain SHA-256 correspondence with **these
specific bytes**. If any DMG/EXE/DEB is changed or signed after this check,
that new byte stream needs a new receipt, installed-app QA and checksum.

## Publication procedure — ONLY after gates are signed off

1. Record each gate's real GitHub evidence and independent approval in
   `config/v3.1-release-readiness.json`. Complete and review corresponding
   source archives, third-party notices and replacement instructions.
   Ensure `python -m tools.check_v31_release` succeeds against the
   approved manifest.
2. An existing **private** GitHub Release draft already exists for
   `v3.1.0`, with four full installers and three QA files (release ID
   `442346875`, [private owner-only draft](https://github.com/MasynNay/anything-plays/releases/tag/untagged-293d7611aadb2e7f65f3)).
   **Review and update that original draft**, do not create a competing
   second draft or reuse RC2 binary files. At public approval time confirm
   its exact tested source revision and all seven original asset hashes,
   provide nonexpiring corresponding-source/third-party notices and applicable
   replacement information, and reconcile any necessary new assets or rebuilt
   binaries with a new QA receipt. Do not press Publish until every gate is
   supported and explicitly approved.
3. Review the draft asset list and exact SHA-256 **after GitHub upload**;
   GitHub may normalize asset names. Check the release tag's source hash,
   actual owner permissions and checksum file names, then publish stable
   3.1.0 explicitly and verify that its release JSON has `draft=false`,
   `prerelease=false` and each of the four files is downloadable.
4. Test one real download end to end. Confirm `releases/latest` targets
   `v3.1.0`, retain unchanged historical 1.5, 2.0, stable 3.0 and RC1/RC2
   artifacts, and verify links in README and
   https://anythingplays.masynnay.com/ before promoting 3.1 on the site.
5. Record actual publication date, assets, checksums, release URL,
   exact source commit and any platform-specific warnings. Avoid saying
   Apple notarization, physical hardware or complete library relink testing
   succeeded unless there is separate specific evidence.

No release-creation API access or permission should be assumed. If the
GitHub app's integration token returns `Resource not accessible by
integration`, leave the verified draft/artifacts intact and use an
appropriately authenticated maintainer account; never fabricate a release
or move a tag without the proper release privilege.

## Abort / rollback

- If any source, checksum, notice or platform artifact differs, **do not
  publish**. Keep the private stage for diagnosis.
- If a public release is created in error, stop site/README promotion,
  disclose the affected asset, correct the distribution and repeat
  verification before publishing a replacement. Avoid silently rewriting
  the existing tag or deleting historical releases.
- Stable 3.0 and the original public 3.1 RC2 packages remain available
  while remediation occurs.
- For any real device regression, capture OS/app version, controller or
  camera type, console/core, anonymized steps and reproducible evidence.
  Never collect or upload privately owned ROMs or unredacted camera footage.
