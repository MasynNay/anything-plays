# Anything Plays 3.1.0 — Camera-only OpenCV corresponding-source record

**Exact four-platform source-build evidence, updated November 11/12, 2026.
Technical and reproduction documentation; it is NOT a statement of
redistribution compliance or a stable-release approval.**

## Exact upstream and locally modified source inputs

All four camera-only OpenCV wheels used in the unified 3.1.0 candidate were
built independently on their target operating systems using the original
`opencv-python-headless==4.14.0.94` source distribution:

| Input | SHA-256 | Permanent public access |
| --- | --- | --- |
| Original `opencv_python_headless-4.14.0.94.tar.gz` | `4afa2ea1214453648be88259f035712454faa9039b686de7753569ba8eec1577` | [Published project source archive](https://github.com/MasynNay/anything-plays/releases/download/v2.0.0/opencv_python_headless-4.14.0.94.tar.gz) |
| Windows packager `WINDOWS_OPENCV_SETUP_PATCH.diff` | See exact public 2.0.0 `SHA256SUMS.txt` and the native Windows provenance receipt | [Published source patch](https://github.com/MasynNay/anything-plays/releases/download/v2.0.0/WINDOWS_OPENCV_SETUP_PATCH.diff) |
| Original source/archive checksums | Recorded in published 2.0.0 source manifest | [Published `SHA256SUMS.txt`](https://github.com/MasynNay/anything-plays/releases/download/v2.0.0/SHA256SUMS.txt) |

The patch is a **source packaging** change to `setup.py`: it removes the
assumption that a bundled FFmpeg DLL must be present in the Windows wheel.
The original `.diff` uses descriptive `setup.py` diff-header captions.
[Windows native workflow](../.github/workflows/v31-windows-camera-only-opencv-source.yml)
verifies the original patch's public SHA256 and normalizes only those diff
headers in temporary memory before applying to a **separate source copy**.
Never alter the original published patch to make this work.

## Four separately native-compiled OpenCV source wheels

| Native host | Source-build evidence | Camera backend | Compile-time codec configuration |
| --- | --- | --- | --- |
| Linux x64 | [Actions 43133383864](https://github.com/MasynNay/anything-plays/actions/runs/43133383864) | V4L2 | FFmpeg off, GStreamer off, no Qt/GTK |
| Windows x64 | [Actions 43138596964](https://github.com/MasynNay/anything-plays/actions/runs/43138596964) | DirectShow | FFmpeg off, GStreamer off, no Qt, AVIF off |
| Mac Apple Silicon | [Actions 43137079614](https://github.com/MasynNay/anything-plays/actions/runs/43137079614), arm64 | AVFoundation | FFmpeg off, GStreamer off, no Qt, AVIF off |
| Mac Intel | [Actions 43137079614](https://github.com/MasynNay/anything-plays/actions/runs/43137079614), x86_64 | AVFoundation | FFmpeg off, GStreamer off, no Qt, AVIF off |

Each native source wheel was built with Python 3.13, pip 26.3, NumPy 2.5.4,
`ENABLE_HEADLESS=1`, `ENABLE_CONTRIB=0`, and
`CMAKE_BUILD_PARALLEL_LEVEL=3`, using platform-specific
`CMAKE_ARGS`. The private source build manifests record exact native
SHA-256 wheel fingerprints, and the wheel verification rejects unexpected
FFmpeg/x264/x265 file candidates. The imported native `cv2` reported a
working compiled camera backend and no active FFmpeg backend; no physical
webcam was opened by these source build tests.

The commands to reproduce each native wheel are in the exact source workflows:
[Linux](../.github/workflows/v31-linux-camera-only-opencv-source.yml),
[Windows](../.github/workflows/v31-windows-camera-only-opencv-source.yml),
[macOS Intel/ARM](../.github/workflows/v31-macos-camera-only-opencv-source.yml).
They are runnable examples, not an assertion that build dependencies on all
future developer machines will match GitHub-hosted runner images.

## Which exact 3.1.0 installers contain these wheels?

The [unified private four-platform
build](https://github.com/MasynNay/anything-plays/actions/runs/43140637755)
compiled the application at exact git revision
`104b96621ec4cb8dc39fde8c3fe96fc854c406ed` using those four
source-built custom wheels, preserving their SHA-256 fingerprints in
`FINAL_CAMERA_ONLY_OPENCV_SOURCE_QA.json` with the native source-stage and
full installer artifacts. All original eleven emulator core families and
18 console profiles were assembled; native installed Tk/Stream Mode/RC2
settings smoke passed for Windows, Linux, Intel Mac and Apple Silicon.

A [subsequent verified private release
stage](https://github.com/MasynNay/anything-plays/actions/runs/43142249044)
revalidated the same original four installers and embedded independent
source wheel hashes, exact upstream source SHA and CI run references in the
seven-asset `FINAL_QA_MANIFEST.json` and `FINAL_SOURCE_ACCESS_REVIEW.md`.
Its private 30-day GitHub Actions artifact is
`AnythingPlays-3.1.0-FOUR-CLEAN-FULL-18-SOURCE-VERIFIED-PRIVATE-REVIEW`.
The original public 3.0 and RC2 packages and the older stock OpenCV
private 3.1 draft were **not** changed.

A source package download, compiler invocation, wheel/native backend check,
or checksum is not equivalent to permission to distribute. The private
source-wheel artifacts expire, so a public release needs durable recipient
access to required original and modified sources, notices, actual build
instructions and any replacement/relinking mechanisms that apply.

## Remaining source and replacement obligations are NOT certified

This record covers **only these four OpenCV wheel builds**. It does not
establish complete corresponding-source/rebuild/relinking compliance for
pygame-ce and SDL2/SDL2_image/SDL2_mixer/SDL2_ttf, their transitive
libraries, the eleven original emulator cores, or any relevant license
obligations. A separate [native distribution review](V3_1_NATIVE_DISTRIBUTION_REVIEW.md)
documents those gaps. Source candidate archives in
[V3_1_SOURCE_COMPANION.md](V3_1_SOURCE_COMPANION.md) may help the reviewer
but do not automatically correspond to every shipped frozen object.

**Explicit release decision:** `public_release_approved = false`.
Do not update the public GitHub Release, application website, or
`config/v3.1-release-readiness.json` source/legal/hardware gates based
solely on this technical OpenCV record. For public stable 3.1.0, the owner
still needs grounded physical controller/camera/gameplay acceptance and
independently reviewed source/notice/replacement and redistribution evidence.
