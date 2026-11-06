# Third-party software notices

Anything Plays contains independent third-party components. The repository
[MIT License](../LICENSE) applies to original project code only to the extent
its contributors have the rights to grant it.

## Native emulator cores

### mGBA — Game Boy, Game Boy Color, and Game Boy Advance

- Upstream: https://github.com/libretro/mgba
- License: Mozilla Public License 2.0
- Bundled license text: `../licenses/mGBA-MPL-2.0.txt`
- Documentation: https://docs.libretro.com/library/mgba/

### Snes9x — Super Nintendo Entertainment System

- Libretro port: https://github.com/libretro/snes9x
- Upstream: https://github.com/snes9xgit/snes9x
- License: custom noncommercial terms
- Bundled license text, including contributor copyright notices:
  `../licenses/Snes9x-LICENSE.txt`

Snes9x's permission to distribute applies only subject to its terms, including
its noncommercial restrictions and required copyright notices. Snes9x is **not**
MIT-licensed or OSI-approved open source.

Gambatte (GPLv2) appeared in historical development builds but is not
included in this release plan. Historical license:
`history/Gambatte-GPL-2.0.txt`.

## Python and native dependencies

OpenCV, NumPy, Pillow, sounddevice, PyObjC (macOS), and transitive native
libraries retain their own licensing and attribution requirements. The
installed versions and full dependency notices need a release-specific audit.

## Redistribution status

**Not yet approved for public binary distribution.** The following remain:
corresponding source and source-version verification for bundled cores,
dependency/license and asset-rights review, and inspection of final platform
installers. See [the release review](RELEASE_LICENSE_REVIEW.md).
