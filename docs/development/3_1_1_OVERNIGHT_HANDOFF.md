# Anything Plays 3.1.1 — Overnight engineering checkpoint

**Date:** November 11, 2026, America/Denver. **Scope:** Maintenance release ONLY; preserve published 3.1.0/3.0/RC2 intact.

## Release target

The [post-3.1 roadmap](../ROADMAP.md) lists 3.1.1 as a reliability update: real controller + camera acceptance, ROM loading/unloading, SRAM/native saves, clean installer behavior, safe shutdown and 30-minute representative soak tests. Do not claim compatibility for physical hardware that has not actually been exercised. Original source, eight release assets and license notices of v3.1.0 must remain immutable; any future 3.1.1 release needs its OWN source identity, complete four-platform installers, notices and checksum proof.

## 2026-11-11 22:00 Mountain — first actual 3.1.1 change

- Open [PR #235](https://github.com/MasynNay/anything-plays/pull/235), branch `feature/v3.1.1-camera-failure-isolation`, head `ee974b22f40a183a5b7e15a9b42f07d504487e7e`.
- Camera discovery fix `ff68f4104a8889dd14a40a79869ed1ea7b7dfb8a`: keep discovering later cameras if the VideoCapture constructor, isOpened/read or release fails, and skip phantom macOS camera probing when AVFoundation reports an empty list.
- Safe UI shutdown fix `4b452ab0553b924c73feb729b7185ed1387e010d`: detach webcam handle before calling native release, catch expected unplug/driver exceptions, always clear preview/stream/bezel and disarm controls. Recover native RuntimeError during initial camera open.
- New hardware-free [tests/test_v311_camera_failure_isolation.py](../../tests/test_v311_camera_failure_isolation.py) committed on PR as `ee974b22f40a183a5b7e15a9b42f07d504487e7e`. Tests inject native constructor/read/close failures, macOS zero-device state and live UI cleanup. These are synthetic tests, NOT real webcam hardware acceptance.
- CI launched: [Source checks](https://github.com/MasynNay/anything-plays/actions/runs/43159164164) and [four-platform source app identity](https://github.com/MasynNay/anything-plays/actions/runs/43159164217). Initial state queued; do not claim pass until GitHub reports green.

## Next exact steps

1. Review PR #235 CI. Fix any failed assertions/platform behavior. Merge **only after tests pass**; record tested merge SHA and CI links here.
2. Inspect any real save error recovery/ROM switching issue; implement a small, independently testable fix and re-run 3.12/3.13 and relevant native tests. Favor correctness, safety and data preservation over cosmetic changes.
3. Add bounded long-session stress tests, safe controller hotplug/focus recovery, read-only camera mock reliability, and platform-specific regression checks. Separate synthetic tests from genuine physical hardware.
4. Prepare `3.1.1` build identity/release notes/source notice preservation and full 18-profile/11-core four-OS verification; **do not clone/relabel old 3.1.0 binaries as 3.1.1**.
5. Publish a 3.1.1 stable release only if true source-built and installed acceptance, source-rights, checksum and complete installer evidence support it. Otherwise leave a clearly named private candidate and document blockers; never break public 3.1.0.

**Process:** Each subsequent overnight development run must APPEND a dated entry with actual code, commit SHA, verified CI outcome, outstanding issues and next work. Do not silently erase earlier checkpoints or invent an overnight completion.
