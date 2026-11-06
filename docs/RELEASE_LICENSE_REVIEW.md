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
| Core source revision evidence | Per-target core archives and hashes preserved in a [private draft](https://github.com/MasynNay/anything-plays/actions/runs/42173630332); exact upstream Git source snapshots preserved and verified in [run 42174478479](https://github.com/MasynNay/anything-plays/actions/runs/42174478479). Reproducible binary-to-source build correspondence is **not** independently proven |
| Python/native dependency and asset rights | Exact Python build distribution versions are pinned and wheel notices are collected. The owner attests purchased betta artwork rights. Native FFmpeg/codec and precise artwork-license-scope reviews remain open |
| Newly packaged two-core installers | Four actual installer archives and original emulator ZIPs were produced and verified in the [private RC1 draft workflow](https://github.com/MasynNay/anything-plays/actions/runs/42173630332); macOS DMGs and Linux DEB payloads were inspected after packaging |
| Public publishing job and tag-triggered release builds | Disabled pending release clearance; a version tag alone must not package or publish binaries |

**Release-build control:** The checked-in [v2.0 core lock](../config/v2.0-core-lock.json) has `approved_for_binary_distribution: false`. When a future release workflow is enabled, `AP_RELEASE_BUILD=1` will require both staged immutable ZIP archives through `AP_CORE_ARCHIVE_DIR` (never mutable-nightly network fallback) and approved fingerprints at core download and again after package staging. Ordinary development builds remain available. The lock does **not** imply binary redistribution clearance. See [core release pinning](CORE_RELEASE_PINNING.md).

## Release-candidate packaging defects discovered from audit artifacts

During the [four-platform inventory run](https://github.com/MasynNay/anything-plays/actions/runs/42169745287),
inspection of the actual staged native binaries found:

- **Windows Python mismatch:** Despite CI selecting Python 3.13, the Windows
  packaging script used the unqualified `py` launcher and froze Python 3.15
  extension binaries (for example, `_imaging.cp315-win_amd64.pyd`). The script
  has been changed to use a single explicit `python` executable from PATH,
  requiring Python 3.12 or 3.13, for core download, venv creation and final
  bundle verification. Subsequent [four-target CI](https://github.com/MasynNay/anything-plays/actions/runs/42172205627) confirmed Windows Python 3.13.
- **macOS core mutation after verification:** Both macOS inventory reports show
  that `codesign --deep` changed the nested emulator dylib sizes/hashes
  *after* their provenance hashes were verified. For example, the Apple
  Silicon mGBA binary changed from the candidate lock's 2,829,600 bytes to
  2,847,744 staged bytes, so its `CORE_PROVENANCE.json` could no longer
  verify the packaged bytes. The original nested `Contents/MacOS/cores` path
  also caused outer-only signing to fail because the JSON manifest was
  treated as executable content. The two cores and their manifest have moved
  into `Contents/Resources/cores`; runtime lookup and verification now agree
  on that location. Ad-hoc signing targets the outer app without `--deep`,
  followed by mandatory verification both after signing and after mounting
  the final DMG. Subsequent [four-target CI](https://github.com/MasynNay/anything-plays/actions/runs/42172205627) confirmed unchanged staged core hashes and macOS packaging.

Neither finding was visible from the older staged-bundle checks alone. The
updated checks reduce the chance of distributing a broken binary, but do not
alter third-party rights clearance or mark the distribution gate approved.

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

Latest complete four-platform *private candidate* verification: [GitHub Actions run 42173630332](https://github.com/MasynNay/anything-plays/actions/runs/42173630332), which produced all four installers, eight exact native ZIPs, four manifests, and draft-only checksums. The source snapshot job [42174478479](https://github.com/MasynNay/anything-plays/actions/runs/42174478479) added matching upstream Git tree archives. These are automated package and provenance checks, **not** third-party redistribution authorization.

An unapproved `v2.0.0-rc.1` **draft release** exists with all candidate inputs.
Do not publish a public `v2.0.0` tag or redistribute the bundled installers before
these items are resolved. The source code being publicly available on GitHub
does **not** mean the native installers have been cleared for redistribution.
