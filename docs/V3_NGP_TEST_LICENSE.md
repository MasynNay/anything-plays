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

## Genuine original monochrome-only native acceptance (no external game fixture)

The four runner jobs for `system=ngp` in
`.github/workflows/v30-ngp.yml` must no longer use the **color-header**
alignment cartridge above for a monochrome acceptance claim. Instead, they
run the *fully original source-generated* **0x00 monochrome cartridge**
from `tools/build_v30_ngp_mono_native_av.py`, using
`tools/probe_v30_ngp_mono_native_av.py` and each platform's genuine
NeoPop Libretro binary.

Its source is in this repository and produces a 64 KiB authentic
monochrome header, a K1GE changing grayscale display, and actual PSG tone
using B8=55 sound enable and B9=AA Z80 stopped. Real native
`CoreSession` video/audio/input callbacks must all pass; an additional
workflow step checks the actual source-built mode, distinct nonblank
frames, nonzero PCM samples, manual A and camera B input callback counts,
and exact JSON SHA-256. Source-generated ROM bytes are temporary **CI
only**, not saved in Git, in an installer, or in a public test artifact.

The four `system=ngpc` runners still use the independent pinned original
MIT StarGunner **color** `.ngc` demo with full upstream blob, byte length,
and original header checks. The old color-header `.ngp` calibration file
remains in the research registry solely for transparency and is never
accepted as real mono evidence.

**Scope:** This is authentic native *homebrew core compatibility testing*,
not proof of retail-game compatibility, end-user physical speakers,
camera-zone behavior under actual hardware, cartridge flash save or
long-run installed app operation. The exact in-process GPL/noncommercial
combined-software licensing and 3.0 public distribution flags remain
unapproved. Do not close either on a green native test alone.

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
