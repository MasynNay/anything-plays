# Anything Plays 3.1 RC1 — Real compiled modified pygame C source on Macs

**Apple Silicon: PASS. Intel Mac: PASS. Both real signed RC1 native source replacement and frozen desktop tests complete.**
Evidence: [Mac source-build and frozen desktop test workflow](https://github.com/MasynNay/anything-plays/actions/runs/42951159759).

## Verified source and native build

The workflow takes original **pygame-ce 2.5.8** at the exact pinned
commit `c8200a9eaa530f884a0a4c3384cefc48006e58be` and applies the same
source patch already proven on Linux: an observable native method
`pygame.base._ap31_relink_probe()` in `src_c/base.c`.

Importantly, the Mac test separately builds the **exact original SDL2
2.32.10 release** from upstream Git commit
`5d249570393f7a37e037abf22cd6012a4cc56a71` to match the
actual SDL version bundled inside the signed RC1 Mac installers.
Using Homebrew's newer SDL2 2.32.74 headers instead caused an appropriate
"Dynamic linking causes SDL downgrade" runtime error; this is not bypassed.
Meson/Ninja builds the modified pygame extension using the original
matching SDL 2.32.10 C headers and library.

## Actual signed native replacement and application behavior

The exact four-OS full RC1 QA installer, native integrity receipt and
official 2.5.8 pygame universal2 wheel SHA are verified. The original
signed RC1 DMG is mounted **read-only**, and the source-built, genuinely
modified `pygame.base` extension replaces the native in a **separate
disposable app copy only**. The freshly compiled native machine-code
section differs from the original signed native file and official wheel.

The replacement's SDL load command is adjusted to point to the already
packaged SDL2 native library **inside the app copy**, rather than
depending on Homebrew. The copied extension and app receive fresh ad-hoc
signatures, both validated by `codesign`. External CPython 3.13 imports
the modified extension from the **copied app**, invokes its new C
method, and verifies the expected value:

```
anything-plays-3.1-ce-2.5.8-compiled-modified-native
```

The copy's actual frozen desktop `--ap-v30-ui-smoke` starts the
18-console GUI and runs Tk's event loop. Legacy 3.0 settings-migration
fixtures run in a disposable home, not the real user's profile.

| Actual native source change test | Apple Silicon | Intel Mac |
| --- | --- | --- |
| Exact source of pygame-ce 2.5.8 + SDL2 2.32.10 pinned | PASS | PASS |
| C extension compiled from changed source | PASS | PASS |
| Original signed DMG untouched; disposable copy changed | PASS | PASS |
| Native linked to in-app SDL2, re-signed, loaded | PASS | PASS |
| New C method invoked from copied binary | PASS | PASS |
| Real frozen 18-console Tk desktop boot | PASS | PASS |
| LGPL Section 6 complete/source correspondence approved | **NO** | **NO** |

Source diff and native/runtime receipts are retained as 90-day GitHub
Actions artifacts for review.

## Outstanding limitations

This demonstrates an observable source-modified Python C extension can
be rebuilt and loaded, but the independent CPython call is separate from
the frozen GUI's Tk startup test. It is not an end-to-end modified
gamepad or physical controller test. It does not establish every
LGPL-covered pygame and SDL component can be relinked, complete
corresponding source/flags and transitive notices, Gatekeeper-supported
user installation procedures, or legal LGPL 2.1 Section 6 satisfaction.

Windows source-modified compilation has since passed [separate Windows QA](https://github.com/MasynNay/anything-plays/actions/runs/42953456034); real hardware acceptance, complete
source/relinking materials and correctly identified final 3.1.0 builds
also remain open. **All six stable acceptance gates remain false.**

Scripts: `tools/build_v31_modified_pygame_probe.py`,
`tools/verify_v31_modified_pygame_macos.py`,
`tests/test_v31_modified_pygame_macos.py`, and
`.github/workflows/v31-macos-modified-pygame-from-source.yml`.
