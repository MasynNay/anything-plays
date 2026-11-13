# Anything Plays 3.1.1 — Stable release candidate checklist

**Development only. Not published.** This file accompanies [draft integration PR #239](https://github.com/MasynNay/anything-plays/pull/239) and documents the exact path from the successful reliability tests to an honest full public 3.1.1 maintenance release. The public [stable 3.1.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0) stays unchanged.

## Verified 3.1.1 code changes (combined development integration)

- Camera failure isolation, safe control disarm and Tk timer shutdown behavior [PR #235](https://github.com/MasynNay/anything-plays/pull/235)
- Colliding independent SRAM save writes: unique temporary files, fsync, atomic replacement and bounded retry for transient Windows file-sharing denial [PR #236](https://github.com/MasynNay/anything-plays/pull/236)
- Controller device enumeration and partial SDL startup/shutdown isolation, reconnect/focus safety [PR #237](https://github.com/MasynNay/anything-plays/pull/237)
- Unreadable/symlinked ROM shelf/art folders handled without losing healthy sibling titles [PR #238](https://github.com/MasynNay/anything-plays/pull/238)
- Synthetic virtual 30-minute controller/hotplug/save checks and real wall-clock Linux Tk/SDL/OpenCV 180-second UI soak; **do not** conflate simulated time with physical hardware testing
- QA hardening: early app exit, missed resource samples and hidden Tk callback exceptions must fail the soak
- Robust macOS temporary DMG detach: accept only a confirmed unmount; a genuinely still-mounted drive remains an error

**Existing independent combined evidence, before the new installer work:** [Python source checks](https://github.com/MasynNay/anything-plays/actions/runs/43297910539), [native controller](https://github.com/MasynNay/anything-plays/actions/runs/43297910626), [native webcam recovery](https://github.com/MasynNay/anything-plays/actions/runs/43297910554), [save durability](https://github.com/MasynNay/anything-plays/actions/runs/43297910522), [ROM shelf](https://github.com/MasynNay/anything-plays/actions/runs/43297910509), [five-job extended synthetic session](https://github.com/MasynNay/anything-plays/actions/runs/43297910614) all **passed** on source revision `61ec6dc0c6d4bbfe833a9fa0ba866e915c3f47f7`. They do **not** certify later 3.1.1 release package revisions.

## New native source and full installer staging

The [dedicated 3.1.1 four-platform QA workflow](https://github.com/MasynNay/anything-plays/blob/feature/v3.1.1-integration-qa/.github/workflows/v311-private-source-stage.yml) now implements this planned dependency chain:

1. Fresh Python 3.13 native builds, not relabeled 3.1.0 executables, for Linux x64, Windows x64, Mac ARM64 and Mac x64. Initial build identity is `3.1.1 / v311_candidate` with isolated `anything-plays-311-candidate` preferences and packages. These mGBA-only shells are **not** releasable.
2. The exact original, separately built camera-only OpenCV 4.14.0.94 wheel for each native architecture, with SHA-pinned upstream original source `4afa2ea1214453648be88259f035712454faa9039b686de7753569ba8eec1577`. Require FFmpeg disabled, native camera backend present and immutable wheel source/ABI evidence.
3. Independently retrieve published stable 3.1.0 original source-built cores and notices by *exact* verified release SHA256 for each OS. Copy **all 11 core families/18 console profiles unchanged** into the new 3.1.1 program and verify the installed DEB/EXE/signed DMG native payloads. Preserve the new app's pygame/SDL/OpenCV runtime and its own notices; never overwrite stable 3.1.0.
4. Upload private original full-installation QA receipts and matching SHA256 hashes only to CI artifacts, with explicit `public_release_approved:false`.

## Must be completed before ANY public stable 3.1.1 publication

- [ ] Four source-shell jobs and all four complete-core packaging jobs **pass on the same immutable 3.1.1 source SHA**, including direct installed program startup, save/load and preferences checks on Windows, Linux and both Macs. Source-shell jobs alone do not count.
- [ ] A separate **true 3.1.1 stable installation identity** is built and verified: user-facing installers must use `3.1.1`, share the established stable 3.1 preferences namespace `anything-plays-31` and update the stable installation, **not** retain the isolated `v311_candidate` identity or `3.1.1-qa1` filenames. All final installers must be rebuilt and checked from this reviewed final source.
- [ ] Native source/notice check certifies unchanged libretro original-source core hashes and that the inherited pygame-ce, SDL and mpg123 libraries have corresponding source/rebuild/replacement access via the approved 3.1.0 source companion, with any new version-specific amendments retained durably.
- [ ] Genuine target-version package identity and source mapping receipts, a complete public SHA256SUMS, regression pass and named version-specific release notes are verified against the actual final installer bytes.
- [ ] Physical controller, live webcam, retail ROM save/audio and long-session test limitations are explicitly disclosed if untested, without substituting synthetic tests for device acceptance.
- [ ] Publish a **new tag v3.1.1** only after these gates pass, verify real anonymous public availability and each upload checksum, then update the website/README. Never republish, delete or mutate the existing 3.1.0/3.0/RC2 downloads.

### Planned public-release changes

**What's improved:** safer unplugged or failing cameras; controller hotplug recovery and released inputs after SDL errors; crash-resistant unique game-save writes and transient Windows sharing-conflict retry; resilient ROM and artwork directory scanning; longer-session UI timer and memory regressions.

**Unchanged:** 18 offline console profiles, 11 native emulator core families, Stream Mode and 16 themes, local/private camera capture, save locations and original source/copyright restrictions.

**Not promised:** real hardware acceptance on untested machines, Apple notarization, flawless GameCube performance or identical compatibility for every retail game.

**Current status:** 3.1.1 remains in active development, not publicly downloadable. Review the latest [GitHub Actions jobs](https://github.com/MasynNay/anything-plays/actions/workflows/v311-private-source-stage.yml) before claiming the new source/full installers pass.
