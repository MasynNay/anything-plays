# Anything Plays v2.0.0 binary-distribution review

This is the release's documented technical and permissions basis, not legal
advice and not an independent copyright audit of every upstream project.
Only the exact four installers listed in
[RC6_VERIFICATION.md](RC6_VERIFICATION.md) are included in this decision.

## Scope and conditions

The maintained Anything Plays 2.0 download is a free, noncommercial
distribution, with **no fees, advertisements, donations, subscriptions,
sponsorships, or paid promotion**. The project's original source is MIT
licensed, while the binary installer combines that source with separately
licensed components. No commercial-game ROM or BIOS file is intentionally
included.

The maintainer has stated that the commissioned betta artwork came with
purchased full ownership or commercial-use rights and was later recolored.
The artwork is **not** licensed under the software's MIT license and no
general right to reuse that artwork outside this application is claimed.

## Reviewed upstream conditions

- **Snes9x:** its exact upstream `LICENSE` explicitly grants
  noncommercial use, copying and binary/source distribution provided
  complete notices accompany the copies. It prohibits unrestricted
  commercial use, including promotion of other commercial products.
  The release is expressly free and nonpromotional, and the full
  Snes9x copyright/license notice is installed with the binary.
- **Snes9x NTSC component:** upstream marks `snes_ntsc` LGPL 2.1 and
  discusses exceptions for licensed components within Snes9x. The exact
  pinned upstream source snapshot and full LGPL text are attached and
  included in the application. Compatible Libretro native libraries are
  replaceable by the end user (see [source-access instructions](RELEASE_SOURCE_ACCESS.md)).
- **mGBA:** the exact pinned Libretro revision is available under MPL 2.0.
  The complete MPL license is bundled, and an upstream Git source
  snapshot at its reported revision is included in the release.
- **OpenCV:** exact `opencv-python-headless==4.14.0.94` source, four
  SHA-256-pinned wheels and a Windows source-packaging patch are
  preserved. Camera-only wheels were compiled with FFmpeg, GStreamer
  and Qt disabled. The final four staged native-file inventories show
  **no FFmpeg, x264, or x265 binaries**, eliminating the specific earlier
  media-codec transitive licensing problem.
- **Linux system libraries:** the final Debian installer no longer ships
  redundant bundled Readline, PortAudio, JACK, ALSA, or Berkeley DB binaries.
  Instead it depends on the distribution's own `libportaudio2` package.
- **Other Python dependencies:** installed exact versions and wheel
  license texts are included in the packaged `licenses/` directory;
  this does not grant broader redistribution permissions.

The eight emulator libraries matched independently preserved binary
SHA-256 fingerprints before being loaded and after installer packaging.
Their *reported* source revisions were verified to exist upstream and
the complete corresponding upstream Git trees are attached. These
upstream nightly binaries were **not independently reproduced from
source**, and this release makes no reproducible-build guarantee.
Anyone requiring byte-for-byte independently rebuilt emulator cores
should compile the included upstream source themselves.

## Distribution decision and safety bounds

The project is being prepared for public release in direct response to
the maintainer's request to finish and publish version 2.0 and the
maintainer's statement concerning commissioned artwork rights. The
permissions basis above is limited to the intended free/nonpromotional
release and is **not authorization for commercial reuse of Snes9x,
third-party code, or the betta artwork**.

The public release pipeline must compare the exact four installer SHA-256s
against the separately verified RC6 candidate, verify all archived native
Libretro core hashes and both source snapshots, and publish the full
license/source access notice. It may not substitute a changing nightly
binary or a newly built wheel, and it must not claim Windows signing or
Apple notarization. Any changed binary requires a new reviewed release.

All remaining legal interpretation questions are matters for the
copyright holders or qualified counsel; automated tests can verify bytes
and included notices but cannot make a legal guarantee.
