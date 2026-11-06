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

## Assets and distribution materials

- The app icon, branding and other files under `assets/` require provenance:
  identify who created each asset, rights to publish and modify it, and
  third-party/trademark limitations.
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
