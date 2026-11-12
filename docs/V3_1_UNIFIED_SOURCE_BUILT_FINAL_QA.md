# Anything Plays 3.1.0 — Unified source-built camera-only final QA

**Verified November 11/12, 2026. Technical verification complete; public stable
release NOT authorized.**

This document supersedes **only the technical build-status** portions of
earlier 3.1 release handoffs. It is not a legal opinion, source/relinking
certification, physical gamepad/camera acceptance or permission to publish.

## One exact source tree, all four full installers

[GitHub Actions run 43140637755](https://github.com/MasynNay/anything-plays/actions/runs/43140637755)
completed **13/13 native jobs successfully** for the **exact PR head source SHA**
`104b96621ec4cb8dc39fde8c3fe96fc854c406ed`
([PR #219](https://github.com/MasynNay/anything-plays/pull/219), squash-merged
as `b1f63f1b60c33e4c126f27d146ab14b92ec28179`).

| OS | Genuine 3.1.0 final installer inside private run | Original-source 11 cores / 18 profiles | Installed frozen Tk + Stream Mode + settings QA |
| --- | --- | --- | --- |
| Linux x64 | `AnythingPlays-3.1.0-FINAL-FULL-18-linux-x64-QA-ONLY` | PASS | PASS |
| Windows x64 | `AnythingPlays-3.1.0-FINAL-FULL-18-windows-x64-QA-ONLY` | PASS | PASS |
| Apple Silicon | `AnythingPlays-3.1.0-FINAL-FULL-18-macos-arm64-QA-ONLY` | PASS | PASS |
| Intel Mac | `AnythingPlays-3.1.0-FINAL-FULL-18-macos-x64-QA-ONLY` | PASS | PASS |

Each platform also has a corresponding `AnythingPlays-3.1.0-FINAL-IDENTITY-{target}-QA-ONLY`
source-stage artifact and `AnythingPlays-3.1.0-FINAL-INSTALLED-DESKTOP-{target}-QA-ONLY`
installed-app evidence artifact. **Use the artifact's original source, size,
installer SHA-256, native source-wheel receipt and full-core receipt; do not
assume matching installer filenames imply matching bytes.** These artifacts
are private, time-limited QA outputs, not assets of a published release.

### Camera-only native source provenance

The four independent original OpenCV source-wheel jobs were completed before
they were used in the unified final run. All verify the pristine OpenCV
`opencv-python-headless==4.14.0.94` source archive at SHA-256
`4afa2ea1214453648be88259f035712454faa9039b686de7753569ba8eec1577`.
They compile native camera backends with `WITH_FFMPEG=OFF`, then inspect the
source-built wheel and import it on its actual OS:

| Platform | Independent native source-wheel proof | Native camera backend |
| --- | --- | --- |
| Linux | [43133383864](https://github.com/MasynNay/anything-plays/actions/runs/43133383864) | V4L2 |
| Windows | [43138596964](https://github.com/MasynNay/anything-plays/actions/runs/43138596964) | DirectShow; published 2.0 Windows packaging source patch separately SHA-verified |
| Apple Silicon | [43137079614](https://github.com/MasynNay/anything-plays/actions/runs/43137079614) | AVFoundation; optional AVIF disabled |
| Intel Mac | [43137079614](https://github.com/MasynNay/anything-plays/actions/runs/43137079614) | AVFoundation; optional AVIF disabled |

**This is evidence of compiled backends and running frozen GUI, not video
capture using an actual webcam.** The 11 emulator core families derive from
the original SHA-checked public 3.0 source-built packages; this does not
resolve every original core license or full native corresponding-source
obligation.

### Additional cross-checks that passed

- Earlier independently source-rebuilt full installer and actual desktop
  acceptance: Linux [43136053895](https://github.com/MasynNay/anything-plays/actions/runs/43136053895),
  Windows [43140465834](https://github.com/MasynNay/anything-plays/actions/runs/43140465834),
  Apple Silicon [43138729334](https://github.com/MasynNay/anything-plays/actions/runs/43138729334),
  Intel Mac [43140319401](https://github.com/MasynNay/anything-plays/actions/runs/43140319401).
  The independent runs used **different PR source SHAs**; the unified run
  above fixes that source consistency issue.
- [PR #216](https://github.com/MasynNay/anything-plays/pull/216),
  [native notice audit 43141091687](https://github.com/MasynNay/anything-plays/actions/runs/43141091687):
  authentic new clean Linux and Apple Silicon full-installer native/notice
  inventories passed. **Native inventory is not licensing or redistribution
  approval.**
- Source tests on Python 3.12 and 3.13 and native mGBA tests passed against the
  PR head. 3.1.0 identity remains separate from public 3.0/RC1/RC2 data.

## GitHub Release truth: keep the two different source families separate

**Existing private `v3.1.0` draft**: release ID `442346875`, seven
original assets, built from **old stock-OpenCV source SHA**
`d852de9a513f83a329c14647ddc86bf3690fb5f5`, with original QA
[43120583726](https://github.com/MasynNay/anything-plays/actions/runs/43120583726).
This draft is deliberately **unchanged**. Do not overwrite or publish it
using the **new** clean-wheel evidence. The initial public 3.1 RC2 and
stable 3.0/2.0 remain unchanged.

**New source-built camera-only full installers**: source SHA
`104b96621ec4cb8dc39fde8c3fe96fc854c406ed`, private QA run
`43140637755` with fresh source receipts and **four different installer
byte hashes**. The new source and original draft assets must not share a
manifest or be silently interchanged. If approved later, produce a separate
verified seven-asset four-installer private staging bundle and an accurate
SHA256SUMS/source-and-notices manifest from these **new** exact bytes before
changing the draft/public release.

## Four remaining required gates

`config/v3.1-release-readiness.json` must continue to show
`public_release_approved: false`. Its four independent open gates are:

1. Actual physical camera/gamepad acceptance and representative gameplay,
   audio, saves and longer sessions (the owner's earlier Linux RC2 launch and
   positive GUI report do **not** prove these).
2. Complete independent pygame/SDL and native wheel license/redistribution
   review. Merely replacing old FFmpeg-bearing OpenCV removes one candidate
   class, not all third-party obligations.
3. Exact corresponding source, modifications, notices, user rebuild and
   native relinking/replacement process covering the actually distributed
   final OS packages and relevant licenses, with independent review.
4. Final notes, new-source receipt + checksum staging, deliberate owner
   approval, controlled public release and portfolio rollout.

Until all are documented and approved, stable **v3.1.0 is NOT published**.
Avoid rerunning the completed 13-job matrix just to refresh a document. The
repository and temporary Actions artifacts are the definitive evidence.
