# Anything Plays 3.2.0 — Public release and QA evidence

**PUBLIC STABLE RELEASE — November 15, 2026.** [Anything Plays 3.2.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.2.0) was published following merged PR #244, exact four-platform [release candidate verification](https://github.com/MasynNay/anything-plays/actions/runs/43742977770) and successful [publication workflow](https://github.com/MasynNay/anything-plays/actions/runs/43743526029).

The actual public release includes **four internally versioned 3.2.0 full-native installers**, original source access, SHA-256 sums and QA manifest. The original 3.1.1 download remains unchanged and available. The published source tag identifies `0c4db50ede64646cecbadd400dd54f0ae76166c9`.

**Scope:** Free and noncommercial/nonpromotional, with separately licensed third-party components. Native CI verified the 3.1.1-to-3.2 upgrade process on all four OSes; installed real-game progress, physical webcam/gamepad/speaker combinations, extended retail gameplay and independent transitive-license auditing are **not universally verified**. The scoped owner authorization is in [`config/v3.2-publication-authorization.json`](../config/v3.2-publication-authorization.json). See the [public release notes](releases/ANYTHING_PLAYS_V3_2_PUBLIC_NOTES.md) and the release's attached source review.

## Historical pre-publication QA freeze

The remaining material documents the **pre-publication** acceptance evidence and outstanding broad hardware/compliance research as it stood before release. Its earlier hold status is preserved for audit, not a statement that 3.2.0 is still unreleased. The legacy `config/v3.2-release-readiness.json` and `check_v32_release_readiness` implement a stricter *universal* acceptance gate and are archival; the public release used an explicit scoped authorization with disclosures.

## Exact tested evidence

| Gate | Result |
| --- | --- |
| Source revision | `9f6950bc2a532375d2da5a6011571c9af11cf828` |
| Python 3.12/3.13, Tk and mGBA | [Run 43728173567](https://github.com/MasynNay/anything-plays/actions/runs/43728173567), passed |
| Linux/Windows/Intel Mac/Apple Silicon frozen installed apps | [Run 43728173563](https://github.com/MasynNay/anything-plays/actions/runs/43728173563), all four passed |
| Full-native private preview inventory | 11 native core families, 18 console profiles |
| Same-identity full-native stable-upgrade QA | [Run 43734522415](https://github.com/MasynNay/anything-plays/actions/runs/43734522415), all four platforms passed at source `9ce5ec322a202fc111aaa2036794ee6a129e0c10` |
| Synthetic 3.1.1 settings/save preservation | Passed actual frozen-app startup for all four private full-native upgrade packages; no real user saves tested |
| In-place native OS upgrade rehearsal | [Run 43735551340](https://github.com/MasynNay/anything-plays/actions/runs/43735551340), all four passed at exact source `0da314541e2c6e9f739ca2add2e8001bbfb8a9d0` |
| Real saved-game continuity with playable ROMs | Not verified; an unchanged synthetic save canary is not a gameplay save test |
| Linux bounded original / pinned homebrew software smoke | 18/18 positive profiles |
| Real physical webcam/controller, retail games and extended saves | Not verified |
| Independent 3.2 distribution/source approval | Not approved |

The private installed artifacts include separate full-native QA bundles for
`linux-x64`, `windows-x64`, `macos-arm64` and `macos-x64`. Their archived
GitHub Actions artifacts expire **November 22, 2026**, and contain exact-source
installer hashes and frozen-GUI receipts. They retain the separate 3.2 preview
installation identity and `anything-plays-32-preview` settings namespace.
**These preview packages are not a stable 3.1.1-to-3.2 upgrade.** The
separate unpublished same-identity upgrade QA workflow passed on all four
operating systems with eleven original/native core families and synthetic
prior 3.1.1 data. No old user saves or settings were imported from a real
installation, and no user ROMs or BIOS files are shipped. For safety, the
same-identity private upgrade installers are **not uploaded or distributed**;
only original-source and frozen-app test receipts are retained.

The 18 homebrew positives come from bounded Linux native software programs,
not commercial games or hardware tests across every OS. GameCube's separate
native audio research produced nonzero PCM, but the combined homebrew release
matrix did **not** meet the headless 20 FPS threshold or validate physical
speaker output. Do not advertise universal compatibility or performance.

## 3.2 feature scope completed

The Get started launchpad, measured camera calibration/jitter guidance,
controller and keyboard onboarding/remapping, privacy-safe diagnostics,
portable single-console and 18-console controls backup/import/undo, reset
and Undo reset, per-console artwork, stored-profile rollback, and disarmed
camera/controller safety checks are implemented. Full package CI has passed;
source tests verify import/undo recovery under failed disk writes.

## Prepublication acceptance checklist and ongoing field-research limits

1. Complete **real game-save and ROM-library continuity acceptance** after
   upgrading 3.1.1 to 3.2. The private
   `AP_V32_STABLE_CANDIDATE=1` channel already preserves the original
   Linux package/launcher, Windows Inno AppId and Mac bundle ID and includes
   eleven checksum-verified original native core families. Exact-source
   [run 43735551340](https://github.com/MasynNay/anything-plays/actions/runs/43735551340)
   passed four genuine **disposable old-then-new installation rehearsals**:
   Linux used an isolated `dpkg --root` database, Windows used in-place
   Inno Setup, and each Mac replaced `AnythingPlays31.app` in a temporary
   Applications directory. The actual new frozen applications preserved
   synthetic old GBA controls, preferences/ROM directory metadata and
   byte-exact fake save files. This does **not** prove real games can reload
   3.1.1 saves, match performance or restore library progress. The
   same-identity packages remain withheld and not approved for public use.
2. Independently review full native-core redistribution rights, original
   notices, current Python/SDL/OpenCV runtime provenance, corresponding
   source/replacement rights, and finalized artifact SHA256 checksums.
3. Review real webcam/color tracking, USB/Bluetooth controller mapping,
   hotplug, keyboard-only play, and sustained legal-game/save testing on
   owner hardware. Report GameCube GPU/audio limits separately.
4. Obtain explicit approval of the **exact final tested source revision,
   final stable installer hashes, source companion, and release scope**.
   Publish a new version without replacing or deleting v3.1.1.

Historical universal-acceptance checklist (separate from the scoped published release):
`python -m tools.check_v32_release_readiness --require-public-ready`.
The command remains intentionally strict until every broader hardware and research gate
in [`config/v3.2-release-readiness.json`](../config/v3.2-release-readiness.json)
are individually reviewed. A green CI badge never flips these flags.

[Full 3.2 QA release notes](releases/ANYTHING_PLAYS_V3_2_FULL_NATIVE_QA_NOT_RELEASE.md)
