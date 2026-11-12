# Anything Plays 3.1.0 — Exact final Windows source-modified pygame CE test

**Result: PASS**, genuine native Windows x64 / CPython 3.13, [GitHub Actions 43149732092](https://github.com/MasynNay/anything-plays/actions/runs/43149732092), source-built 18-console/11-core final installer `AnythingPlaysSetup-3.1.0.exe` from original four-platform QA run [43140637755](https://github.com/MasynNay/anything-plays/actions/runs/43140637755), application source `104b96621ec4cb8dc39fde8c3fe96fc854c406ed`.

This was an authentic **final 3.1.0** test, not the older RC1:

1. Verified the immutable original final Windows installer source revision, SHA256, eleven native core families and eighteen console profiles. Checked the exact original Windows native pygame extension against the official upstream pygame-ce 2.5.8 wheel and independent [native inventory SHA report](https://github.com/MasynNay/anything-plays/actions/runs/43147036559).
2. Cloned exact tagged original LGPL pygame-ce at source commit `c8200a9eaa530f884a0a4c3384cefc48006e58be` and modified original `src_c/base.c` with an observable new `pygame.base._ap31_relink_probe()` function.
3. Downloaded SHA-verified original SDL2 2.32.10 MSVC development headers/import library, compiled a genuine new Windows x64 `base.cp313-win_amd64.pyd` PE from modified C code using installed MSVC and Python 3.13. The new bytes were independently checked to differ from the original wheel.
4. Extracted the verified original full 3.1.0 Inno Setup installer, copied it to an unrelated disposable application folder, replaced **only the copied app's** pygame C extension and verified the original installer/native bytes remained unchanged.
5. Actually loaded the replaced native with CPython 3.13, invoked the new C method and obtained its exact modified native return value, then launched the genuine copied final 18-console frozen Tk desktop with an isolated user profile. Both changed-code execution and frozen desktop startup passed.
6. Preserved the original source diff, compiled native hashes, original QA identity, changed-code invocation and frozen startup evidence in a private CI artifact.

The legacy RC1 settings migration fixture was deliberately **not** reused: it targets older RC1 profile identities and failed against the newer final installation. The original [13/13 clean-source full final QA run](https://github.com/MasynNay/anything-plays/actions/runs/43140637755) separately passed the correct installed final settings-isolation contracts.

**Scope:** one authentic source-modified LGPL pygame native extension, not every pygame CE or transitive native dependency and **not** independent compliance review of license notices, complete corresponding source, user replacement/relinking requirements or recipient instructions. No physical USB/Bluetooth gamepad, live camera, gameplay/audio/save or endurance acceptance. Public release authorization remains blocked pending those independent reviews.
