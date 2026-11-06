# Source code and redistribution notices for Anything Plays 2.0

Anything Plays' **original Python application code** is available under the
repository's MIT license. **The entire installer is not MIT-licensed**:
it includes separately licensed emulator cores and other dependencies.

## Exactly which sources accompany the installers

- **Application:** the `v2.0.0` repository tag, including
  `anything_plays/`, tests, desktop build scripts, and included notices.
- **mGBA Libretro core:** Mozilla Public License 2.0. Reported upstream
  revision `7a12d6d4b9acb14c0ae62c9166b6a2f3d08007f6`.
  [Upstream source](https://github.com/libretro/mgba) and the attached
  `source-mgba-7a12d6d4b9acb14c0ae62c9166b6a2f3d08007f6.tar.gz`.
  The full MPL text is in `licenses/mGBA-MPL-2.0.txt`.
- **Snes9x Libretro core:** custom **noncommercial** license, not MIT,
  with required author copyright notices. Reported upstream revision
  `fae2fea08f74180759ef540ee94259213f503480`.
  [Upstream source](https://github.com/libretro/snes9x) and the attached
  `source-snes9x-fae2fea08f74180759ef540ee94259213f503480.tar.gz`.
  The complete license is in `licenses/Snes9x-LICENSE.txt`.
- **Snes9x NTSC filter:** LGPL 2.1 component included in the upstream Snes9x
  source snapshot. The full NTSC license is in
  `licenses/Snes9x-snes_ntsc-LGPL-2.1.txt`.
  The general Snes9x license also describes exceptions for components used
  in Snes9x. JMA and xBRZ are **not** present in the pinned Libretro
  source tree.
- **Custom headless OpenCV wheels:** Apache-2.0/OpenCV and separate packaging
  terms. All four wheels are based on
  `opencv-python-headless==4.14.0.94`. The original
  `opencv_python_headless-4.14.0.94.tar.gz` source and the Windows-specific
  `WINDOWS_OPENCV_SETUP_PATCH.diff` are preserved as release inputs.
  FFmpeg, x264, x265, GStreamer and Qt were disabled in these wheels.
  The Windows patch only removes an upstream packager assumption that an
  FFmpeg DLL exists; see `WINDOWS_OPENCV_PATCH_PROVENANCE.json`.
- **Other Python and native packages:** the installed application contains
  exact version records in `licenses/PYTHON_DISTRIBUTIONS.json` and copies
  relevant wheel license notices into
  `licenses/python-distribution-notices/`. Platform system libraries are
  governed by their respective licenses and package managers.

All eight native core archives and the exact source snapshots are preserved
with platform-specific SHA-256 manifests. The cores **report** the upstream
source revisions above. That establishes their declared revision but **does
not independently reproduce the Libretro buildbot compilation**, and no
independent reproducible-build guarantee is given.

## Replacing and rebuilding emulator cores

The application loads ordinary Libretro dynamic libraries. Advanced users
may build a compatible mGBA or Snes9x core from the upstream source/Libretro
build files and replace `cores/mgba_libretro.*` or
`cores/snes9x_libretro.*` in the installed application's resources:

- Windows: inside the installed `AnythingPlays/cores/` folder.
- Ubuntu/Debian: `/opt/anything-plays/_internal/` for Python dependencies
  and `/opt/anything-plays/cores/` for native cores.
- macOS: inside `AnythingPlays.app/Contents/Resources/cores/`.

Replacement cores must match the Libretro ABI and the system architecture.
macOS app modifications invalidate the existing ad-hoc code signature; a
modified local app may need to be ad-hoc signed again for the user's machine.
This is not an assertion of Apple notarization or of compatibility with
arbitrary modified cores.

The release includes **no copyrighted game ROMs or BIOS images**. Users must
supply legally obtained compatible game images themselves.

## Use and restrictions

Anything Plays is distributed free of charge and without ads, subscriptions,
donations or paid promotions. Snes9x does **not** permit unrestricted
commercial use. Anyone planning commercial redistribution of a complete
installer must obtain the necessary third-party permissions; the project's
MIT license is limited to its own original code. The commissioned betta fish
artwork is separately rights-controlled and is not part of the MIT code
license. Nintendo and other trademark holders do not endorse the project.

The checksums identify exact binary files, not copyright compliance.
See [the binary review](RC5_VERIFICATION.md) and
[third-party notices](THIRD_PARTY_NOTICES.md) for technical evidence and
upstream licensing conditions.
