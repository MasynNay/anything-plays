# Anything Plays v3.1.0 — Stable public release operator checkpoint

**Approved publication scope:** one public `v3.1.0` GitHub Release containing four native, source-verified full 18-console installers and four other immutable evidence/source assets. The release is free, noncommercial and nonpromotional. Preserve public v3.0, public 3.1 RC2, and all earlier versions.

## Exact release identities

- Application source SHA: `104b96621ec4cb8dc39fde8c3fe96fc854c406ed`.
- Actual original final four-platform QA: [run 43140637755](https://github.com/MasynNay/anything-plays/actions/runs/43140637755), 13/13 jobs passed.
- Source and original SHA-pinned binary stage: [run 43142249044](https://github.com/MasynNay/anything-plays/actions/runs/43142249044), exact seven files, four clean native FFmpeg-disabled OpenCV wheels.
- Original pygame/SDL/mpg123 source ZIP: [run 43152661067](https://github.com/MasynNay/anything-plays/actions/runs/43152661067). This must become the eighth release asset and must match its original staged sha256.
- Source + all eight immutable release files: [read-only preflight passed](https://github.com/MasynNay/anything-plays/actions/runs/43153670927).
- The older private draft ID `442346875` has **old stock OpenCV binaries**. [Write-scoped draft access passed](https://github.com/MasynNay/anything-plays/actions/runs/43154143521); the `v3.1.0` Git tag did not yet exist. The protected workflow must replace the draft's seven old files with **exactly eight** verified new files, then publish from the source SHA above, not rename RC2 or reuse older binary bytes.

## Explicit release conditions

- Every true rights/source/rollout acceptance gate and owner approval are recorded in `config/v3.1-release-readiness.json` and the [scoped free/noncommercial distribution decision](V3_1_SCOPED_DISTRIBUTION_DECISION.md).
- The real physical camera/gamepad/retail-game and endurance tests are not certified and must remain reported as unverified in release notes; do not convert virtual tests into physical passes. [Disclosure](V3_1_HARDWARE_QA_SCOPE.md).
- Check [release source companion](V3_1_SOURCE_COMPANION.md) for native source/replacement instructions and original upstream notices, and [public original-core sources](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources).
- Only [the protected stable-publication GitHub Actions workflow](../.github/workflows/v31-publish-cleared-clean-stable.yml) may promote the owner-only draft. It verifies source, original receipts, every downloadable SHA256 and eight-asset identity both before and after upload. Any mismatch fails before public release.
- After the final GitHub Release reports `draft=false`, verify it is anonymously downloadable and then update the portfolio and README links, preserving public stable 3.0 and RC2 for rollback.

**This checkpoint records authorization and the exact deployment inputs; it is not an assertion that the release was public before the GitHub Actions publication job completes.**
