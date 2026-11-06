# v2.0 redistribution clearance (not yet approved)

This is a release gate, not a declaration that the project or bundled
emulator cores are cleared for redistribution. Official builds are intended
to be free of charge. Noncommercial distribution does not remove the license
conditions of third-party code.

## Current integration

- `systems.py` selects Gambatte for Game Boy and Game Boy Color, mGBA
  for Game Boy Advance, and Snes9x for SNES.
- `gba_emulator.py` loads a native Libretro library with `ctypes.CDLL`.
  This is in-process integration, not an independent command-line program.
- The downloader `fetch_mgba_core.py` currently fetches `/latest/`
  nightlies; it records resulting hashes but **not** matching source commits.
- The three build scripts bundle all three core binaries in platform installers.
- Project and core license texts are committed to `develop/v2.0` and copied
  into all three platform packages. `verify_bundle.py` checks presence and
  matches packaged core hashes to the generated manifest; this is **not** a
  compatibility, source-availability, or license-compliance audit.

## Current evidence (as of November 2026)

| Check | Verified finding | Release implication |
| --- | --- | --- |
| Original code license | MIT license file committed | Applies only to code whose contributors may grant it |
| Packaging instructions | Windows, macOS and Linux scripts stage core licenses and notices | The staged outputs still need artifact inspection on each OS |
| macOS Apple Silicon package | Local rebuild reported that staging verification and DMG creation succeeded | Confirms files and checksums for that build, not legal clearance or notarization |
| Windows and Ubuntu | Maintainer supplied EXE and DEB artifacts and confirmed successful application testing | Functional testing is complete; updated license-file packaging alone is not independently verified |
| Core provenance | Buildbot `latest` nightlies with post-download SHA-256 | Corresponding source revisions not established; not reproducible |
| Third-party rights | Gambatte GPLv2, mGBA MPL 2.0, Snes9x noncommercial | Combined-work and specific redistribution obligations still outstanding |

**Naming:** The original Anything Plays source is MIT-licensed. The complete
bundle includes noncommercial Snes9x; do not represent every bundled component
as OSI-approved open source or apply MIT to those third-party binaries.

**Cross-platform functional testing is complete.** The maintainer provided the
Windows EXE, macOS DMG and Linux DEB and confirmed they work. Do not request
more gameplay testing merely because documentation, notices or CI changed.
If required, validate only the modified packaging contents independently.

## Required decisions and evidence

- [ ] **Combined-work review — release blocker.** Determine whether the
      in-process GPLv2 Gambatte integration and Snes9x's noncommercial terms
      can be distributed together. Seek qualified open-source licensing review
      or relevant rights-holder permission, or test an appropriately licensed
      alternative to Gambatte (for example SameBoy). A separate file directory
      or a free download does not itself resolve this issue.
- [ ] **Gambatte.** Identify the exact core build, its source revision,
      complete GPL notices, and corresponding source obligations.
- [ ] **mGBA.** Identify the exact core build and source revision; make
      MPL-covered source and notices accessible as required.
- [ ] **Snes9x.** Check the full notices and noncommercial terms for the
      exact Libretro build, and confirm the planned distribution is authorized.
- [ ] **Dependencies and assets.** Inventory the versions and notices for
      frozen Python/native dependencies and packaged assets on all OSes.
- [ ] **Installer contents.** Ship all notices, required licenses and
      corresponding-source information in each installer. Check the actual
      built artifacts, not only the scripts.
- [ ] **Release immutability.** Lock approved core binaries by target
      architecture and SHA-256 before release. Preserve source archives
      and a verifiable build/source mapping.
- [ ] **Testing and approval.** Complete application smoke tests on Windows
      x64, macOS arm64/x86_64, Linux x64, and explicitly authorize publication.

## Automatic publishing safeguard

The `publish` job in `.github/workflows/release.yml` is disabled on
`develop/v2.0`. **It is acceptable to merge the verified v2 source into
`main` without publishing new binaries; this does not constitute release
licensing approval.** Before merging, confirm that the disabled job will
remain disabled on `main`. Until that merge is complete, pushing a version tag
based on the old `main` may still publish. Do not create version tags or
manually publish installers until redistribution review is completed.

## References

- [GNU GPL FAQ: combined works and plug-ins](https://www.gnu.org/licenses/gpl-faq.html)
- [Libretro core license overview](https://github.com/libretro/docs/blob/master/docs/development/licenses.md)
- [Libretro mGBA](https://docs.libretro.com/library/mgba/)
- [Libretro Snes9x](https://docs.libretro.com/library/snes9x/)

This is a technical compliance checklist, not legal advice or a legal opinion.
