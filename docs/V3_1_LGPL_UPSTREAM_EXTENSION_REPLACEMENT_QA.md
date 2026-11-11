# Anything Plays 3.1 RC1 — Actual upstream pygame extension replacement test

**Verified November 10, 2026. This tests one narrow modification/replacement mechanism; it is NOT a full LGPL-2.1 compliance determination or stable 3.1.0 acceptance.**

## Real Mac tests: both passed

[GitHub Actions run 42936779875](https://github.com/MasynNay/anything-plays/actions/runs/42936779875) completed successfully on original
macOS Apple Silicon and Intel RC1 builds. Each job independently:

1. Required the immutable successful [full 18-profile RC1 build](https://github.com/MasynNay/anything-plays/actions/runs/42905694504) and verified the original signed app and frozen native SHA receipts.
2. Mounted the authentic published RC1 DMG **read-only**.
3. Downloaded the original published pygame-ce 2.5.8 `cp313` macOS universal2 wheel and checked SHA-256 **`56441a9bb75c2461750dc0e6e4a46e3833b3cf6339bfbaf16f93ecac037510f3`**.
4. Selected the correct wheel's `pygame/base.cpython-313-darwin.so` executable slice for that architecture. Verified its compiled `__TEXT,__text` SHA-256 exactly matches the installed signed pygame extension.
5. Created a **separate disposable copy** of `AnythingPlays31RC.app`, swapped only the copied `Contents/Frameworks/pygame/base.cpython-313-darwin.so` with the upstream wheel's genuine architecture slice, and proved the original signed file was unchanged.
6. Ad-hoc signed the replacement binary and the **disposable copied app**. Verified both signatures with `codesign --verify`.
7. Loaded the replacement native file with **the actual CPython 3.13 dynamic loader** using `ctypes.CDLL`.
8. Launched the copied frozen desktop program with `--ap-v30-ui-smoke` under an isolated temporary HOME and confirmed the Tk startup and event-loop checks completed **exit 0** on both Macs.
9. Verified the copied app retained the **18-profile, 11-core RC1 identity** with the existing `tools.verify_v31_installed_ui_smoke` independent QA verifier.

| Target | SHA-verified upstream pygame extension installed in copied app | Re-sign verification | Actual library dynamic load | Frozen Tk GUI startup | Original untouched |
| --- | --- | --- | --- | --- | --- |
| Apple Silicon | PASS | PASS | PASS | PASS | PASS |
| Intel | PASS | PASS | PASS | PASS | PASS |

Each job retained a `STAGED_PYGAME_EXTENSION_SWAP.json`, a real
`SWAPPED_FROZEN_GUI_SMOKE.json`, and
`ACTUAL_COPIED_APP_STARTUP.json` in its 90-day Actions artifact.
The manifest explicitly leaves legal approval, actual modified-from-source
compilation, complete corresponding source, and final stable release **false**.

## What this does and does not prove

**Proven:** a **genuine upstream, binary-compatible** pygame-ce 2.5.8
native extension can replace the signed frozen `pygame.base` file **inside
a copied app**, that copy can be re-signed with an ad-hoc signature, the
replacement shared extension can be dynamically loaded by CPython, and
the full copied app can start its Tk event loop.

**Not proven:** that a user can **compile a newly modified pygame-ce
extension**, substitute it and use all pygame/SDL features (including a
physical gamepad); that every LGPL-covered pygame native module and other
dependencies can be replaced; that complete matching source, compile
flags, library replacement guides, third-party notices, and possible
object/relinking materials have been provided; or that Apple Gatekeeper
and macOS installation policy allow end-user changes without additional
steps. The existing GUI smoke does not automatically activate gamepad
scanning, so successful boot is **not** a physical-controller test.

The legal question must be addressed independently using the exact
LGPL-2.1 text: [GNU LGPL 2.1 Section 6](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html).
In particular, demonstrating that a *single original wheel slice* can be
swapped is not the same as satisfying modified-library replacement and
corresponding-source obligations.

## Reproduce the automated test

The workflow is `.github/workflows/v31-macos-pygame-replacement.yml`,
with the safe staging tool
`tools/probe_v31_macos_lgpl_replacement.py` and adversarial
unit checks `tests/test_v31_macos_lgpl_replacement.py`.

The test deliberately refuses input hashes that do not match official
pygame wheel metadata and original RC1 QA receipts, a copy destination
inside the original mounted app, a tampered native binary, an unknown
OS architecture, or release approval flags that are already set.

The original 3.1 RC1 downloads at
[GitHub Releases](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc1)
and the stable 3.0/2.0 distributions are **not modified**.

## Next concrete tests before stable 3.1.0

- Rebuild an actual deliberately modified pygame-ce extension from the
  exact 2.5.8 original source, preserving its dependency ABI, and verify
  that **a native gamepad test** uses the modified code in each OS package.
- Repeat the user-swappable-library demonstration on the exact original
  Linux and Windows installers, including native dynamic-loading and
  an installed desktop startup test.
- Supply reproducible source/compilation and replacement instructions,
  all required SDL and transitive license notices and source packages,
  and review LGPL Section 6 requirements with distribution counsel.
- Complete real controller/camera/gameplay/audio/save endurance
  testing and four final stable `3.1.0` production installer builds.

**Six stable acceptance gates remain false.**
