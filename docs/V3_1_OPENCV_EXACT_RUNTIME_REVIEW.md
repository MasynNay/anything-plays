# Anything Plays 3.1.0 — exact OpenCV and video codec source review

**Evidence recorded November 11, 2026. Review OPEN; this is not a legal
opinion or permission to publish the stable build.**

## What the actual packages contain

The [read-only native file/notice inventory](https://github.com/MasynNay/anything-plays/actions/runs/43130496526)
inspected the **complete**, checksum-matched final 3.1.0 installers on their
native OSes and retained one detailed JSON artifact for each target.
[PR #203](https://github.com/MasynNay/anything-plays/pull/203) merged these
checks without changing any installer.

The [stable 3.0 vs exact final 3.1.0 OpenCV comparison](https://github.com/MasynNay/anything-plays/actions/runs/43131176213)
then downloaded the *published* 3.0 installers, checked their published SHA-256,
downloaded the immutable 3.1.0 full QA installers from
[run 43120583726](https://github.com/MasynNay/anything-plays/actions/runs/43120583726),
checked their receipt/source hashes, and inspected extracted or read-only mounted
application bundles. All four native comparison jobs PASSED; the code
landed in [PR #204](https://github.com/MasynNay/anything-plays/pull/204).

| Native target | OpenCV-associated files with matching 3.0/3.1 hashes | Native OpenCV binaries matching byte for byte | FFmpeg / x264 / x265 names in BOTH versions |
| --- | ---: | ---: | --- |
| Linux x64 | 97 / 97 | 17 / 17 | 5 FFmpeg libraries (libavcodec, libavformat, libavutil, libswresample, libswscale) |
| Windows x64 | 82 / 82 | 2 / 2 | 1 OpenCV FFmpeg videoio DLL |
| Mac Apple Silicon | 106 / 106 | 94 / 94 | 6 FFmpeg libraries, libx264 and libx265 |
| Mac Intel | 17 / 17 | 5 / 5 | None identified by those filenames in inspected OpenCV subset |

**Conclusion supported by the byte comparisons:** Those libraries were
**already included in the published 3.0 installers**. The genuine final 3.1.0
build did **not introduce or change** the inspected OpenCV bytes. Do not
describe the 3.0 distribution as universally FFmpeg-free. An older
[2.0 source-access statement](RELEASE_SOURCE_ACCESS.md) specifically describes
*2.0's* custom-wheel build; its claim cannot be extended to public 3.0 or
private 3.1 without matching exact build evidence.

The separate native inventory found additional *codec-related* candidates:
7 on Linux, 1 on Windows, 9 on Apple Silicon and 2 on Intel Mac. Some, such as
libaom, libdav1d and libvpx, are **not themselves proof of GPL linkage**.
These inventories are names/hashes only. Absence of an FFmpeg filename on
Intel Mac is likewise not a proof that no codec code exists statically linked
inside any library.

## Source and license obligations needing independent verification

The pinned application uses **opencv-python-headless 4.14.0.94**. The official
[opencv-python project](https://github.com/opencv/opencv-python#licensing)
says its packaging scripts are MIT, OpenCV itself is Apache-2.0, and its
precompiled wheels bundle FFmpeg with LGPL 2.1 notices, plus other
third-party libraries listed in `LICENSE-3RD-PARTY.txt`.
The [FFmpeg legal guidance](https://ffmpeg.org/legal.html) explains the
distinction between FFmpeg's LGPL baseline and builds that enable optional
GPL-covered components, particularly libx264 and libx265. This is guidance
to inventory the **actual build and linked dependencies**, not proof that an
unmodified wheel complies, or that a project including it automatically
changes to GPL. Presence of libx264/libx265 in the Apple Silicon frozen
bundle warrants a separate build/configuration and applicable license review.

The native QA inventory also found bundled OpenCV wheel notices, including
`LICENSE-3RD-PARTY.txt`, on the audited targets. Their presence does not by
itself supply exact corresponding sources, compiler configuration, source
patches, user-replacement options or complete downstream notices.

**Still open, for each actual installer and each license-covered component:**

1. Identify the precise wheel and any upstream FFmpeg/native source revision,
   build configuration and patches that produced the distributed bytes.
2. Review each transitive codec library, its particular license and how
   FFmpeg/OpenCV links to it; especially the Apple Silicon x264/x265 pair.
3. Preserve correct license texts, attribution and applicable corresponding
   sources in nonexpiring public distribution materials. Review the
   component-specific replacement/relinking provisions where they apply.
4. Check SDL2, pygame-ce and original emulator cores separately. An FFmpeg
   review alone does not clear the other open 3.1 release gates.
5. Record an independent redistribution decision with evidence and physical
   device QA before the existing private `v3.1.0` draft is publicly released.

## Two technically viable remediation paths

**A. Keep existing verified binaries, complete component-by-component review.**
Audit their exact upstream build flags, license notices and sources; provide
recipient-usable correspondence/replacement information where required,
and obtain independent signoff for the native distribution. This preserves
the existing four-platform installer hashes and 13/13 native QA results, but
cannot be declared complete merely because 3.0 shipped the same codecs.

**B. Build an explicit camera-only OpenCV wheel on affected platforms.**
The desktop build scripts already accept a verified, source-built wheel using
`AP_CUSTOM_OPENCV_WHEEL` and
`AP_CUSTOM_OPENCV_SHA256`. The
[verification script](../tools/verify_custom_opencv_wheel.py) rejects
FFmpeg/x264/x265 filename candidates and checks wheel version and SHA-256;
`tools/check_opencv_build.py` requires the camera capture backend to stay
available and rejects active FFmpeg when the flag is set. An independently
source-built wheel could reduce the linked codec surface, but all affected
installers would need to be rebuilt, reaudited, rerun through native installed
UI and real camera checks, resigned as applicable, checked for corresponding
sources and updated in the private draft with fresh checksums. **Never
remove DLLs/dylibs from an already-verified package without testing; that
breaks its immutable verification and may break camera capture.**

There is no demonstrated clean-swap or license-clearance outcome yet.
Start with actual FFmpeg/OpenCV source and licence evidence from the current
published wheel and treat a four-platform custom build as a deliberate,
testable alternative, not a shortcut.

## Release and publication status

- Final 3.1.0 full 18-console installers: **PASSED** original source and
  frozen native GUI/Stream Mode automation on all four OSes.
- Private [seven-asset GitHub Release draft](https://github.com/MasynNay/anything-plays/releases/tag/untagged-293d7611aadb2e7f65f3):
  **created, not published**. Keep its exact asset hashes and public 3.0/RC2
  unchanged pending the independent release decision.
- OpenCV codec source/rights review: **OPEN**.
- pygame/SDL and other native distribution/source review: **OPEN**.
- Physical controller and representative camera/gameplay acceptance: **OPEN**.

See [full distribution review](V3_1_NATIVE_DISTRIBUTION_REVIEW.md),
[publication runbook](V3_1_PUBLICATION_RUNBOOK.md) and
[release readiness gates](../config/v3.1-release-readiness.json).
