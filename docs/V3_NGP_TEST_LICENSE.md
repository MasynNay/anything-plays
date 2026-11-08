# Neo Geo Pocket 3.0 CI-only homebrew test fixtures

The test harness downloads two independent MIT-licensed homebrew examples
**only in temporary CI runners**. Their binaries are not committed to this
repository, packaged into Anything Plays, uploaded as test artifacts, or
downloaded by the application at runtime. The shipped app requires users to
provide their own lawful ROMs.

Both downloads are pinned to an immutable upstream Git commit and verified
against the corresponding Git blob SHA-1, expected size, and actual cartridge
header byte `0x23` **before execution**. File extensions are not evidence of
monochrome vs. color mode; the true monochrome release gate requires 0x00.

## Color-header calibration ROM with a `.ngp` filename (not true monochrome proof)

- **NGPCraft emulator**, original alignment-calibration cartridge v12. **Important:** despite the `.ngp` extension, the pinned Git blob's cartridge header has **byte `0x23 = 0x10` (Color-compatible)**, not `0x00` (monochrome). It is **not** a valid genuine monochrome acceptance fixture.
- Author: **Tixul**. Source repository: https://github.com/Tixul/Ngpcraft_emulator
- Commit: `93b1fd666ff375afcbb48079fbcf61dbb99b86b4`
- File: `hw_calibration/a_align_calib_v12.ngp` (10,630 bytes).
- Blob SHA-1: `8942344acbc23b80fa6f72c10e0fada5b58cdd7a`.
- License: MIT, Copyright (c) 2026 Tixul.

## Color Neo Geo Pocket

- **StarGunner**, original Neo Geo Pocket Color demo, provided as a working
  template rather than a polished retail game.
- Author/license holder: **NGPC Template Contributors**. Source:
  https://github.com/Tixul/Stargunner
- Commit: `de49e240e7b715f1d1f666931b1ad082adff5069`
- File: `Stargunner.ngc` (79,765 bytes).
- Blob SHA-1: `27a06c37743460fcb85832b25b1754103b99e09d`.
- License: MIT, Copyright (c) 2026 NGPC Template Contributors.

## MIT permission and notice

Each project's `LICENSE` grants permission, without charge, to use, copy,
modify, merge, publish, distribute, sublicense and sell copies of the
software, **provided the original copyright and permission notice are
included in all copies or substantial portions**. The projects provide
their binaries under that license; this harness performs transient CI testing
only and does not publish the binary outputs.

Both MIT licenses explicitly provide the software *as is* without warranty,
including implied warranties of merchantability, fitness and
noninfringement. Refer to each exact linked source repository for the complete
copyright and permission text.

## Verification status

The probe uses the real embedded `CoreSession` and strict native video and
nonzero PCM acceptance rules, and runs across Windows x64, Linux x64, Intel
macOS x64 and Apple Silicon macOS. The parent strict acceptance **rejects**
the color-header `.ngp` test fixture for the `ngp` monochrome target even if
its native video/audio/input callbacks succeed. The color StarGunner `.ngc`
fixture declares `0x10` and remains the independently valid NGPC color test. Failure to generate sound in a test demo is
not automatically an emulator bug: it remains a failed *audio evidence gate*
until a suitable reproducible test program establishes real audio. **Do not
weaken this gate or claim physical speaker testing based on CI PCM callbacks.**
