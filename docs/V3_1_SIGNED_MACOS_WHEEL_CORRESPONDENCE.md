# Anything Plays 3.1 RC1 — macOS native wheel provenance

**Verified November 10, 2026. Technical evidence, not a licensing or final stable-release approval.**

Original source-built RC1 DMGs were mounted read-only on actual Apple Silicon and Intel macOS Actions runners. The audit checked all native pygame/SDL candidate file SHA-256 hashes against frozen installer receipts before comparing their compiled `__TEXT,__text` machine-code sections with published, checksum-pinned Python wheel files.

| Original signed RC1 installer | Native files | Exact pygame-ce wheel executable text sections | Exact OpenCV wheel executable text sections | Unmatched |
| --- | ---: | ---: | ---: | ---: |
| macOS Apple Silicon | 121 | 120 | 1 | **0** |
| macOS Intel | 120 | 120 | 0 | **0** |
| **Total** | **241** | **240** | **1** | **0** |

**Evidence:** [Signed original Mac installer comparison](https://github.com/MasynNay/anything-plays/actions/runs/42925583942) passed both runner architectures, and [independent OpenCV SDL wheel comparison](https://github.com/MasynNay/anything-plays/actions/runs/42926295393) passed, with corresponding original JSON artifacts retained 90 days.

The signed Mac SDL/pygame sections map to:

- **pygame-ce 2.5.8 macOS universal2:** `pygame_ce-2.5.8-cp313-cp313-macosx_10_13_universal2.whl` (SHA-256 `56441a9bb75c2461750dc0e6e4a46e3833b3cf6339bfbaf16f93ecac037510f3`), matches 120 original installed native files on Apple Silicon and 120 on Intel.
- **OpenCV Python Headless 4.14.0.94 Apple Silicon:** `opencv_python_headless-4.14.0.94-cp37-abi3-macosx_13_0_arm64.whl` (PyPI SHA-256 `bc7db37dc234f7bb3190a158fd9dd750357246fc7d8adb23698843ef721a993b`), matches the one extra `Contents/Frameworks/cv2/__dot__dylibs/libSDL2-2.0.0.dylib` signed ARM binary's `__text` section.
- Original ARM RC1 DMG SHA-256 `f272c79c31761607221a0a0e9b03756ecc0c6ae998be05d416bf3f5ebd50ce9b`. Original Intel DMG SHA-256 `5a3522259955efa9082c47b7c528b3f94575ea3d830e15d206b38876125343fc`.
- Upstream wheel sources: [pygame-ce 2.5.8](https://github.com/pygame-community/pygame-ce/releases/tag/2.5.8) and [OpenCV Python Headless 4.14.0.94](https://pypi.org/project/opencv-python-headless/4.14.0.94/). Frozen runtime package pins are in `requirements-build.txt`.

**Exactly what matched:** the `__TEXT,__text` executable section length and SHA-256, after selecting the wheel architecture slice. This is stronger than the previous 0/121 and 0/120 *full installed-file* SHA matches, because PyInstaller and macOS signing can legitimately change overall Mach-O bytes. It is **not** a proof that the installed and upstream whole files match, nor proof that the published binary's complete source, compiler flags or linked LGPL libraries are reproducible.

## Follow-on genuine Mac library replacement test

[Original signed Mac RC1 extension replacement study](https://github.com/MasynNay/anything-plays/actions/runs/42936779875) PASSED both Apple Silicon and Intel: a disposable copy was swapped with the verified original upstream `pygame.base` extension, re-signed, loaded by CPython 3.13, and launched to a real Tk GUI event loop. The readonly original installer remains unchanged.

This is **stronger than comparing file hashes alone**, but still does not prove user-modified compiled pygame library replacement or overall LGPL Section 6 compliance. [Full procedure and limitations](V3_1_LGPL_UPSTREAM_EXTENSION_REPLACEMENT_QA.md).

## Remaining stable 3.1.0 release tasks

1. Establish compiled SDL 2.32.8/2.32.10, SDL_image, SDL_mixer and SDL_ttf source build lineage, source patches, relevant transitive library source and license notices. Pinned tagged SDL source candidates alone do not certify a particular binary.
2. Verify pygame-ce LGPL-2.1-or-later and other applicable LGPL dependencies can be replaced or relinked by end users on all four production installers. Ad-hoc Mac signing and embedded library paths need an actually tested, documented process.
3. Inspect OpenCV's original wheel `LICENSE-3RD-PARTY.txt` (including its stated FFmpeg LGPL terms) and confirm complete installed transitive licensing and source access.
4. Finish actual physical controller, real camera, game save/audio, longer-session and correctly versioned stable 3.1.0 installer acceptance.

Audit source: `tools/inspect_v31_macos_text_provenance.py` and `tools/inspect_v31_opencv_wheel_origin.py`. Negative tests: `tests/test_v31_macos_text_provenance.py` and `tests/test_v31_opencv_wheel_origin.py`.

**No 3.1.0 stable readiness gate was approved by this investigation.** Public 3.1 RC1 and public stable 3.0/2.0 packages are unchanged.
