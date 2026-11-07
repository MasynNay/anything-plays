# In-app emulator core updates — 2.1 engineering contract

Anything Plays ships usable emulator core binaries **inside** every supported
desktop installer. Users never need to install RetroArch, Dolphin, or another
emulator application, and they can continue playing offline.

## What the buttons do

- **Check emulator updates:** checks each of the 11 unique installed native
  cores (not 18 duplicate downloads) and separately checks the Anything
  Plays GitHub releases for approved, platform-matched core packs.
- **Install approved updates:** after one confirmation, downloads and checks
  packs inside Anything Plays. No browser download or external installer.
  A currently running ROM must be unloaded first.
- **Restore bundled:** switches a selected console back to its previously
  verified core or to the original core shipped inside the installer.
  Previously installed native objects are retained for rollback.

A successful core update **does not close the application**. The launcher
reselects the active verified core the next time a ROM is loaded. Existing
game saves, per-console profiles, camera settings, themes, and ROM folders
remain unchanged. A native library currently in use is never overwritten.

## Update trust model and fail-closed rules

The program **never installs arbitrary nightly Libretro ZIP files**.

Independent updates must come from a published `v2.1.x` release under
`MasynNay/anything-plays`, with exact asset names
`AnythingPlays21-Core-<core>-<platform>.zip` and a GitHub release-asset
`sha256:` digest. A candidate is rejected if its size, HTTPS origin,
platform, format, archive members, unpacked binary SHA-256, source
repository, or explicit license/runtime-review claims do not match.

The code downloads complete archives with bounded sizes, never extracts
untrusted ZIP paths, and stores immutable binaries under the user's app
data directory. A small active JSON pointer is atomically updated; hash
mismatch, corruption, or a missing native object falls back to the bundled
original. An update in flight blocks new ROM launches, but not the rest of
the UI. A user can roll back without reinstalling the app.

This is trust in the **official repository's GitHub release and GitHub's
authenticated asset digest**, not an independent offline developer
signature. A production release must additionally audit platform code
signatures/notarization, legal distribution rights, real-game compatibility
and the entire installed-app update path.

**GameCube exception:** Dolphin depends on matching `dolphin-emu/Sys`
assets and its GPU renderer is not yet release-ready. The updater still
checks Dolphin's upstream source, but it must update together with a vetted
complete application bundle until a safe paired-core/Sys pack is designed.

## Maintainer release process

Run `python tools/create_core_packs.py --release v2.1.0-alpha.2`
against a provenance-verified core directory to build **UNAPPROVED**
candidate packs. These are explicitly rejected by the in-app installer.

Only after verifying each core's source/license and installed gameplay
(including camera buttons, saves and long-running operation) on the exact
target architecture, rebuild with both
`--license-reviewed --runtime-tested`. Review the produced ZIP content and
SHA-256. Upload only the accepted per-core ZIPs to the matching public
Anything Plays 2.1 release as manually approved assets. The app discovers
only those published, reviewed releases; mere upstream activity doesn't
trigger execution of new binaries.

CI packaging or a green unit-test suite **does not constitute approval**.
Current 2.1 alpha releases do not automatically publish emulator updates.
All 18 consoles must still pass the release acceptance gate.
