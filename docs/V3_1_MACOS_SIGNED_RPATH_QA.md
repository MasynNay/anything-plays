# Anything Plays 3.1 — Signed Mac SDL2 direct runpath investigation

**Status:** original installer engineering QA only. Not an all-dependencies
dyld load-chain proof, an LGPL determination, or stable 3.1 acceptance.

## Why this exists

The [original signed native dependency inventory](V3_1_MACOS_NATIVE_DEPENDENCY_GAPS.md)
identified one ambiguous dependency name on Apple Silicon:
`@rpath/libSDL2-2.0.0.dylib`.
The installed app has two distinct SDL2 runtime versions:
OpenCV's 2.32.8 and pygame CE's 2.32.10. Earlier tests successfully
loaded both SDL2 libraries directly and exercised virtual joystick
buttons; they **did not** determine the actual image chosen for each
indirect `@rpath` dependency.

## New original-binary investigation

[Signed Mac runpath workflow](../.github/workflows/v31-macos-signed-rpath-review.yml)
mounts the genuine Apple Silicon and Intel original RC1 DMGs read only,
validates the existing signed app, and checks the exact head commits
of the original 18-console QA and signed native dependency audit.

For every previously audited native image with a dependency whose name
is exactly `@rpath/libSDL2-2.0.0.dylib`, the new Python
tool authenticates the on-disk file SHA-256 against the original receipt,
calls `otool -l` to inspect that image's `LC_RPATH` load commands,
and expands only **that image's direct** `@loader_path` or
`@executable_path` runpaths. Any resulting bundled
SDL2 file is compared by actual SHA-256 against the two approved-for-
*inspection* binaries.

The machine-readable report identifies missing, indirect/unexpanded,
external, nonmatching and exact-hash-matching **candidate paths**.
It explicitly records `full_dyld_loader_chain_resolved: false` and
`live_loaded_sdl_image_proven: false`. This matters because the
loading process can inherit runpaths from its loader chain, and a path
candidate match is not proof that dyld actually selected it.

The adversarial tests reject wrong source revisions or platforms,
altered signed binaries, forged library hashes, invalid or incomplete
load commands, duplicate paths, untrusted/escaping symlinks, and any
change to redistribution or relinking approval fields.

## Verified signed installer result (original RC1)

The [two-Mac signed runpath test](https://github.com/MasynNay/anything-plays/actions/runs/42959425185)
passed on Apple Silicon and Intel, after adjusting strict native-file
validation to accept only signed-hash-matched in-app relative symlinks.

| Observed original signed RC1 entries | Apple Silicon | Intel Mac |
| --- | ---: | ---: |
| SDL2 referencing Mach-O images | 83 | 82 |
| Images with an exact signed pygame SDL2 direct runpath candidate | 79 | 79 |
| SDL2 provider/alias images with no direct LC_RPATH | 4 | 3 |
| Other SDL2 consumers without a direct signed-hash match | **0** | **0** |

The entries without direct runpaths are the installed SDL2 dylibs or
aliases themselves, and are **not additional application consumers**.
All 79 original consumer images on each architecture have an
authenticated local direct runpath candidate to the pygame SDL2 binary.
The report now distinguishes those groups explicitly and CI requires
the exact original counts. These are *candidate paths*, not proof of
the image selected by a complete live dyld loader chain. The other
OpenCV SDL2 runtime version still exists on Apple Silicon and can
be loaded independently, as demonstrated in prior testing. No
copyright, LGPL, physical hardware, or stable installer gates change.

## Verified underlying inputs

- [Full source-pinned RC1 QA, all four OSes](https://github.com/MasynNay/anything-plays/actions/runs/42905694504)
- [Original signed Apple Silicon and Intel native linkage evidence](https://github.com/MasynNay/anything-plays/actions/runs/42906227613)
- [Earlier native dependency gap inventory](https://github.com/MasynNay/anything-plays/actions/runs/42957981160)

The workflow creates 30-day technical artifacts only; it never
changes the original installer, signs an app, publishes a release or
changes user preferences.

## Remaining requirements

This investigation is intended to make the next runtime loader test
targeted and reproducible. Complete linker-chain and live image
verification, transitive source and notice review, physical
controller/camera/gameplay acceptance, and properly versioned final
stable installers remain separate work. All six
[stable-release gates](../config/v3.1-release-readiness.json) remain
**false** until independently accepted. Public 3.1 RC1 and stable 3.0
are unchanged.
