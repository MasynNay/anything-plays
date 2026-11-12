# Anything Plays 3.1.0 — native dependency distribution review

**Review state: OPEN. This is an evidence index and remediation plan, not legal approval.**
Last updated: November 11/12, 2026. The newest **clean candidate**
has [13 passing exact-source native full/installed QA
jobs](https://github.com/MasynNay/anything-plays/actions/runs/43140637755),
source revision `104b96621ec4cb8dc39fde8c3fe96fc854c406ed`, and a
[private reverified four-installer source provenance
bundle](https://github.com/MasynNay/anything-plays/actions/runs/43142249044).
The original private `v3.1.0` GitHub Release draft still has the
**older stock OpenCV** packages from
`d852de9a513f83a329c14647ddc86bf3690fb5f5`.
Do not combine those older exact installer hashes with the new clean OpenCV
candidate or describe a private bundle as a published stable release.
[Permanent original OpenCV source archive and Windows patch, exact per-OS
build recipe and SHA receipts](V3_1_CLEAN_OPENCV_SOURCE_REPRODUCTION.md).
Native LGPL/source/relinking rights and actual hardware acceptance remain
independent open requirements.

## 1. Exact frozen binaries under review

| Target | Reviewed full installer | Native/installed QA |
| --- | --- | --- |
| Windows x64 | `AnythingPlaysSetup-3.1.0.exe` | [43120583726](https://github.com/MasynNay/anything-plays/actions/runs/43120583726) |
| Linux x64 | `anything-plays-31_3.1.0_amd64.deb` | Same run |
| macOS Intel x64 | `AnythingPlays-3.1.0-macos-x64.dmg` | Same run |
| macOS Apple Silicon | `AnythingPlays-3.1.0-macos-arm64.dmg` | Same run |

The private [staging run 43123263034](https://github.com/MasynNay/anything-plays/actions/runs/43123263034)
checked original full 11-core receipts, all four actual installed GUI receipts,
source SHA, every platform checksum, and preserved one review bundle. [Private
GitHub draft](https://github.com/MasynNay/anything-plays/releases/tag/untagged-293d7611aadb2e7f65f3)
`v3.1.0` contains four tested installers plus `SHA256SUMS.txt`,
`FINAL_QA_MANIFEST.json`, and `FINAL_SOURCE_ACCESS_REVIEW.md`.
**The final draft is not public.**

## 2. Source material and evidence on hand

| Component | Existing artifact/evidence | Still to establish |
| --- | --- | --- |
| Anything Plays MIT source | Exact tested [source tree](https://github.com/MasynNay/anything-plays/tree/d852de9a513f83a329c14647ddc86bf3690fb5f5) and build scripts | Verify the public tag points to this exact source if and when published |
| Eleven Libretro emulator core families | [3.0 original-source release](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources), source-derived stable binary core hashes compared again during 3.1 full packaging | Confirm preserved licenses, source access and any additional component-specific distribution terms alongside 3.1 |
| pygame-ce 2.5.8 | Exact upstream commit `c8200a9eaa530f884a0a4c3384cefc48006e58be`, LGPL-2.1 notice; [six-source candidate review](https://github.com/MasynNay/anything-plays/actions/runs/42909893531) | Complete per-extension and transitive SDL binary-to-source correspondence, redistribution notices and user modification/relink options |
| SDL2, SDL2_image, SDL2_mixer, SDL2_ttf | Tagged candidate source archives and original license texts in retained [source review](https://github.com/MasynNay/anything-plays/actions/runs/42909893531) | Identify the versions actually frozen into **each final 3.1.0** installer and compare each native hash/build arrangement to a corresponding original source tree |
| OpenCV, FFmpeg and transitive video codecs | [Exact stable 3.0 versus final 3.1 runtime inventory](V3_1_OPENCV_EXACT_RUNTIME_REVIEW.md): all 97 Linux, 82 Windows, 106 Apple Silicon and 17 Intel Mac OpenCV-associated frozen files match byte-for-byte; 3.0 and 3.1 both have FFmpeg-named binaries on three platforms, with libx264/libx265 on Apple Silicon. The older custom FFmpeg-free wheel evidence pertains to **2.0**, not the actual published 3.0 packages | Review original wheel FFmpeg build configuration, linked x264/x265 terms, exact corresponding sources, notices and applicable downstream redistribution/replacement requirements. Do not call 3.0 or 3.1 universally FFmpeg-free. |
| Other Python and native wheels | `licenses/PYTHON_DISTRIBUTIONS.json` and `licenses/python-distribution-notices/` are the intended in-package inventory | Verify these inventories are complete for each new final installer and carry all applicable license and corresponding-source obligations |

The six-source archive above is **still available** as a private Actions
artifact at the time of this review. Its original tagged SDL and pygame
sources are **candidates**. Naming a matching library version does not prove
that a particular frozen object was compiled from that exact source/patch
set. Do not substitute `src` links for a required, verifiable corresponding
source package without completing the source-to-binary review.

### Confirmed codec provenance correction (November 11)

The exact [four-platform OpenCV comparison](https://github.com/MasynNay/anything-plays/actions/runs/43131176213)
PASSED on Linux, Windows and both Mac architectures. Every OpenCV file in
the selected public 3.0 runtime matched its counterpart in the 3.1.0
private final runtime by SHA-256; FFmpeg libraries on Linux/Windows/Apple
Silicon and x264/x265 on Apple Silicon were already present in stable 3.0.
See the [full per-platform evidence and two remediation paths](V3_1_OPENCV_EXACT_RUNTIME_REVIEW.md).
An earlier reference to 2.0's FFmpeg-free custom OpenCV wheel does not describe
the exact 3.0 or 3.1 installer bytes. This finding neither clears nor
establishes a licensing violation; obtain actual source/build/rights evidence.

## 3. Existing genuine modified-native replacement evidence

Genuine source modifications to pygame CE `src_c/base.c` were compiled,
placed into disposable frozen app copies and successfully loaded on all
four native architectures:

- [Linux x64 modified pygame native source](https://github.com/MasynNay/anything-plays/actions/runs/42949949019)
- [Both macOS architectures](https://github.com/MasynNay/anything-plays/actions/runs/42951159759)
- [Windows x64 modified Visual C extension](https://github.com/MasynNay/anything-plays/actions/runs/42953456034)

These prove a narrow technical replacement path for **one** extension in
the earlier RC1 installation, not complete source/relink compliance for all
libraries frozen in **final 3.1.0**. Mac replacement requires local
ad-hoc resigning of a modified bundle. See
[V3_1_LGPL_ACTUAL_MODIFIED_PYGAME_WINDOWS_SOURCE_QA.md](V3_1_LGPL_ACTUAL_MODIFIED_PYGAME_WINDOWS_SOURCE_QA.md)
and [the macOS native gaps](V3_1_MACOS_NATIVE_DEPENDENCY_GAPS.md).

## 4. Outstanding verification before publication

1. **Read the completed exact-package inventory and finish interpretation:**
   [PR #203](https://github.com/MasynNay/anything-plays/pull/203) scanned
   every exact 3.1.0 full installer on four native systems, recording
   231 Linux, 199 Windows, 297 Apple Silicon and 209 Intel Mac native files
   plus package notice paths; [PR #204](https://github.com/MasynNay/anything-plays/pull/204)
   compared exact OpenCV bytes with public 3.0. Inventories are
   [preserved as QA artifacts](https://github.com/MasynNay/anything-plays/actions/runs/43130496526).
   Investigate each candidate library's actual dependencies, notices and
   source/build flags; resolve SDL duplicate-loader and codec ambiguity.
   Hash inventories alone are not legal correspondence or full review.
2. **Source correspondence:** Link each relevant native binary to actual
   tagged source, local patches, generated code, compiler flags and relevant
   transitive library inputs. Use the already pinned six-source candidates
   only if independent comparison supports that source match.
3. **Replacement and rebuild:** Document and test a recipient-usable process
   for rebuilding or replacing LGPL-covered native code on Windows/Linux and
   both Macs, including macOS re-signing after a replacement and any build
   files or link information required by the applicable licenses.
4. **Notices and permissions:** Verify applicable MIT, MPL, GPL, LGPL and
   other third-party notices/conditions, including special noncommercial
   or artwork restrictions where relevant. Include all required licenses
   and corresponding-source access with the *public* release, not only
   in expiring private CI artifacts.
5. **Separate physical QA:** Confirm representative real gamepad, webcam,
   game/video/audio, save/reload and longer session behavior as appropriate.
   If any cannot be tested, document precise unverified scope instead of
   marking it passed.
6. **Decision and rollout:** Require independent licensing/source signoff,
   final release notes and exact byte manifest, owner acceptance and a
   deliberate public release action. Confirm the draft is still private
   until those checks finish. After publication, update the portfolio and
   download links; keep 3.0 and RC2 untouched.

These steps are not a prediction that every obligation will apply in the
same way on every platform. They are a checklist for identifying and
meeting the actual component-specific requirements, with independent review.

## 5. Release decision at this checkpoint

- Full final-version 18-console installer technical QA: **PASS (4/4)**.
- Actual installed Tk/Stream Mode automated QA: **PASS (4/4)**.
- Private draft with all four verified binaries and three supporting receipts: **CREATED**.
- Complete per-final-installer LGPL/source/relinking and redistribution review: **OPEN**.
- Representative hardware/controller/camera/gameplay/endurance acceptance: **OPEN**.
- Final stable `v3.1.0` public release: **NOT PUBLISHED**.

Machine-readable gates:
[`config/v3.1-release-readiness.json`](../config/v3.1-release-readiness.json).
No step in this document sets `public_release_approved` to true.
