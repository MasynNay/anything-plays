# Anything Plays 3.2.0 — Full-native QA notes, NOT A PUBLIC RELEASE

**Unreleased owner-test version.** Public stable is still
[v3.1.1](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.1).

3.2 introduces guided first-run setup and local camera color/stability
calibration, controller and keyboard tutorials, live controller test and
per-console remapping, and portable versioned control-profile files. One
console or all 18 can be backed up, inspected, imported, reset and undone.
Persistence is protected against invalid controls, read-only disks and
failed refreshes, with explicit retry and conflict prompts. Custom zone
artwork caches are independent for each console. No ROM paths, camera frames,
credentials or saved-game files are included in portable controls.

The private full-native QA contains **11 native core families** for
**18 console profiles** on Linux, Windows, Intel macOS and Apple Silicon.
Actual installed/frozen app verification passed on revision
[`9f6950b`](https://github.com/MasynNay/anything-plays/commit/9f6950bc2a532375d2da5a6011571c9af11cf828).
The Linux original or pinned homebrew research probes recorded 18/18
positive software smokes. These are not retail-game compatibility or physical
hardware certifications. GameCube headless speed remains a research gap.

These side-by-side QA installers use a distinct **3.2 Preview** identity.
They do not update the stable app or migrate 3.1.1 settings or saves. Keep
your 3.1.1 installation. No commercial ROMs or firmware are included.
macOS is ad-hoc signed and not notarized; Windows may be unsigned.

**Not yet finished for public release:** true 3.1.1-to-3.2 upgrade packages,
3.2 native-redistribution/source approval, final checksum/source companions,
owner real-device/long-session verification and explicit release approval.

[Exact acceptance evidence](../V3_2_RELEASE_ACCEPTANCE.md) ·
[Private QA workflow](https://github.com/MasynNay/anything-plays/actions/runs/43728173563)

## Full-native stable-upgrade software QA (not distributable)

The separate exact-version 3.2.0 same-identity development channel passed
[private workflow 43734522415](https://github.com/MasynNay/anything-plays/actions/runs/43734522415)
on Linux, Windows, Intel Mac and Apple Silicon at source revision
`9ce5ec322a202fc111aaa2036794ee6a129e0c10`. The workflow builds a
source-authenticated 3.2 upgrade using the public stable 3.1.x package /
installer / bundle identity, replaces only the original-source 11-core
library set using SHA256-reviewed 3.1.1 files, and proves that an actual
frozen application launch preserves a **synthetic** old GBA profile, ROM
folder settings and fake save file. It never uploads its same-identity
upgrade installers.

This is not an installed real-user 3.1.1-to-3.2.0 migration, physical
controller acceptance, commercial-game save test, or approval of third-party
redistribution. Private full-native Preview installers remain the only
3.2 packages offered for direct testing. Public 3.1.1 remains unchanged.
