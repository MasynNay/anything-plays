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
- The checked-in branch may not yet contain the license/documentation updates
  prepared locally by the maintainer. Reconcile local uncommitted files before
  merging.

## Required decisions and evidence

- [ ] **Combined-work review.** Determine whether the in-process GPLv2
      Gambatte integration and the Snes9x noncommercial component can be
      distributed together. Obtain suitable copyright-holder permissions or
      change the architecture/cores if needed. Separating the binary into a
      different directory is not by itself a solution.
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
`develop/v2.0`. **Tags using the workflow already present on `main`
could still publish. Do not create or push version tags, or manually
publish installers, until this review is completed.** After the
requirements above are met, restore publishing with an intentional
release approval process.

## References

- [GNU GPL FAQ: combined works and plug-ins](https://www.gnu.org/licenses/gpl-faq.html)
- [Libretro core license overview](https://github.com/libretro/docs/blob/master/docs/development/licenses.md)
- [Libretro mGBA](https://docs.libretro.com/library/mgba/)
- [Libretro Snes9x](https://docs.libretro.com/library/snes9x/)

This is a technical compliance checklist, not legal advice or a legal opinion.
