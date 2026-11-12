# Anything Plays 3.1.0 — Actual clean final macOS pygame source modification

**Result: PASS on genuine new full final 3.1.0 Apple Silicon and Intel Mac DMGs** in [two native GitHub Actions jobs, 43149191077](https://github.com/MasynNay/anything-plays/actions/runs/43149191077).

Both runners independently verified original complete 18-console/11-core installer QA from [43140637755](https://github.com/MasynNay/anything-plays/actions/runs/43140637755) at exact source `104b96621ec4cb8dc39fde8c3fe96fc854c406ed` and checked per-architecture signed native hashes from the [corrected original inventory run 43147036559](https://github.com/MasynNay/anything-plays/actions/runs/43147036559).

On **each native Mac architecture**, the workflow:

1. Cloned authentic pygame-ce 2.5.8 upstream at exact commit `c8200a9eaa530f884a0a4c3384cefc48006e58be` and verified its LGPL source notice.
2. Applied a controlled original C `src_c/base.c` change to add a distinct, observable `pygame.base._ap31_relink_probe()` method.
3. Built and checked original SDL2 `2.32.10` source development headers; compiled a real distinct CPython 3.13 Mac native `base.cpython-313-darwin.so` with Meson, Ninja and the appropriate CPU's compiler.
4. Downloaded and independently authenticated the original immutable full Mac 3.1.0 DMG and original upstream SHA-256-pinned universal pygame wheel.
5. Mounted the original DMG read-only, verified the original signed app, checked the original pygame native code section against the correct slice of the official upstream wheel, and modified **only an external disposable copy**.
6. Relinked the source-built replacement to the bundled SDL2 library, ad-hoc signed both replacement and copied app, loaded the replacement in a real CPython process and executed its genuinely modified C method.
7. Launched the actual **copied, signed final 3.1.0 frozen Tk desktop** and verified its 18-console initialization and successful event loop with an isolated profile. The original DMG remained unchanged.

Both native Mac jobs completed successfully. Artifacts retain the source patch, compiler/changed-native receipts, original source identity and changed method/frozen GUI evidence.

**Limits:** This is one LGPL-covered pygame extension on two original source-built final DMGs, **not** verification that every pygame/other native dependency has corresponding source and a complete legally sufficient user replacement/relinking path. No real physical gamepad, camera, ROM, audio or endurance testing was performed. Other native source/notice/transitive obligations and independent release authorization remain OPEN. No public installer bytes, other releases or source/rights approval flags changed.
