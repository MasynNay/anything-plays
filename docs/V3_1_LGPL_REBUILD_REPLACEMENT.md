# Anything Plays 3.1.0 — Rebuild and replace covered native libraries

**Recipient source and replacement instructions for the exact 3.1.0 clean-source installer candidate.** These instructions are for users who want to modify pygame-ce or other compatible native shared libraries. They do not claim that every possible replacement has been tested or guarantee general hardware compatibility.

## Sources and copyright notices

- Application source, packaging configuration, `requirements-build.txt`, packaging helpers, and executable entry points: [exact original 3.1.0 application revision `104b96621ec4cb8dc39fde8c3fe96fc854c406ed`](https://github.com/MasynNay/anything-plays/tree/104b96621ec4cb8dc39fde8c3fe96fc854c406ed) (MIT for original application code).
- The `AnythingPlays-3.1.0-PYGAME-SDL-MPG123-ORIGINAL-SOURCE.zip` companion (once publicly attached to the stable release) contains pinned original pygame-ce 2.5.8, SDL2 2.32.8/2.32.10, SDL2_image 2.8.12, SDL2_mixer 2.8.2, SDL2_ttf 2.24.0, mpg123 1.33.7 source archives, licensing texts, source fingerprints and SHA-256 manifests. The original pygame-ce source commit is `c8200a9eaa530f884a0a4c3384cefc48006e58be`.
- Original libretro emulator-source archives and their individual licenses remain at [3.0 source companion](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources). OpenCV 4.14.0.94 and the Windows source build patch are referenced in [the 3.1 OpenCV source instructions](V3_1_CLEAN_OPENCV_SOURCE_REPRODUCTION.md).
- Full [pygame-ce LGPL 2.1 text](../licenses/Pygame-CE-LGPL-2.1.txt), [original mpg123 LGPL 2.1 text](../licenses/mpg123-LGPL-2.1-ORIGINAL.txt) and individual upstream SDL source archive LICENSE files are available with the source. Other proprietary/unrelated components do not become MIT licensed by being packaged beside the app.

The applicable LGPL terms permit modification of the licensed libraries and reverse engineering needed to debug those modifications. The MIT grant for original Anything Plays source also permits alteration. Complete installation contents are **not** offered for unrestricted commercial redistribution because some libretro cores, including Snes9x, have separate noncommercial restrictions.

## Confirm the exact binary before doing any replacement

Download the correct 3.1.0 installer and the release's `SHA256SUMS.txt` from the **same** release page. Check its SHA-256 before installing or copying it. Do not combine a 3.1 RC1/RC2 DLL, extension, controller wheel, or old stock-OpenCV draft with the final 3.1.0 installers.

All four original installers were built from the exact same application source [43140637755](https://github.com/MasynNay/anything-plays/actions/runs/43140637755). The [native library and notice hash audit](https://github.com/MasynNay/anything-plays/actions/runs/43147036559) includes the original `pygame.base` filename, location, SHA256 and compiled native platform architecture. Perform any replacement **only on a local copy**, keep the original installer, and preserve all copyright notices.

## Linux x64 (Ubuntu/Debian)

1. To inspect without installing, extract the original `anything-plays-31_3.1.0_amd64.deb` with `dpkg-deb -x anything-plays-31_3.1.0_amd64.deb ./unpacked`. The frozen app is below `./unpacked/opt/anything-plays-31`. An installed copy is normally at `/opt/anything-plays-31`.
2. Copy that entire app directory to a user-writable separate folder. Preserve its `_internal`, `cores`, `licenses`, and versioned config behavior. Do not overwrite a system-owned original without making a restorable backup.
3. Extract the pygame-ce 2.5.8 tagged original source from the source companion. Install compatible build tools (native gcc, CPython 3.13 headers, Meson/Ninja/Cython and SDL2 development headers). The exact independently exercised workflow [`v31-final-linux-modified-pygame-source-qa.yml`](../.github/workflows/v31-final-linux-modified-pygame-source-qa.yml) shows how to compile an intentionally changed `src_c/base.c` with Meson and Ninja.
4. Replace only `_internal/pygame/base.cpython-313-x86_64-linux-gnu.so` in the copy with your compiled ABI-compatible native extension. Do not alter the original installed app. Confirm the changed method/import and copied frozen GUI startup using the methods and checks in the workflow.
5. Bundled SDL2 and other shared libraries occupy `_internal/pygame_ce.libs/`, including `libmpg123-*.so.0.49.4`. Their hashed filenames, ELF SONAMEs, dependency lookup paths and symbol ABI must remain compatible if replacing them. A fresh `mpg123` build is **not** proven compatible by the tested single pygame.base swap. Compile and validate it independently before attempting a substitution.

## Windows x64

1. Install the original `AnythingPlaysSetup-3.1.0.exe` normally, or use the repository's `tools.assemble_v31_full_windows.unpack` helper on a disposable directory.
2. Copy the **whole** extracted app, including its `_internal`, `cores`, and license files, to a separate directory. The pygame extension is `_internal/pygame/base.cp313-win_amd64.pyd`; SDL support DLLs are inside the frozen package.
3. The [actual final Windows source-modification workflow](../.github/workflows/v31-final-windows-modified-pygame-source-qa.yml) builds a deliberately changed version of the original pygame-ce `src_c/base.c` using native x64 MSVC, CPython 3.13 development files and the original SHA-pinned SDL2 2.32.10 VC SDK. Its [verification helper](../tools/verify_v31_final_windows_modified_pygame.py) validates original wheel/native checksums and safely substitutes the newly compiled x64 PE binary in the **copied** app.
4. Run the copied desktop, then use native dependency checks to diagnose a missing or incompatible SDL DLL. Replacing a `.pyd` or `.dll` with the wrong architecture, import library, SONAME or symbol ABI can prevent startup; retain the original copy for rollback.

## macOS Apple Silicon and Intel

1. Mount the corresponding original `AnythingPlays-3.1.0-macos-arm64.dmg` or `AnythingPlays-3.1.0-macos-x64.dmg` read-only; copy `AnythingPlays31.app` to a separate writable directory.
2. The frozen `pygame.base` extension is `AnythingPlays31.app/Contents/Frameworks/pygame/base.cpython-313-darwin.so`. The SDL2 and audio native libraries reside beneath `Contents/Frameworks/pygame/__dot__dylibs/`, including `libmpg123.0.dylib` where present.
3. Use the [exact final dual-Mac source-modification workflow](../.github/workflows/v31-final-macos-modified-pygame-source-qa.yml) as the tested compilation and relocation recipe. It compiles a changed C extension from pinned original pygame-ce source against pinned SDL2 2.32.10, uses `install_name_tool` to restore a relative SDL2 loader path, validates `otool -L`, and ad-hoc re-signs the **copied** modified app.
4. After replacing a dynamic library or extension, macOS's original signature will no longer match. Follow the tested workflow to re-sign the changed extension and copied app (`codesign --force --sign -`), then verify with `codesign --verify --verbose=2`. Apple notarization is not claimed and macOS Gatekeeper settings may affect launch.
5. Use a native build matching the machine architecture, correct Mach-O install names and library dependencies. The actual tests modified one pygame C extension; arbitrary SDL2 or mpg123 replacements have not been certified.

## Compatibility and support

An interface-compatible independently compiled `pygame.base` replacement was actually imported, its changed C method invoked, and a copied frozen 18-console Tk desktop started in [Linux](https://github.com/MasynNay/anything-plays/actions/runs/43148388829), [Windows](https://github.com/MasynNay/anything-plays/actions/runs/43149732092), [Apple Silicon and Intel macOS](https://github.com/MasynNay/anything-plays/actions/runs/43149191077). These are actual modified-code technical checks, not merely swapping back an identical upstream wheel.

The source materials provide the project's own Python/build scripts and LGPL upstream source candidates for further experiments. They do not guarantee reproducible identical compiler outputs, hardware controller compatibility, working substitutions for every LGPL/transitive native library, or independent legal certification. If a changed copy fails, restore the original app and open a [GitHub issue](https://github.com/MasynNay/anything-plays/issues) with its source revision, architecture and complete loader error. Distribution of modified LGPL library versions must preserve the relevant license notices and source responsibilities.
