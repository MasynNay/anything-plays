# Third-party components and redistribution status

Anything Plays is an MIT-licensed application (for the original code whose
authors may grant that license). **The bundled application includes software
under other licenses; do not describe the complete installer as MIT-licensed or
wholly OSI-approved open source.** Official distributions will be free of
charge, with no advertising, subscriptions, donations or paid functionality.

## Emulator components packaged by v2.0

| System | Core | License | Authoritative information |
| --- | --- | --- | --- |
| GB / GBC / GBA | mGBA | MPL 2.0 | [Libretro mGBA](https://docs.libretro.com/library/mgba/) |
| SNES | Snes9x | Custom noncommercial terms | [Libretro Snes9x](https://docs.libretro.com/library/snes9x/) |

The build scripts bundle **two** native cores. mGBA supports Game Boy and Game
Boy Color as well as Game Boy Advance. Snes9x permits certain noncommercial
copying/distribution provided its full notices accompany copies. The terms of
each *actual binary* and its dependencies still need validation.

Earlier development builds bundled Gambatte under GPLv2. It is **not** part of
this release plan; its old license text is retained in `docs/history/` for
historical attribution. Moving from Gambatte to mGBA changes GB/GBC
emulation and requires targeted compatibility verification.

## Reproducibility and release inputs

Ordinary local development may fetch the latest matching Libretro nightly core.
The audited v2.0 candidate instead preserved all eight exact core ZIP archives
with verified SHA-256s, and upstream mGBA/Snes9x source snapshots at the
reported 40-character commits. The new private RC2 workflow restores the
original core ZIP bytes from the RC1 draft and verifies their archive and
extracted-library hashes *before* each build. See
[core pinning](CORE_RELEASE_PINNING.md) and the
[private candidate workflow](../.github/workflows/candidate-draft.yml).
Release-mode approval is still explicitly **false**, even when a package
build passes. The cores' reported Git revisions are not independent proof
of the buildbot compilation instructions or applied patches.

The source code, nightly artifacts and third-party license obligations
therefore remain separate verification dimensions; having the source
snapshot on GitHub does not automatically authorize redistributing the binary.

## Other third-party dependencies

The frozen application includes camera-capable
`opencv-python-headless`, NumPy, Pillow, sounddevice and platform-specific
dependencies such as PyObjC, plus transitive native libraries. Verified
four-platform headless candidate inventories contain **no bundled Qt GUI
libraries**; the Linux native-library count declined from 177 to 145.
Earlier RC2/RC3 headless builds still carried FFmpeg/media codecs, including
x264/x265 on Apple Silicon. The [fully checked private RC5](RC5_VERIFICATION.md)
instead uses four custom camera-capable headless OpenCV builds with FFmpeg
disabled; all four frozen inventories contain **zero** bundled FFmpeg/x264/x265
binaries. Their exact wheel hashes, source and the Windows packaging patch
are retained privately. This resolves that specific bundled media-codec
problem, **not** all native dependency obligations. The Linux inventory also
contains system-built GNU Readline, JACK, Berkeley DB and ALSA libraries:
the [RC5 ELF linkage audit](https://github.com/MasynNay/anything-plays/actions/runs/42257248885)
identifies their actual consumers for further licensing decisions.
The build scripts collect installed wheel license/notice files
under the packaged `licenses/python-distribution-notices/` directory and
write a version inventory to `licenses/PYTHON_DISTRIBUTIONS.json`. The
inventory includes **build-only packages**, so it does not prove which
libraries were actually frozen or whether native/transitive licenses are
fully satisfied. The source artwork and icon rights must also be confirmed.
Flexible source dependencies are declared in `../requirements.txt`; verified
packaging versions are pinned in `../requirements-build.txt`.

## Remaining binary publication requirements

- [ ] Verify that the mGBA and Snes9x versions shipped are licensed as stated.
- [ ] Confirm Snes9x's noncommercial redistribution conditions cover the
      complete intended distribution and respect all component notices.
- [x] Retain all eight exact core ZIPs with locked checksums and matching reported Git source snapshots in the private release candidate.
- [ ] Verify upstream buildbot binary-to-source correspondence independently and provide all required final-release source access.
- [ ] Review frozen dependencies, native libraries, and asset provenance.
- [ ] Inspect final Windows, macOS and Linux packages for complete notices,
      exact core hashes, source pointers and permitted content.
- [x] Verify GB/GBC native mGBA ROM loading and representative battery-backed save restoration using generated test ROMs.
- [x] Approve the exact reviewed free/nonpromotional v2.0.0 release separately from source integration; [scoped distribution decision](RELEASE_DISTRIBUTION_REVIEW.md).

**Status: [v2.0.0 is published](https://github.com/MasynNay/anything-plays/releases/tag/v2.0.0)** under a narrowly reviewed free/noncommercial distribution scope, with exact byte hashes and source/notice files attached. Independent upstream buildbot *reproducibility* remains an explicitly documented technical limitation, not a claim of unverified commercial rights. A successful `verify_bundle.py` only proves integrity, not copyright ownership.
