# Anything Plays 3.1 RC1 — Four OS upstream pygame native replacement trial

**Verified November 10, 2026. Strict technical evidence only, not full LGPL 2.1 Section 6 review or stable 3.1.0 approval.**

The existing public RC1 installers were independently verified against
their immutable four-platform source-first QA run, and only **disposable
copied installations** were changed. Each candidate used the official,
versioned, SHA256-pinned **pygame-ce 2.5.8 CPython 3.13 wheel** for
its architecture. No user's files, real profile, ROMs or stable 3.0
installation were changed.

| OS target | Original full RC1 | Original wheel pygame extension swap into copied app | Actual copied frozen Tk GUI started | Isolated old 3.0 settings preserved | Result |
| --- | --- | --- | --- | --- | --- |
| Windows x64 | Authentic EXE | Pinned exact original wheel base.pyd | PASS | PASS | PASS |
| Linux x64 | Authentic DEB | Pinned exact original wheel base.so | PASS | PASS | PASS |
| Mac Apple Silicon | Authentic signed DMG | Pinned original wheel base.so ARM slice; re-signed copy | PASS | PASS (separate RC1 GUI acceptance) | PASS |
| Mac Intel | Authentic signed DMG | Pinned original wheel base.so Intel slice; re-signed copy | PASS | PASS (separate RC1 GUI acceptance) | PASS |

- [Linux and Windows two-runner native swap test](https://github.com/MasynNay/anything-plays/actions/runs/42937982305) — passed. Both original frozen applications were unpacked from genuine pinned RC1 installer packages, checked against original core/SDL receipts, copied to a new directory, had the corresponding upstream pygame native extension placed in the copied frozen app, and ran their real Tk startup test. The four-platform installed UI verifier established that all **18 console profiles** remained present; isolated settings migration checked legacy stable profiles remained unchanged.
- [Mac Apple Silicon and Intel native swap test](https://github.com/MasynNay/anything-plays/actions/runs/42936779875) — passed. Mounted signed DMGs read-only; a **different** app copy received the universal2 upstream architecture slice. Ad-hoc re-signing, genuine Python 3.13 dynamic loading of that copied extension and the actual frozen desktop startup passed on both.
- Linux original official wheel SHA-256: `5bb966b610e161a8f6d908b4c62ef3a1f3e922bc7bed73bd70a3e15dc780b90e`.
- Windows original official wheel SHA-256: `f495b0eb7a5c54c59da58e964bc7f68073c3f43cf307729fd48309104a04c190`.
- Mac universal2 original official wheel SHA-256: `56441a9bb75c2461750dc0e6e4a46e3833b3cf6339bfbaf16f93ecac037510f3`.

**Important technical limitation:** the released Windows and Linux
pygame native libraries were already **byte-identical** to their
original upstream wheel file members. Copying the same bytes back
into a disposable installation confirms install layout, source identity
and continued installed-app startup; it does *not* demonstrate that a
recompiled, changed native library can be loaded. The Mac test is a
more meaningful transformed-binary swap because original signed/thinned
Mac native files differ from their upstream universal2 wheel slice.
Even this does not prove source-modified pygame extensions can be
compiled and used by all gamepad features.

The workflow records real per-platform installed startup JSON,
a SHA-256 wheel/source receipt and a report marking the original
installation unchanged. It intentionally does not set any legal
compliance or final-release acceptance flag true.

## Subsequent source-modified Linux extension test passed

The [source-modified pygame-ce build/RC1 runtime check](https://github.com/MasynNay/anything-plays/actions/runs/42949949019)
compiled a genuinely changed C-native extension, invoked its new method
from the copied frozen RC1 app and passed desktop startup on Linux. This
surpasses the previous byte-identical wheel swap but does not complete
other three OSes or LGPL license requirements. [Complete report](V3_1_LGPL_ACTUAL_MODIFIED_PYGAME_LINUX_SOURCE_QA.md).

## Remaining mandatory independent evidence

1. **Compile a deliberately altered pygame-ce extension from pinned original LGPL 2.1 source** and demonstrate that its changed behavior is observable through the actual frozen app after swapping, not just that byte-identical published wheel bytes are accepted.
2. Repeat with other covered pygame extensions and SDL/third-party LGPL shared libraries that require user modification and replacement, taking native dependencies and interface compatibility into account.
3. Produce the exact corresponding source tree, compile scripts, patches, transitive library sources and notice inventory for each production binary, plus a working end-user replacement/relinking tutorial.
4. Review GNU [LGPL 2.1 Section 6](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html) independently for the chosen distribution method; satisfy other emulator GPL, MPL, and custom license terms.
5. Finish physical controllers, cameras, representative game saves/audio, longer sessions, and **new correctly versioned stable 3.1.0 installers** on all four platforms.

Until these are genuinely verified, do not mark final source, relinking,
hardware or stable 3.1.0 release gates as approved. The [existing public
3.1 RC1](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc1)
and [stable 3.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0)
releases are unaffected.
