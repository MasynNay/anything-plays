# Anything Plays 3.1 RC1 — Genuine source-modified pygame CE on Windows

**Verification: PASS, November 10, 2026 (Mountain Time).** This is a technical compile, native replacement, and frozen desktop test. It does **not** certify GNU LGPL Section 6 compliance or approve a stable 3.1.0 release.

[Verified Windows Actions build and test](https://github.com/MasynNay/anything-plays/actions/runs/42953456034)

## What was really tested

The independent Windows x64 GitHub Actions runner built a **new pygame CE 2.5.8 native C extension from deliberately changed source** rather than reusing or renaming the original prebuilt wheel. The workflow:

1. Cloned original pygame CE version **2.5.8** at exact Git commit `c8200a9eaa530f884a0a4c3384cefc48006e58be`, with Git's Windows CRLF conversion disabled, and validated the original LGPL notice's exact content hash.
2. Applied the same controlled `src_c/base.c` change previously tested on Linux and both Macs. Its canonical UTF-8 / LF SHA-256 is `89b4e97a1fe664a95d5e8c7ec8d7e2836747e19debdace6e87e463f3a3c8b050`. It adds an observable native function `pygame.base._ap31_relink_probe()`.
3. Downloaded the original official **SDL2 2.32.10 Visual C** development ZIP, validating its pinned upstream SHA-1 `27f5179346a0b0db80c4dd1769c7c9d62b9a91f3`. This is the header/import-library SDK corresponding to the SDL2 version in the real RC1 runtime.
4. Used Visual Studio 2026's actual x64 **MSVC C compiler** and CPython **3.13** headers to compile the changed `base.c` into a genuine x64 PE Python extension (`base.cp313-win_amd64.pyd`). Its produced SHA-256 is `65f522cc363ecc7d8bdb5d7d85e2eb597c7e0547eb28c867ffc2169b0e92089e`.
5. Independently checked the immutable original 18-console, 11-core 3.1 RC1 Windows Inno Setup EXE and original SDL/native QA receipts. The exact original published pygame-ce 2.5.8 Windows wheel was also SHA-256 pinned to `f495b0eb7a5c54c59da58e964bc7f68073c3f43cf307729fd48309104a04c190`.
6. Installed that original RC1 into an **ephemeral runner**, then staged a **separate disposable app copy**. Only the copy received the new source-compiled native extension. Its PE header was independently checked for 64-bit AMD64 architecture, and it had different bytes from the upstream/original installed extension.
7. Used a separate actual Windows CPython 3.13 process to load the replacement `pygame.base` extension **from inside that copied RC1 installation**, resolved its shared libraries from the app's packaged directories, invoked the newly added C method, and verified the returned value:

   `anything-plays-3.1-ce-2.5.8-compiled-modified-native`

8. Launched the **copied original frozen Anything Plays desktop executable** with its real Tk event-loop startup diagnostic. The independent validator confirmed 18 console profiles and successful startup. Isolated 3.0 settings migration checks also passed without touching the original user preferences.

| Technical check | Result |
| --- | --- |
| Exact tagged pygame-ce source and LGPL license checked | PASS |
| Same genuinely changed C source as Linux and both Macs | PASS |
| Original SDL2 2.32.10 Windows SDK pinned to upstream checksum | PASS |
| Native Windows x64 PE built from modified C source | PASS |
| Modified native extension differs from unmodified wheel and RC1 | PASS |
| Modified C method executed from the copied RC1 native file | PASS |
| Actual copied 18-profile frozen desktop Tk startup | PASS |
| Original installer and stable user profile untouched | PASS |

The workflow's full modified-source diff, source and native hashes, native invocation, actual frozen GUI diagnostics, and preference acceptance receipts are preserved for **90 days** as Actions artifact `AnythingPlays-3.1-RC1-WINDOWS-GENUINE-SOURCE-MODIFIED-PYGAME-C` (scheduled expiry February 9, 2027).

## Four-platform result

The same **genuinely changed pygame-ce C source** is now proven to compile and load from a disposable original RC1 installation on each supported platform:

- [Linux x64](https://github.com/MasynNay/anything-plays/actions/runs/42949949019): new C-native method executes; original copied frozen 18-profile Tk desktop starts.
- [Mac Apple Silicon and Intel](https://github.com/MasynNay/anything-plays/actions/runs/42951159759): modified C extension links to packaged SDL2 2.32.10, app copy is ad-hoc signed, new C method executes, and both original copied frozen Tk desktop apps start.
- [Windows x64](https://github.com/MasynNay/anything-plays/actions/runs/42953456034): changed-source MSVC x64 PE extension executes in copied RC1; frozen 18-profile Tk desktop starts.

**Limitations:** The new C method is executed by a separate test process loading the actual copied native extension. The frozen GUI's startup smoke does not itself call that new method or exercise a real controller. These results prove only one `pygame.base` replacement mechanism, not that all LGPL-covered pygame and SDL libraries are replaceable, that full corresponding source/build instructions are complete, or that real gamepad, camera, save, audio and long-session performance has been verified.

### Remaining stable 3.1.0 requirements

Finish the dependency-by-dependency LGPL/native source and license notices audit; prepare genuine user rebuild/replacement instructions with matching SDL source, transitive libraries and linking data; verify the required legal distribution obligations; finish physical hardware and gameplay acceptance; and produce correctly versioned stable 3.1.0 installers. **All six stable-release gates remain unapproved.**

Reproduction: `tools/build_v31_modified_pygame_probe.py`, `tools/build_v31_modified_pygame_windows.py`, `tools/verify_v31_modified_pygame_windows.py`, `tools/run_v31_modified_pygame_windows_smoke.py`, `tests/test_v31_modified_pygame_windows.py` and `.github/workflows/v31-windows-modified-pygame-from-source.yml`.

The [public 3.1 RC1](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc1), [stable 3.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0), and 2.0 installers are unchanged.
