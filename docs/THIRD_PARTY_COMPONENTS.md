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

## Known reproducibility gap

`fetch_mgba_core.py` currently downloads the latest matching Libretro
nightly archives. It writes `cores/CORE_PROVENANCE.json` with the download URL,
SHA-256, file size, embedded Libretro library version, and any source revision
reported by the library itself. Verification compares these recorded fields
against the staged binary. These are **self-reported source identifiers**, not
independent build reproducibility or proof that no patch was applied.
Release-mode checks now also require the explicit, initially unapproved
[core fingerprint lock](CORE_RELEASE_PINNING.md). That lock will reject changed
or unapproved cores; it does not turn changing nightly URLs into immutable
build inputs. Approval still requires preserving binary archives, verifying
corresponding source and licensing, and locking inputs for every supported
architecture.

## Other third-party dependencies

The frozen application includes OpenCV, NumPy, Pillow, sounddevice and
platform-specific dependencies such as PyObjC, plus transitive native
libraries. The build scripts collect installed wheel license/notice files
under the packaged `licenses/python-distribution-notices/` directory and
write a version inventory to `licenses/PYTHON_DISTRIBUTIONS.json`. The
inventory includes **build-only packages**, so it does not prove which
libraries were actually frozen or whether native/transitive licenses are
fully satisfied. The source artwork and icon rights must also be confirmed.
The dependency ranges are declared in `../requirements.txt`.

## Remaining binary publication requirements

- [ ] Verify that the mGBA and Snes9x versions shipped are licensed as stated.
- [ ] Confirm Snes9x's noncommercial redistribution conditions cover the
      complete intended distribution and respect all component notices.
- [ ] Identify corresponding source revisions for each shipped platform binary,
      provide any required source, and lock checksums/versions.
- [ ] Review frozen dependencies, native libraries, and asset provenance.
- [ ] Inspect final Windows, macOS and Linux packages for complete notices,
      exact core hashes, source pointers and permitted content.
- [ ] Validate the GB/GBC mGBA core transition with focused tests.
- [ ] Approve publication separately from source integration.

**Status: binary release clearance is not complete.** See the
[redistribution audit](REDISTRIBUTION_AUDIT.md) for the complete outstanding
Snes9x, MPL, native-library and asset-rights checks. A successful
`verify_bundle.py` run proves the presence/integrity of required files,
not the copyright status of those files.
