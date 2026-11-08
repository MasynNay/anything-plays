# Third-party software notices

Anything Plays contains independent third-party components. The repository
[MIT License](../LICENSE) applies to original project code only to the extent
its contributors have the rights to grant it.

## Native emulator cores

### mGBA — Game Boy, Game Boy Color, and Game Boy Advance

- Upstream: https://github.com/libretro/mgba
- License: Mozilla Public License 2.0
- License text: `licenses/mGBA-MPL-2.0.txt` in the source repository,
  `mGBA-MPL-2.0.txt` beside this notice in an installed package
- Documentation: https://docs.libretro.com/library/mgba/

### Snes9x — Super Nintendo Entertainment System

- Libretro port: https://github.com/libretro/snes9x
- Upstream: https://github.com/snes9xgit/snes9x
- License: custom noncommercial terms
- License text, including contributor copyright notices:
  `licenses/Snes9x-LICENSE.txt` in the repository, or
  `Snes9x-LICENSE.txt` beside this notice in an installed package

Snes9x's permission to distribute applies only subject to its terms, including
its noncommercial restrictions and required copyright notices. Snes9x is **not**
MIT-licensed or OSI-approved open source.

The checked Snes9x Libretro source at commit
[`fae2fea`](https://github.com/libretro/snes9x/commit/fae2fea08f74180759ef540ee94259213f503480)
lists `filter/snes_ntsc.c` in `libretro/Makefile.common`. The filter is
separately licensed under LGPL 2.1; the verbatim upstream
`filter/snes_ntsc-license.txt` is bundled as
`licenses/Snes9x-snes_ntsc-LGPL-2.1.txt` (installed beside this notice).
Including the license text is required but does **not** alone establish all
LGPL source, relinking or other distribution compliance obligations.
Review the actual compiled binary and corresponding source before release.

Gambatte (GPLv2) appeared in historical development builds but is not
included in this release plan. Historical license:
`history/Gambatte-GPL-2.0.txt`.

## Additional 3.0 core license texts (candidate audit)

The 3.0 **full offline developer preview** includes additional independent
cores beyond the v2.0 mGBA and Snes9x set. Their inclusion does not mean
that public redistribution is already approved.

The following GPLv2 license texts have been copied verbatim from the
**specific upstream source revisions reported by the Linux preview
binaries**:

- **ProSystem (Atari 7800):** `licenses/ProSystem-GPL-2.0.txt`,
  [pinned upstream license](https://github.com/libretro/prosystem-libretro/blob/8a88014287c7a01cd568067e5a557d0a2b2a051f/License.txt).
- **Beetle NeoPop (Neo Geo Pocket / Color):**
  `licenses/Beetle-NeoPop-GPL-2.0.txt`,
  [pinned upstream COPYING](https://github.com/libretro/beetle-ngp-libretro/blob/a50d5ac288a81f2104ddf43195a4efdd15c72227/COPYING).
- **Beetle WonderSwan (WonderSwan / Color):**
  `licenses/Beetle-WonderSwan-GPL-2.0.txt`,
  [pinned upstream COPYING](https://github.com/libretro/beetle-wswan-libretro/blob/4b01295838ea89e3f1355bbe4cb5cf98aa6108cd/COPYING).

A `COPYING` or `License.txt` file is only part of a complete release
notice inventory. Copyright headers, corresponding source distribution,
linked library terms and any other obligations must still be reviewed
against the exact packaged native binary. Reported Git versions are not
independent proof of reproducible compilation. The release remains blocked
until [the 3.0 distribution review](V3_DISTRIBUTION_READINESS.md) and
release acceptance evidence are complete.

## Python and native dependencies

OpenCV, NumPy, Pillow, sounddevice, glcontext, PyObjC (macOS), and transitive native
libraries retain their own licensing and attribution requirements. The
installed versions and full dependency notices need a release-specific audit.

### OpenCV, FFmpeg and GUI dependency boundaries

The official [opencv-python packaging project](https://github.com/opencv/opencv-python#licensing)
states that the packaging scripts are MIT-licensed, the OpenCV library is
Apache-2.0-licensed, and its bundled FFmpeg libraries are licensed under
LGPL-2.1. The official [FFmpeg licensing guidance](https://ffmpeg.org/legal.html)
explains that optional GPL components can change a particular FFmpeg build's
applicable terms and describes obligations when redistributing binaries.

The installer records each wheel's installed version and copies its license
files, including OpenCV's `LICENSE-3RD-PARTY.txt`, to
`licenses/python-distribution-notices/`. These notices include the FFmpeg
LGPL language. They do not independently prove that the source corresponding
to every frozen FFmpeg binary is available or that all LGPL installation,
replacement and linking conditions are met.

Earlier RC2/RC3 used the stock `opencv-python-headless` wheel, eliminating
Qt GUI binaries but **not** its bundled FFmpeg codec dependencies.
The [publicly distributed RC6-derived v2.0.0](RC6_VERIFICATION.md) uses separate, SHA-256-locked
source-built wheels for all four platforms, configured with FFmpeg disabled.
The staged Windows, Linux, and both Mac inventories now contain no FFmpeg,
x264 or x265 binary filenames; build-time camera backends and tracking image
operations passed. The exact OpenCV source, its Windows packaging patch, and
four wheel files and the corresponding source/patch evidence are preserved in the reviewed private RC6 draft; public source and notices accompany the release. This is not proof
that unrelated native dependencies or all source/license obligations are met.

## Redistribution status

**Published for the project's stated free/noncommercial use only.** The [v2.0.0 release](https://github.com/MasynNay/anything-plays/releases/tag/v2.0.0) includes exact source snapshots and all four installer hashes. This does not confer commercial reuse rights for Snes9x or the commissioned artwork or establish independent reproducible upstream core builds. See [the scoped review](RELEASE_DISTRIBUTION_REVIEW.md) and [source access instructions](RELEASE_SOURCE_ACCESS.md).

### glcontext 3.0.0 — headless WGL/CGL GameCube rendering

- Upstream: https://github.com/moderngl/glcontext
- License: MIT, copyright 2021 ModernGL Contributors
- Complete upstream license: `licenses/glcontext-MIT.txt` (to be
  included verbatim with frozen application notices)
- The module uses system graphics drivers. It supplies OpenGL contexts, **not**
  Dolphin code, firmware, ROMs, or the standalone RetroArch application.
