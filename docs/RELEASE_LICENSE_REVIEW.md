# v2.0 binary release readiness

**Application functionality:** The maintainer supplied Windows EXE, macOS
DMG and Linux DEB installers and confirmed that v2.0 worked on all three
operating systems. This prior gameplay testing is complete and should not be
repeated merely for changes to documentation.

**Source:** The v2.0 application is merged into `main`. Original code is
licensed under MIT (where contributors have rights to grant that license).

**Binary distribution:** Not yet approved. This record is technical evidence,
not legal advice or a claim of copyright clearance.

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
| Exact corresponding source commits for downloaded binaries | Not established |
| Python/native dependency and asset rights | Not fully audited |
| Newly packaged two-core installers | Windows x64, macOS Apple Silicon and Intel, and Ubuntu/Debian x64 build and staged license/native core checks passed on GitHub Actions |
| Public publishing job | Disabled pending release clearance |

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
- [ ] Verify compatibility of existing GB/GBC battery-backed `.sav` files with mGBA and representative real-game behavior.
- [ ] Inspect the final two-core installers on Windows, macOS and Linux,
      including license files and core checksum manifest.
- [ ] Obtain release approval, restore a controlled publication mechanism,
      and publish signed/unsigned limitations accurately.

Latest platform package verification: [GitHub Actions run 42159955003](https://github.com/MasynNay/anything-plays/actions/runs/42159955003).

Do not create a v2.0 release tag or distribute bundled installers before
these items are resolved. The source code being publicly available on GitHub
does **not** mean the native installers have been cleared for redistribution.
