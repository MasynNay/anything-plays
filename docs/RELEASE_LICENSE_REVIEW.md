# v2.0 binary release readiness

**Application functionality:** The maintainer supplied Windows EXE, macOS
DMG and Linux DEB installers and confirmed that v2.0 worked on all three
operating systems. This prior gameplay testing is complete and should not be
repeated merely for changes to documentation.

**Source:** The v2.0 application is merged into `main`. Original code is
licensed under MIT (where contributors have rights to grant that license).

**Binary distribution:** Not yet approved. This record is technical evidence,
not legal advice or a claim of copyright clearance. Consult the
[third-party rights audit](REDISTRIBUTION_AUDIT.md) and the
[release core pinning procedure](CORE_RELEASE_PINNING.md) before sign-off.

## Core licensing strategy

For the prospective public binary build, Game Boy, Game Boy Color, and Game
Boy Advance use the already-integrated mGBA Libretro core (MPL 2.0); SNES
uses Snes9x under its custom noncommercial terms. That removes Gambatte
GPLv2 from the *proposed* packaged binary, avoiding the specific Gambatte /
Snes9x combined-work conflict that blocked the earlier three-core design.
This does not automatically resolve all third-party redistribution obligations.

Libretro documents [mGBA supporting GB/GBC/GBA](https://docs.libretro.com/library/mgba/)
and [Snes9x's noncommercial license](https://docs.libretro.com/library/snes9x/).
The application's original MIT license does **not** govern Snes9x.

## Evidence

| Check | State |
| --- | --- |
| Existing v2 functionality on Windows/macOS/Ubuntu | Maintainer confirmed completed |
| Package structure / imports | Refactor passed source checks and headless UI tests |
| Revised native core mapping | mGBA for GB/GBC/GBA; Snes9x for SNES |
| Targeted GB/GBC emulation with mGBA | Native Linux mGBA successfully loaded generated GB/GBC test ROMs and delivered video frames in CI; prior representative-game testing used Gambatte |
| macOS previous three-core notice/integrity packaging | Passed locally, before changing core mapping |
| Core source revision evidence | Build scripts now record versions and reported Git revisions; the [release core lock](CORE_RELEASE_PINNING.md) starts explicitly unapproved and checks exact fingerprint identity for future releases. Independent binary-to-source matching and archival remain pending |
| Python/native dependency and asset rights | Build scripts collect installed Python-wheel license files and versions for audit; native/transitive notices and asset rights still need independent review |
| Newly packaged two-core installers | Windows x64, macOS Apple Silicon and Intel, and Ubuntu/Debian x64 build and staged license/native core checks passed on GitHub Actions |
| Public publishing job and tag-triggered release builds | Disabled pending release clearance; a version tag alone must not package or publish binaries |

**Release-build control:** The checked-in [v2.0 core lock](../config/v2.0-core-lock.json) has `approved_for_binary_distribution: false`. When a future release workflow is enabled, `AP_RELEASE_BUILD=1` will require approved fingerprints at core download and again after package staging. Ordinary development builds remain available. The lock does **not** imply binary redistribution clearance. See [core release pinning](CORE_RELEASE_PINNING.md).

## Binary publication checklist

- [ ] Approve an exact mGBA and Snes9x build for each architecture and
      preserve its corresponding source code and full license notices.
- [ ] Freeze each approved binary by cryptographic hash and source revision;
      avoid mutable `latest` URLs for actual releases.
- [ ] Check the full Snes9x terms and embedded component notices for this
      explicitly noncommercial release.
- [ ] Confirm all bundled Python/native dependencies and app assets are
      redistributable with their required notices.
- [x] Verify native GB/GBC ROM loading and frame rendering with mGBA using generated homebrew test ROMs.
- [x] Verify 8 KiB MBC1 battery-backed raw `.sav` restore and persistence
      using the real mGBA core and generated GB/GBC test cartridges.
- [ ] Review other battery-backed mapper formats and representative real-game
      behavior as needed; the targeted MBC1 test is not blanket compatibility proof.
- [ ] Inspect the final two-core installers on Windows, macOS and Linux,
      including license files and core checksum manifest.
- [ ] Obtain release approval, restore a controlled publication mechanism,
      and publish signed/unsigned limitations accurately.

Targeted save compatibility: [GitHub Actions run 42163546612](https://github.com/MasynNay/anything-plays/actions/runs/42163546612) verified restoration and persistence of an existing raw 8 KiB MBC1 `.sav` in native mGBA, for both GB and GBC synthetic cartridges. Other mapper formats are not covered.

Latest platform package verification: [GitHub Actions run 42159955003](https://github.com/MasynNay/anything-plays/actions/runs/42159955003), which completed successfully on all four target architectures. These are automated packaging and native-core checks, not distribution authorization.

Do not create a v2.0 release tag or distribute bundled installers before
these items are resolved. The source code being publicly available on GitHub
does **not** mean the native installers have been cleared for redistribution.
