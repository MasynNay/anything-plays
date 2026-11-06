# v2.0 third-party redistribution audit

**Status: incomplete — do not publish bundled native installers.**

This record distinguishes verifiable licensing evidence from permission or
compliance conclusions. It is not legal advice. It applies to release binaries,
not the already-public MIT-covered Anything Plays original source.

## Emulator licenses

| Core | Claimed license | Evidence checked | Outstanding question |
| --- | --- | --- | --- |
| [mGBA Libretro port](https://github.com/libretro/mgba) | [MPL 2.0](https://github.com/libretro/mgba/blob/master/LICENSE) | The committed `licenses/mGBA-MPL-2.0.txt` matches upstream text | Associate each exact distributed binary with the source and patches used, and comply with MPL source availability and notices |
| [Snes9x Libretro port](https://github.com/libretro/snes9x) | [Custom noncommercial terms](https://github.com/libretro/snes9x/blob/master/LICENSE) | The committed `licenses/Snes9x-LICENSE.txt` matches upstream text | Confirm all purposes of the official free distribution are permitted and the compiled port's third-party obligations are satisfied |

The Snes9x license permits certain noncommercial copying and distribution
provided the copyright/license notice accompanies copies. It also describes
the software as freeware for personal use, reserves commercial permission, and
identifies some contributors for whom commercial rights are unavailable.
**Free of charge does not automatically prove an intended distribution meets
all noncommercial conditions.** Obtain qualified review or rights-holder
clarification if interpretation affects the release.

Snes9x's upstream license also identifies component licenses or exceptions,
including JMA (GPL/LGPL), `snes_ntsc` (LGPL), and xBRZ (GPLv3 with a reported
exception). **This list is not a claim those components are included in every
Libretro binary.** Inspect the exact compiled source/build options and bundled
dependencies to establish which notices and source obligations apply. Retain
the complete core-specific LICENSE; avoid replacing it with a short paraphrase.

### Snes9x source-level component finding

The [upstream Libretro source tree at `fae2fea`](https://github.com/libretro/snes9x/tree/fae2fea08f74180759ef540ee94259213f503480)
contains `filter/snes_ntsc-license.txt` and its
[`libretro/Makefile.common`](https://github.com/libretro/snes9x/blob/fae2fea08f74180759ef540ee94259213f503480/libretro/Makefile.common)
lists `filter/snes_ntsc.c` among the C sources without a conditional
feature flag. Thus the NTSC filter's LGPL 2.1 notice is relevant to builds
using that Makefile. The complete upstream license text is now committed at
`licenses/Snes9x-snes_ntsc-LGPL-2.1.txt`, and staged-bundle verification
requires it. The inspected source tree did not expose JMA or xBRZ component
directories mentioned by the general Snes9x LICENSE; this does not prove
their absence from every published native build. Inspect exact build logs
and source archives and review LGPL source/relinking requirements rather
than treating a license copy as full compliance.

## Source and binary traceability

The core builds in [a successful four-architecture CI run](https://github.com/MasynNay/anything-plays/actions/runs/42163068042)
reported these upstream identifiers:

- mGBA: `7a12d6d`, upstream
  [`7a12d6d4b9acb14c0ae62c9166b6a2f3d08007f6`](https://github.com/libretro/mgba/commit/7a12d6d4b9acb14c0ae62c9166b6a2f3d08007f6)
- Snes9x: `fae2fea`, upstream
  [`fae2fea08f74180759ef540ee94259213f503480`](https://github.com/libretro/snes9x/commit/fae2fea08f74180759ef540ee94259213f503480)

Those hashes resolve in the upstream repositories, but **reported version
strings do not prove build-to-source correspondence**. The `latest` buildbot
URLs can change. Before distribution: preserve exact binary archives, verify
their hashes, obtain/retain corresponding source revisions and build
instructions, and populate the explicitly unapproved
[core lock](CORE_RELEASE_PINNING.md).

### CI artifact retention check (2026-11-05)

GitHub Actions reported seven successful jobs in run
[`42164654048`](https://github.com/MasynNay/anything-plays/actions/runs/42164654048),
including Windows, Linux, and both macOS package targets. A check of the
run-artifact API for runs `42164654048`, `42163068042`, and `42159955003`
returned **zero downloadable artifacts for each run**. The existing package
jobs verify staged build output but do not upload immutable emulator core ZIPs
or completed installers. Therefore the earlier successful builds cannot be
used as a preserved, audited binary release input. Do not claim the eight
candidate SHA-256 values are re-obtainable merely because they were recorded.

The next release candidate must explicitly retain immutable core archives,
corresponding source snapshots, build dependency inventories, and the exact
final installers in a controlled location. Do not make unapproved installers
public simply to retain them as CI artifacts.

## Frozen Python and native libraries

- Direct requirement ranges in `requirements.txt` include OpenCV, NumPy,
  Pillow, sounddevice and macOS PyObjC. Version ranges and an unpinned
  PyInstaller installation do **not** create reproducible release builds.
- Installers now contain `licenses/PYTHON_DISTRIBUTIONS.json` plus available
  Python wheel license files, collected from the build environment. These
  include build-only packages; the collection is **not** a verified frozen
  binary software bill of materials (SBOM).
- Before publication, identify the actual shipped versions and native
  libraries from the PyInstaller output, check their license obligations and
  collect any missing notices, licenses, and corresponding source as required.
- Create target-specific lock files for Python dependencies once the exact
  versions and artifacts are approved. Do not treat the existing version ranges
  as sufficiently pinned.

### Review-only staged binary inventories

The `tools/binary_inventory.py` utility inspects the actual staged app folder
and writes SHA-256 checksums, sizes, native binary signatures (ELF, PE,
Mach-O), and internal symlink targets for every staged file. It refuses
symlinks that resolve outside the app folder. Unit tests cover known binary
formats and symlink boundaries.

Pull requests from `release/` branches run the four platform packaging checks
and upload **JSON metadata only** (`evidence-windows-x86_64`,
`evidence-macos-arm64`, `evidence-macos-x86_64`, and
`evidence-linux-x86_64`). The `.exe`, `.dmg`, `.deb`, and native core bytes
are **not** uploaded or approved by these jobs. Evidence JSON files support
review of what PyInstaller actually staged; they are not a complete software
bill of materials or verification of every linked system library. Review each
native file and compare inventories with frozen Python notices. Final release
binaries still require independent archival, archive-level inspection, and
separate redistribution approval.

### Headless OpenCV candidate (pending new installer checks)

Anything Plays uses Tkinter for its interface and relies on OpenCV for
camera capture, frame processing and drawing, not for `cv2.imshow` or
other OpenCV-owned windows. The upstream
[opencv-python wheel instructions](https://github.com/opencv/opencv-python)
recommend `opencv-python-headless` when a separate GUI toolkit is used.
The pinned build and source requirements now use that headless variant at
4.14.0.94. Its wheels exclude Qt/HighGUI libraries, eliminating the previously
observed bundled Linux Qt 5 GUI stack if platform verification confirms it.
**The FFmpeg and other native library obligations still require review.**
The release candidate currently stored in the private GitHub draft was
assembled before this change; it is not replaced or publicly distributed
merely by merging the dependency change. Validate four fresh platform
inventories, video capture backends, and packaged installers before promoting
a new candidate.

### Pinned v2 Python build dependencies

The four reviewed CI inventories from
[run 42172205627](https://github.com/MasynNay/anything-plays/actions/runs/42172205627)
recorded identical versions for the shared Python runtime packages, including
NumPy 2.5.4, OpenCV headless 4.14.0.94, Pillow 12.3.0, sounddevice 0.5.6,
PyInstaller 6.22.3 and pyinstaller-hooks-contrib 2026.9. Platform-specific
PyObjC, macholib, pefile and Windows compatibility packages were also
recorded. Those exact versions are now pinned in
[`requirements-build.txt`](../requirements-build.txt), installed by all
three installer scripts; source development retains its flexible
[`requirements.txt`](../requirements.txt).

This freezes *package versions*, not wheel SHA-256 hashes or the contents of
system libraries supplied by the operating system. The recorded package list
also includes build-only distributions, so the native-file inventory still
requires attribution and source/access review. Do not claim complete
reproducibility or distribution clearance from these pins alone.

### Actual candidate inventory findings (2026-11-06)

I inspected the four preserved, review-only binary inventories from the
[verified v2 packaging CI](https://github.com/MasynNay/anything-plays/actions/runs/42172205627).
Each inventory includes the exact SHA-256 of its staged native files. Reported
counts are **staged** files, not distinct third-party projects:

| Candidate target | Staged files | Native signatures | Recorded Python distributions |
| --- | ---: | ---: | ---: |
| Windows x64 | 1365 | 107 | 14 |
| Linux x64 | 831 | 177 | 12 |
| macOS Apple Silicon | 552 | 210 | 19 |
| macOS Intel | 465 | 123 | 19 |

- Core integrity: both mGBA and Snes9x matched their per-platform hashes in
  all four checked inventories, including the relocated macOS resources.
- The OpenCV wheel contributes **FFmpeg** and related libraries on all
  platforms; the Linux inventory also contains Qt 5 platform libraries,
  and the macOS ARM inventory contains additional media codec libraries such
  as `libx264`, `libx265`, `libavcodec` and `libavformat`.
  These are not covered solely by the top-level OpenCV Apache license.
  The upstream [OpenCV Python package licensing notes](https://github.com/opencv/opencv-python#licensing)
  identify FFmpeg as LGPL 2.1 and Qt 5 on non-headless Linux as LGPL 3.0.
- The OpenCV 4.14.0.94 wheel's `LICENSE-3RD-PARTY.txt` and `LICENSE.txt`
  files are already present in all four staged license directories, as are
  installed-distribution notices for NumPy, Pillow, sounddevice and other
  Python packages. This establishes notice *presence*, not that every
  corresponding-source, codec-license and linking/replacement obligation has
  been fulfilled.
- Every candidate inventory was checked for recognizable cartridge file
  extensions (`.gb`, `.gbc`, `.gba`, `.sfc`, `.smc`) and firmware formats
  (`.rom`, `.bios`), and none appeared. A new bundle guard now rejects
  those extensions in future installer builds. Extension checks cannot prove
  that arbitrary disguised files are licensed.

**Distribution review still needed:** establish per-platform OpenCV/FFmpeg/
Qt and codec license notice and corresponding-source obligations. Distinguish
actual bundled components from optional system-provided libraries; source
snapshots for the two emulators do not cover this multimedia dependency stack.

## Assets and distribution materials

- The maintainer states that the betta illustration was commissioned, that
  full ownership or commercial rights were purchased, and that it was later
  AI-recolored. See the [asset provenance record](ASSET_PROVENANCE.md).
  Exact contractual scope and mapping of each file to its source remain to be
  established; this attestation is not proof of rights for unrelated artwork
  or third-party trademarks.
- No commercial ROMs or game BIOS files are included in the planned releases.
- Windows setup is currently unsigned, and macOS uses ad-hoc signing without
  Apple Developer ID notarization. Release notes must accurately describe
  likely operating-system prompts; do not imply official code signing.
- Review final staged files **and** the completed installer archives on each
  target, compare checksums to a release manifest, and test installation only
  where newly changed packaging semantics justify it.

## Release sign-off

- [ ] Confirm applicability of the Snes9x noncommercial terms and compiled
      third-party exceptions to this specific noncommercial distribution.
- [ ] Verify exact mGBA and Snes9x source used for every locked binary, and
      provide source/access instructions required by the licenses.
- [ ] Archive immutable core binaries and hashes, with reviewed source commits.
- [ ] Review exact frozen Python/native dependencies and all required notices.
- [ ] Verify rights for all committed logos, backgrounds and cartridge art.
- [ ] Inspect the exact planned four installers and publish SHA-256 checksums.
- [ ] Obtain explicit owner release approval, then enable a reviewed release
      workflow that requires an approved core lock; keep the publishing gate
      off until then.

**No release approval has been granted by this document.**
