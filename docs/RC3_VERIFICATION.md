# v2.0.0 RC3: verified private candidate

**Status:** All four installer candidates are assembled and checksummed, but
they are **not approved or published for public redistribution**.

- [Private candidate CI run](https://github.com/MasynNay/anything-plays/actions/runs/42237242577):
  eight jobs passed after rerunning a runner-cancelled Apple Silicon job.
- [Private draft](https://github.com/MasynNay/anything-plays/releases):
  `v2.0.0-rc.3`, `draft=true`, 22 assets. The files below are in that draft.
- All eight Libretro ZIP inputs were restored from the earlier private RC1
  draft and SHA-256 verified *before* loading the core binaries. They were not
  fetched again from mutable nightly URLs.
- Both exact upstream Git source snapshots are attached, matching the source
  revisions reported by the cores. These independently identify upstream Git
  trees, but do **not** independently reproduce the buildbot's compilation.

## Installer identities

The exact assets and GitHub-reported SHA-256 digests were checked against the
successful RC3 job logs. All file sizes are bytes.

| Target | Asset | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Windows x64 | `AnythingPlaysSetup-2.0.0.exe` | 55,037,277 | `b52aa24b059e42eb5871abdac1121e6005cc2a648ae2cb8015249f3a0b14bcb0` |
| macOS Apple Silicon | `AnythingPlays-2.0.0-macos-arm64.dmg` | 78,727,962 | `2ab7fd37a3cb9436f2da6375d0cc6e16e131ee04a25c39a7d2f18deba4ebb025` |
| macOS Intel | `AnythingPlays-2.0.0-macos-x86_64.dmg` | 71,470,305 | `7d202a71eb4d5628261429b84a28e75ac38e9ed71a785518a0273107d0bee576` |
| Ubuntu/Debian x64 | `anything-plays_2.0.0_amd64.deb` | 88,846,720 | `69172502fdd4ba18fbdfde0a1a5e33c9ffacba6581b767e9c3a8d13f789ca38e` |

The private draft also contains `SHA256SUMS.txt`,
`DRAFT_REVIEW_STATUS.json`, four `CORE_PROVENANCE-*.json` manifests,
eight architecture-specific preserved core ZIPs, and source snapshot hashes.

## Upstream source snapshots

| Source | Git commit | SHA-256 of attached tar.gz |
| --- | --- | --- |
| [mGBA Libretro](https://github.com/libretro/mgba) | `7a12d6d4b9acb14c0ae62c9166b6a2f3d08007f6` | `122d8ed73f8fb62b57bded027be5cbbe076ecd2835efe15ccbf3a644aa57a3a2` |
| [Snes9x Libretro](https://github.com/libretro/snes9x) | `fae2fea08f74180759ef540ee94259213f503480` | `6dc065591029650687c666499c6dd70f41b9dfcafe7fac80facb7858bb6bea41` |

## What these checks do and do not demonstrate

**Verified technically:** four platform archive builds completed; the Mac
DMGs and Linux DEB were checked after packaging; final staged native cores
matched the pinned binary hashes; checksums and source snapshots are retained.
The Python packaging version set is pinned; GUI-less OpenCV was confirmed
compatible with platform camera backends at the OpenCV registry level.

**Not yet verified:** actual camera hardware on all four target hosts,
reproducible third-party Libretro builds, FFmpeg/codec corresponding-source
and LGPL/GPL conditions, Snes9x component-exception review, or the scope of
all artwork redistribution permissions. An ad-hoc signed macOS bundle is not
Apple-notarized, and the Windows installer is unsigned.

A source or draft binary existing in GitHub is **not** a public-release
approval. Continue tracking the outstanding conditions in
[issue #10](https://github.com/MasynNay/anything-plays/issues/10) and
[the redistribution audit](REDISTRIBUTION_AUDIT.md). The public publication
workflow must remain disabled until rights and compliance sign-off is complete.
