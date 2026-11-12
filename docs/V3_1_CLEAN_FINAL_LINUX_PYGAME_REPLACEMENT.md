# Anything Plays 3.1.0 — Actual clean-final Linux pygame source modification

**Result: TECHNICAL PASS for one real LGPL-covered pygame CE native extension in the final Linux 3.1.0 application. This is not full third-party redistribution approval.**

The [native Actions run 43148388829](https://github.com/MasynNay/anything-plays/actions/runs/43148388829) succeeded on the exact original clean-source Linux DEB produced in [13/13 original native final QA run 43140637755](https://github.com/MasynNay/anything-plays/actions/runs/43140637755), application source revision `104b96621ec4cb8dc39fde8c3fe96fc854c406ed`.

The independent native Ubuntu test:

1. Checked exact GitHub source revision, full 18-console / 11-core 3.1.0 installer SHA256 and original package receipt.
2. Checked an **official SHA-pinned** pygame-ce 2.5.8 CPython 3.13 wheel against the existing frozen `pygame.base` extension.
3. Cloned genuine pygame-ce 2.5.8 source at exact upstream commit `c8200a9eaa530f884a0a4c3384cefc48006e58be` and verified its original LGPL notice before applying a controlled C source modification.
4. Compiled a genuinely different `base.cpython-313-x86_64-linux-gnu.so` on the native runner using Meson and Ninja, inserted it into **only an independent disposable copy** of the original installed full application and verified the original installer and extracted source app remained unchanged.
5. Loaded that copied modified native library in a real CPython 3.13 process and executed the newly added `pygame.base._ap31_relink_probe()` C method with its expected distinct return value.
6. Launched the **actual frozen 3.1.0 Tk desktop binary** from the changed-source copied app in an isolated virtual display and verified the mainloop and 18-console initialization.

The exact workflow retains native source patch, source modification receipt, compilation evidence, copied-app native execution result and installed frozen GUI smoke evidence. All on-run public release, real hardware, legal/source/relink flags remain **false**.

This supersedes the **Linux RC1-only** native pygame replacement demonstration for purposes of testing **this one exact clean final 3.1 Linux** extension. It does not prove a recipient can rebuild/replace every LGPL-covered pygame or SDL-related dependency in all four final frozen installers. The four-platform original-source/native-relinking review and recipient-accessible source/notice/replacement instructions remain open. Nor does this simulate a real USB/Bluetooth controller, physical webcam, game ROM, save or sustained gameplay.

**Do not set** `pygame_sdl_redistribution_review`, `corresponding_source_material`, `real_controller_hardware_acceptance` or `public_release_approved` to true based solely on this successful test.
