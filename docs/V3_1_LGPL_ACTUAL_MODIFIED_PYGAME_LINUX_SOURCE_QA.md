# 3.1 RC1: genuine modified pygame-ce source rebuild on Linux

**Verified November 10, 2026: PASS.** This is a technical test, **not** full LGPL-2.1 Section 6 or stable 3.1.0 approval.

[Successful CI source-build and real frozen desktop test](https://github.com/MasynNay/anything-plays/actions/runs/42949949019)

## Proven with genuine modified C source

The test cloned pygame-ce **2.5.8** at the exact original commit `c8200a9eaa530f884a0a4c3384cefc48006e58be`, validated its original LGPL license SHA-256 (`a190dc9c8043755d90f8b0a75fa66b9e42d4af4c980bf5ddc633f0124db3cee7`) and patched **`src_c/base.c`** to add an entirely new C-native Python method `_ap31_relink_probe()`.

The changed C file SHA-256 was `89b4e97a1fe664a95d5e8c7ec8d7e2836747e19debdace6e87e463f3a3c8b050`. The controlled source patch and a JSON manifest are retained in the 90-day GitHub Actions artifact named `AnythingPlays-3.1-RC1-LINUX-REAL-SOURCE-MODIFIED-PYGAME-RELINK-QA`.

GitHub Actions installed SDL2 development libraries, Meson, Ninja and Cython, and compiled the **changed `pygame.base` C extension** to a CPython 3.13 Linux native `.so` with the original upstream Meson target. It compared the compiled binary to the official, SHA-pinned 2.5.8 Linux wheel: the new binary genuinely **differed**. This is not a repackaged original wheel.

The original frozen Linux 3.1 RC1 Debian installer was authenticated against its original full 18-console source build receipt, extracted and copied to a **disposable installation directory**. Only the copied app received the changed native extension. The original native file and package remained unchanged.

A separate Python 3.13 process then loaded the **replaced native extension from inside that copied RC1 installation** and invoked `pygame.base._ap31_relink_probe()`. It returned the expected value:

```
anything-plays-3.1-ce-2.5.8-compiled-modified-native
```

The **real frozen 18-console, 11-core desktop executable** in the disposable copy subsequently passed its actual Tk event-loop startup smoke test. Isolated 3.0-to-3.1 preferences migration passed without changing original stable user files.

| Verification | Result |
| --- | --- |
| Exact upstream Git commit and original LGPL text | PASS |
| Source changed and patch retained | PASS |
| New CPython 3.13 extension compiled from changed C source | PASS |
| Native bytes differ from original pygame wheel | PASS |
| New C method executed from replaced RC1 native file | PASS |
| Copied real 18-console frozen desktop booted | PASS |
| Stable user preferences and original releases untouched | PASS |

## Mac follow-on completed

[Apple Silicon and Intel Mac source-modified native extension and frozen GUI QA](https://github.com/MasynNay/anything-plays/actions/runs/42951159759)
**PASSED** as a separate two-runner proof of the same C source change,
with SDL2 2.32.10 built from pinned original source, an isolated
signed app copy, native method invocation and real Tk boot on both.
See [Mac report](V3_1_LGPL_SOURCE_MODIFIED_MACOS_QA.md).

## Limits

The special C method was executed by a separate Python process loading the native extension **from the copied app**. The frozen GUI smoke itself does not call the method or exercise a physical controller. The compiled extension used system SDL development headers; this does not establish full upstream wheel build reproducibility, replacement of every LGPL-covered native component, complete corresponding source, or legal LGPL compliance.

The remaining requirements are genuine source-modified native replacement on **Windows, Intel Mac and Apple Silicon**, comprehensive linked SDL/transitive dependency source and notices, tested end-user source build/replacement instructions, real controller/camera/game-save/audio endurance tests, and correctly versioned 3.1.0 production installers.

**Final stable gates stay false.** Original [3.1 RC1](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc1) and [3.0 stable](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0) are unchanged.

Reproducibility: `tools/build_v31_modified_pygame_probe.py`, `tools/verify_v31_modified_pygame_linux.py`, `tests/test_v31_modified_pygame_relink.py`, `.github/workflows/v31-linux-modified-pygame-from-source.yml`.
