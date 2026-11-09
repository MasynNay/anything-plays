# Anything Plays 2.1: small installer and optional emulator downloads

The **starter application** includes **mGBA only** for Game Boy, Game Boy
Color and Game Boy Advance. Other consoles remain visible in the selector:
their buttons offer **Download emulator** until the appropriate core is
installed. Shared console families reuse a single downloaded library.

Downloads happen **inside Anything Plays**, without a browser, RetroArch,
standalone Dolphin or any separate emulator installer. Only official,
platform-matched, publicly released 2.1 core packs with GitHub SHA-256
asset digests are accepted. The app checks archive membership, verified
binary digest, reviewed source and license metadata, binary format and
runtime-test attestation. An immutable user-data object is atomically
activated between ROM sessions. Previously installed cores can be rolled
back without restarting Anything Plays.

**Publishing is a separate approval step.** The 2.1 CI workflow produces
UNAPPROVED, independent core-pack candidate ZIP artifacts for Windows,
both macOS architectures and Linux. These cannot be downloaded into the app
until maintainers approve and publish them in an official 2.1 release after
real game, audio, controls, camera, save, performance, signing and license
verification. A missing approved pack is clearly reported; the app never
falls back to arbitrary nightly executable downloads.

**GameCube stays explicitly unavailable for one-click install** while
Dolphin's native video renderer crashes or produces black frames. It also
requires matching `dolphin-emu/Sys` assets. A standalone Dolphin library
cannot be advertised as an independently playable package.

Build flags on the 2.1 branch:

- `AP_V21_MINIMAL_CORE_BUILD=1`: starter app ships mGBA only.
- `AP_V21_TEST_CORES=1`: all 11 cores for isolated test runners and optional
  candidate downloads. This does NOT imply all games work.
- Neither flag: unchanged approved v2.0 two-core configuration.

No copyrighted ROMs, firmware or commercial game files are distributed.
Users provide legally obtained game files. Release readiness and native
audio compatibility remain gated on platform-specific gameplay tests.
