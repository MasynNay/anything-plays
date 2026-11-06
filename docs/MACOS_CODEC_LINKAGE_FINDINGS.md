# macOS OpenCV / FFmpeg native-linkage evidence

**Inspection target:** Anything Plays v2 headless OpenCV candidate built from
`opencv-python-headless==4.14.0.94`, with both Libretro cores preserved.
Evidence: [seven-check run 42242227319](https://github.com/MasynNay/anything-plays/actions/runs/42242227319)
and merged [PR #20](https://github.com/MasynNay/anything-plays/pull/20).
The run retained JSON-only `codec-linkage-macos-arm64.json` and
`codec-linkage-macos-x86_64.json` as release evidence artifacts. These
records are not permission to distribute the frozen binary.

## Apple Silicon findings

The macOS arm64 staged application contains all of these libraries in
`AnythingPlays.app/Contents/Frameworks/cv2/__dot__dylibs/`:

- `libavcodec.61.19.101.dylib`
- `libavformat.61.7.100.dylib`
- `libavutil.59.39.100.dylib`
- `libswresample.5.3.100.dylib`
- `libswscale.8.3.100.dylib`
- `libx264.164.dylib`
- `libx265.215.dylib`

Apple's `otool -L` confirmed direct load commands from **both**
`libavcodec.61.19.101.dylib` and `libavformat.61.7.100.dylib` to
`@rpath/libx264.164.dylib` and `@rpath/libx265.215.dylib`.
The `libavdevice` and `libavfilter` binaries also refer to both codecs.
The same linkage report confirms that `cv2.abi3.so` links to
`libavformat`, `libavcodec`, `libswscale`, and `libavutil`.

**Result:** deleting either codec dylib by itself would violate recorded
dynamic links. Do not remove individual binaries from this package as a
licensing shortcut. The fact that the user interface only needs camera
capture does not make these load commands optional.

## Intel macOS contrast

In the separately frozen Intel macOS wheel, no discrete
`libx264*.dylib` or `libx265*.dylib` was found, and the inspected
Mach-O load commands did not reference either filename. This is *not*
proof that all FFmpeg code is absent or that the Intel build has no
LGPL/GPL obligations.

## Why this blocks unqualified LGPL claims

The official [FFmpeg licensing checklist](https://ffmpeg.org/legal.html)
explains that FFmpeg is generally LGPL but may become GPL when GPL
components are enabled; it explicitly names libx264 as an item to review.
The [x264 licensor](https://x264.org/licensing/) offers GPLv2 and separate
commercial licensing, while [VideoLAN's x265 page](https://github.com/videolan/x265)
lists GPLv2 and commercial licensing.

The `otool` data establishes **linkage**, not whether the distributor holds
a special commercial license, exactly how these dylibs were compiled, or the
resulting license obligations of the combined project. Those questions need
further evidence.

## Next safe engineering path

1. Build `opencv-python-headless` from its corresponding source with
   `WITH_FFMPEG=OFF` and `WITH_GSTREAMER=OFF` on Apple Silicon; the project's
   [official build guide](https://github.com/opencv/opencv-python) documents
   custom `CMAKE_ARGS` and source-wheel builds.
2. Verify the resulting wheel reports `FFMPEG: NO`, that AVFoundation camera
   capture remains enabled, and that HSV conversion, resizing and contour
   processing continue to work.
3. If those checks pass, test a *separate* macOS arm64 app/package with the
   replacement wheel, including the signed DMG and frozen core hashes.
4. Only after runtime and binary-provenance verification, replace the candidate
   input in the controlled release path and repeat full rights review.

An isolated proof of concept is tracked on the
[`experiment/opencv-camera-only-arm64` branch](https://github.com/MasynNay/anything-plays/tree/experiment/opencv-camera-only-arm64).
It is **not** included in the private RC3 or public releases.

**Distribution status: not approved.** The public publication workflow stays
disabled until the separate native library/source obligations, Snes9x terms,
and artifact rights are satisfied.
