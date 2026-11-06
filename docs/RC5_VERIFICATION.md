# Anything Plays v2.0.0 — verified private RC5

**Status: release engineering complete; public binary redistribution has not been authorized.**

[RC5 GitHub Actions](https://github.com/MasynNay/anything-plays/actions/runs/42255146567)
finished successfully on all eight jobs, including final archive integrity and
two upstream core source snapshots. The resulting GitHub Release
`v2.0.0-rc.5` is a **private draft**, with 31 preserved assets after
[the follow-up source archival run](https://github.com/MasynNay/anything-plays/actions/runs/42256596208).
The candidate contains no commercial game ROMs or BIOS files by its
recognized-extension verification, and requires end users to supply their own.

## Final installer identities

The SHA-256 digests and sizes below are recorded by GitHub for the actual
assets in the RC5 draft; these are not filename guesses or build intentions.

| Target | Archived filename | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Windows x64 | `AnythingPlaysSetup-2.0.0.exe` | 46,684,864 | `618d07905153da559695727dea77911dd6b7de2dcb5bfa4bddf02dba4e4ba425` |
| Ubuntu/Debian x64 | `anything-plays_2.0.0_amd64.deb` | 68,818,108 | `5554cb7bac9eca3131ac22423ae418bc4c34172bd5e268531bdfcf01e6ec091b` |
| macOS Apple Silicon | `AnythingPlays-2.0.0-macos-arm64.dmg` | 48,257,029 | `762d5ab958ca47cb4456b4d5f88527152f7a20ae1b518720ccad8fc86a92c462` |
| macOS Intel | `AnythingPlays-2.0.0-macos-x86_64.dmg` | 69,998,133 | `995158b5ccb56bf945ea127d4c0620c0295231d57a50a9d1df998435e2c82ab3` |

## Actual frozen native-library inventories

Each installer was built with a separately SHA-256-verified, source-built
`opencv-python-headless==4.14.0.94` wheel with **FFmpeg, GStreamer and Qt
disabled**. Runtime tests confirmed DirectShow on Windows, V4L2 on Linux,
and AVFoundation on both Mac architectures, plus HSV conversion and contour
tracking on synthetic frames. This is not a test of physical camera hardware.

Actual `dist/` file inventories from RC5 CI, with independent JSON reports
attached as workflow artifacts:

| Target | Staged files | Native binaries | mGBA / Snes9x core hashes | FFmpeg/x264/x265 files |
| --- | ---: | ---: | --- | ---: |
| Windows x64 | 1,365 | 106 | Both matched | 0 |
| Linux x64 | 775 | 130 | Both matched | 0 |
| macOS Apple Silicon | 461 | 119 | Both matched | 0 |
| macOS Intel | 464 | 122 | Both matched | 0 |

The absence of these file names and runtime backends resolves the specific
previously-bundled FFmpeg/GPL-codec problem. It **does not** establish every
native dependency's license terms or provide legal distribution approval.

## Immutable OpenCV input wheels

Each of the four wheel files is also retained inside the private RC5 draft,
not merely in short-lived GitHub Actions artifacts.

| Target | Source build run | Wheel SHA-256 |
| --- | --- | --- |
| Windows x64 | [Patched source](https://github.com/MasynNay/anything-plays/actions/runs/42249929138) | `8f824a062ff42d18104478619a3165e8121ddd17275b49fc5797499a1f776914` |
| Linux x64 | [Headless source](https://github.com/MasynNay/anything-plays/actions/runs/42246559996) | `a4bff6a1596aa2e41721748aa12fa56819224efd6701b040eebe6e3c07d3787f` |
| macOS Apple Silicon | [Headless source](https://github.com/MasynNay/anything-plays/actions/runs/42245121687) | `3e1d31233267fdea67311907654d8166d180f9173b87d36b480ab1468e38b6cd` |
| macOS Intel | [Headless source](https://github.com/MasynNay/anything-plays/actions/runs/42246559996) | `1a9815cee13c8efa8c350fc6cea22c960909bb2ec2366319719dbd608ac63c40` |

The source distribution
`opencv_python_headless-4.14.0.94.tar.gz`
(SHA-256 `4afa2ea1214453648be88259f035712454faa9039b686de7753569ba8eec1577`)
and the exact Windows `setup.py` packaging diff and JSON patch provenance are
retained in the private RC5 draft. The Windows source patch removes only
an upstream wheel packager's assumption that an FFmpeg DLL exists even when
FFmpeg is disabled. Its original unpatched PyPI source is preserved.

## Emulator provenance and source availability

All eight original Libretro ZIPs and four corresponding platform manifests
were copied from the original private RC1 draft, hash checked before building
and then preserved again in RC5. The **reported** upstream Git commits are:

- mGBA: `7a12d6d4b9acb14c0ae62c9166b6a2f3d08007f6` (MPL 2.0)
- Snes9x: `fae2fea08f74180759ef540ee94259213f503480` (custom
  noncommercial; the compiled NTSC filter is separately under LGPL 2.1)

Both complete source snapshots and their SHA-256 manifest are attached to
the private draft. These are original upstream source trees at the core's
reported Git revision, **not independently reproducible builds** of the
upstream nightly binaries.

## Final checks before public release

The release owner still needs to approve Snes9x's noncommercial use as
applicable to the actual, free, nonpromotional distribution; ensure that
mGBA/MPL and Snes9x NTSC/LGPL corresponding-source and applicable
modification/relinking obligations are met; confirm the commissioned artwork's
transfer/license covers public installer distribution and derivatives; and
complete the third-party native dependency and legal/rights review. See
[issue #10](https://github.com/MasynNay/anything-plays/issues/10).

The distributed Mac application is ad-hoc signed but not Apple notarized;
Windows is unsigned. GitHub CI verifies package structure and required
camera backends but does not substitute for a physical-camera launch test
on an end-user system.

**Do not publish the private RC5 binary assets, create a public v2.0.0
release, set `approved_for_binary_distribution=true`, or enable the public
release workflow until those outstanding approvals are documented.**
