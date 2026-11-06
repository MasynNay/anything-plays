# Anything Plays 2.0.0 — final RC6 verification

**Engineering result:** all four installer archives passed their native
build, staged-core integrity, and archive verification checks. The
[RC6 build workflow](https://github.com/MasynNay/anything-plays/actions/runs/42259984523)
completed with eight green jobs. The RC6 release is a private draft until
the separately controlled public publication step is approved.

## Exact final installer file hashes

| Platform | File | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Windows x64 | `AnythingPlaysSetup-2.0.0.exe` | 46,673,740 | `78781389a4d7855b55ca7a41339645d69f6c64bc94d5574a2055fc4cdd249a0d` |
| Ubuntu/Debian x64 | `anything-plays_2.0.0_amd64.deb` | 67,414,520 | `b37cf8ead48abf73369782b5b2f796fdbb8697dd38cd5bead11e45fb50538ab3` |
| macOS Apple Silicon | `AnythingPlays-2.0.0-macos-arm64.dmg` | 48,224,997 | `b6f2bfabe60d1bf19d59003dd0ef6a5d6b23298e419f29886e11d2611f42f4b8` |
| macOS Intel | `AnythingPlays-2.0.0-macos-x86_64.dmg` | 69,998,616 | `9e8d14f2f6f8e62eda1254b846d149f64c49ff4f7bf4f8d34ab52f4689510f67` |

These are the actual GitHub asset digests recorded against the preserved RC6
draft, not estimates or filenames inferred from source.

## Final installed dependency inventories

The [RC6 workflow](https://github.com/MasynNay/anything-plays/actions/runs/42259984523)
produced a metadata-only inventory for each staged application. Its
per-platform verification found:

| Target | Regular files | Native executable files | FFmpeg / x264 / x265 shared libraries |
| --- | ---: | ---: | ---: |
| Windows x64 | 1,365 | 106 | 0 |
| Ubuntu/Debian x64 | 769 | 124 | 0 |
| macOS Apple Silicon | 461 | 119 | 0 |
| macOS Intel | 464 | 122 | 0 |

The Linux application now excludes the unused Python Readline extension and
its GPL-related frozen binary, plus redundant local copies of PortAudio,
JACK, ALSA and Berkeley DB. Instead, its DEB explicitly declares
`libportaudio2` as a system dependency. The separate
[Linux ELF dependency audit](https://github.com/MasynNay/anything-plays/actions/runs/42258214050)
verified this pruning preserves the two core hashes and that the Ubuntu
system PortAudio library loads normally.

Both mGBA and Snes9x remain the exact original native binaries on every
platform, and their expected SHA-256 values matched the post-packaging
core manifests. The original eight emulator ZIPs, source snapshots, four
OpenCV wheels and the corresponding OpenCV source plus Windows patch are
privately preserved with RC6.

## Features and compatibility

- GB/GBC/GBA all use mGBA; SNES uses Snes9x
- Independent game shelves, configurable zones, themes, audio and manual
  keyboard input remain part of the tested application
- OpenCV camera acquisition backends remain available: DirectShow (Windows),
  V4L2 (Linux), and AVFoundation (Mac)
- Synthetic camera frame color conversion and contour tests passed
- The user's earlier manual test confirmed the v2.0 app on Windows, Mac,
  and Ubuntu; a complete hardware webcam test of the final *RC6 binary*
  on each physical target was **not** performed by GitHub Actions

The Windows installer is unsigned; the Mac app is ad-hoc signed but is not
Apple-notarized. First launch may require explicit operating-system approval.

## Sources and redistribution

A full list of component licenses, source repositories and modification
instructions appears in [Release Source Access](RELEASE_SOURCE_ACCESS.md).
The Snes9x core uses noncommercial terms and a separate LGPL NTSC component.
All publicly shared software must respect those terms. The core binaries
report the specified upstream Git revisions and full source snapshots are
retained; the upstream buildbot compilation has **not** been independently
reproduced, so no byte-reproducibility assurance is made.

This record is technical verification, not a legal opinion or blanket grant
of third-party commercial redistribution rights. The exact final assets
must be published with their license notices, source links and SHA-256
checksums, and the public release must be explicitly approved separately.
