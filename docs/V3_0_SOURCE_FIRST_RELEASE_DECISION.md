# Anything Plays 3.0.0 — source-first distribution assessment and known limitations

**Scope:** exactly the eleven original-source Libretro libraries compiled in the successful four-platform build, not historical Stella/Snes9x/Genesis Plus GX previews.

This is an **engineering and maintainer distribution assessment** based on the actual source and binary identities. It is not legal advice, a warranty, or a claim that an independent lawyer approved each dependency. The project maintainer has repeatedly authorized publication of the free, open-source, noncommercial portfolio application with all four installers.

## Reproducible corresponding-source evidence

- [Four-platform original-source offline test and installer retention run 42686588072](https://github.com/MasynNay/anything-plays/actions/runs/42686588072): all four jobs passed, eleven exact original-source native modules installed into 18 offline console profiles, frozen desktop GUI, original noncommercial homebrew audio/video and seven sequential cross-console restarts.
- [Eleven exact original Git source archives run 42668367694](https://github.com/MasynNay/anything-plays/actions/runs/42668367694): SHA256-indexed source TARs with copyright notices and all 37 recursive Dolphin Gitlink source trees.
- [Current source/44 native hash verification run 42717944132](https://github.com/MasynNay/anything-plays/actions/runs/42717944132): each exact installed native digest matches the original compiler/source record across the four supported platforms. Workflow `.github/workflows/v30-current-tia-source-proof.yml` can reproduce the evidence and refuses obsolete Stella2014.
- Application source, library loader, dependency specifications, build scripts and packaged notice-copy rules remain publicly available in this Git repository at the release tag. A separate public original-source companion must precede the binary release. The main release's SHA256SUMS must match the **actual** four packaged `3.0.0` file bytes.

## What the license research actually establishes

The core modules are separately compiled upstream Libretro libraries, not one static library combining all emulator source. The MIT-licensed Python application opens one chosen module via `ctypes.CDLL`, registers Libretro ABI video/audio/input callbacks and shuts down the previous game session before starting another. Individual GPL modules may be subject to different license versions even when distributed together; whether plugin interaction is a GPL combined work is a substantive issue, not determined by one archive name.

- BlastEm original sources grant GPLv3 or later.
- Tia source files are SPDX GPL-2.0-or-later, replacing old GPLv2-only Stella2014.
- Supafaust, FCEUmm, Beetle PCE Fast, NeoPop, WonderSwan and other original Mednafen-derived files contain GPLv2-or-later grants. Their upstream `COPYING` files alone merely reproduce the GPLv2 text and do not by themselves prove every compiled file's precise grant.
- mGBA source is MPL 2.0; its bundled non-native optional resources and third-party files require their own applicable grants, not assumptions from the main library's license.
- ParaLLEl-N64 source build uses `HAVE_PARALLEL_RSP=0` and `HAVE_PARALLEL=0`; do not count uncompiled GNU Lightning code as necessarily present in the native runtime.
- Dolphin original-source builds for Windows, Linux and both Macs explicitly use `LIBRETRO=ON`, `ENABLE_QT=OFF` and `ENABLE_TESTS=OFF`. The original recursive source TAR contains Qt files with dual or alternative LGPL/GPL grants and GPLv2-only xxHash **test** files. Their existence in the corresponding-source archive is **not** proof these files are linked into the selected `dolphin_libretro` target. The GNU GPL FAQ's discussions of combined works and plugins still matter.
- Direct `DT_NEEDED` inspection of all eleven original native Linux ELF libraries found no emulator core that links directly to another `*_libretro.so`. This is strong evidence of separate native core objects, not a universal legal conclusion about the Python frontend and a loaded plugin.
- Neither historical Snes9x nor Genesis Plus GX with their noncommercial terms is in the verified selected 3.0 installer. Do not contact irrelevant upstream maintainers to clear these absent binaries.

**Compliance intent for actual publication:** retain every third-party copyright notice and original grant in the installer and matching public source archive; publish the application/build scripts and 11 upstream source TARs before the binary downloads; identify GPL/MIT/MPL components individually, do not relicense their source; include actual SHA256 digests, no ROM/firmware; state unsigned/not notarized Mac/Windows warnings where applicable. Publishing uses the open-source grants, not the mistaken premise that free use cancels GPL obligations.

## Honest release-quality acceptance

A stable **application version number** does not promise every commercial game works. Actual automated checks cover packaged GUI startup, offline core presence, original homebrew framebuffer and audio, and repeated session replacement. The maintainer has reported successful real-world N64/GameCube gameplay plus Windows, Linux, and Apple Silicon tests. We **do not** claim every commercial game, camera, device/audio combination, save-state format, Intel physical hardware, or uninterrupted multi-day run is verified.

Those remaining tests should be transparently disclosed and maintained as post-release compatibility work instead of being retroactively marked `True` in an unrelated exhaustive research manifest. Releasing a free open-source application does not legally require testing every commercial game, nor require notarization, though users should know operating-system security dialogs may appear.

## Outstanding scope and risk

Complete manual file-by-file transitive dependency examination and an independent legal opinion remain unavailable; source presence and successful native runtime tests cannot turn those historical research fields to `True`. Treat this as a source-first, documented GPL/MIT/MPL distribution decision with known limitations. If a concrete incompatible compiled file or missing source obligation is identified, correct the released assets promptly and document the change. Do not call uncertain compatibility guaranteed. Do not silently publish old preview binaries under stable names.

**The release procedure must fail closed on any missing final source archive, incorrect original 44 native source/installed hashes, missing four genuine `3.0.0` installer identities, broken SHA256 receipts, or source-first publication failure.** Stable 2.0.0 assets are immutable and out of scope.
