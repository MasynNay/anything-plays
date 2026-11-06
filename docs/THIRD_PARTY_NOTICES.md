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

## Python and native dependencies

OpenCV, NumPy, Pillow, sounddevice, PyObjC (macOS), and transitive native
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

The proposed v2.0 RC2 uses `opencv-python-headless` because Anything Plays
draws its interface with Tkinter rather than OpenCV's GUI. This removes
unnecessary Qt GUI libraries from Linux builds, subject to verification of
the final four platform archives. Headless OpenCV does **not** eliminate its
FFmpeg libraries or their independent redistribution obligations.

## Redistribution status

**Not yet approved for public binary distribution.** The following remain:
corresponding source and source-version verification for bundled cores,
dependency/license and asset-rights review, and inspection of final platform
installers. See [the release review](RELEASE_LICENSE_REVIEW.md).
