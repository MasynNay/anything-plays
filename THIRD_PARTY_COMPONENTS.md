# Third-party components and redistribution review

Anything Plays includes third-party Python libraries and (in packaged builds)
native emulator cores. **This file is an inventory, not a declaration that
redistribution obligations have been satisfied.** It does not replace upstream
license texts, a corresponding-source offer, or review of combined-work terms.

## Native Libretro cores

| Core | Used for | License identified by Libretro | Upstream information |
| :-- | :-- | :-- | :-- |
| Gambatte | GB, GBC | GPLv2 | [Libretro Gambatte documentation](https://docs.libretro.com/library/gambatte/) |
| mGBA | GBA | MPL 2.0 | [Libretro mGBA documentation](https://docs.libretro.com/library/mgba/) |
| Snes9x | SNES | Non-commercial terms | [Libretro Snes9x documentation](https://docs.libretro.com/library/snes9x/) |

The exact license terms attached to a **specific downloaded binary**, its
copyright notices, source availability, and permitted uses must be inspected
before redistribution. Snes9x's non-commercial condition must be respected.
Because Gambatte is GPL-covered, the integration and distribution of the
combined application warrants a separate license-compliance review.

The downloader obtains the latest matching Libretro nightly packages. Each
build's `cores/CORE_PROVENANCE.json` lists its downloaded source URL and
SHA-256 hash. **Hashes establish what was downloaded, not which source commit
produced it.** Pinning source revisions and keeping corresponding-source
materials are still outstanding release tasks.

## Python dependencies

The application depends on OpenCV, NumPy, Pillow, SoundDevice and, on macOS,
PyObjC's AVFoundation bridge. Their license texts and any redistributable
native libraries must be reviewed for the actual versions collected by
PyInstaller. See `requirements.txt` for declared dependency ranges; a release
build may resolve newer patch versions than a previous build.

## Release checklist for third-party compliance

- [ ] Identify exact upstream version and corresponding source for **every**
  shipped native core; review their actual license texts and notices.
- [ ] Resolve GPL-related combined-distribution obligations for Gambatte and
  the application's own licensing plan.
- [ ] Confirm that the intended no-monetization release complies with Snes9x's
  full non-commercial terms.
- [ ] Include required third-party copyright notices and license texts in
  every installable artifact.
- [ ] Make required source material or a compliant source offer available.
- [ ] Review Python dependencies, images, icons and any other bundled assets.
- [ ] Verify final packages, test on target OSes, and approve publication.

Anything Plays is intended to be free and non-commercial. This does not make
unlicensed original source automatically open source. No project-level license
grant has yet been selected.
