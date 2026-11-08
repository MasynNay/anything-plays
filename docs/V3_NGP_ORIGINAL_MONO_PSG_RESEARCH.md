# Original monochrome Neo Geo Pocket sound: source-built PSG experiment

**Status: experimental, not public 3.0 release approval.**

[The verified 14-cartridge native survey](https://github.com/MasynNay/anything-plays/actions/runs/42448817220) found **0/14** pinned original MIT `.ngp`-named calibration cartridges emitted qualifying native nonzero audio, despite passing source-integrity checks. An independent audit of all 14 original Git blobs also found **all 14 actual header byte `0x23 = 0x10` (color mode)**, so they were never valid original monochrome cartridge fixtures in the first place. This identifies both an unsuitable silent sample set and a **misclassification caused by trusting a file extension**. Neither proves a genuine mono sound defect in NeoPop. That survey was merged through [PR #61](https://github.com/MasynNay/anything-plays/pull/61).

## New original audible-fixture approach

A minimal, auditable, **original** TLCS-900/H executable is produced in `tools/build_v30_ngp_original_mono_psg.py` entirely with Python's standard library. It uses published native instruction encodings and the 64-byte Neo Geo Pocket cartridge header, with system compatibility byte **0x00 (monochrome)** at offset 0x23, entry point 0x200040, a 64 KiB cartridge, and explicit T6W28 tone-register writes. This is a source-built .ngp cartridge, **not a color .ngc ROM renamed to .ngp**.

The four small experiment variants separately test direct tone, stopped Z80 + tone, restarted Z80 + tone, and stopped Z80 + tone + noise. The frequency data is the public T6W28 ~440 Hz divider (218), written via TLCS-900 direct tone register `0x00A1`, and the sound chip activation `0x00B8 = 0x55`, with Z80 stopped by `0x00B9 = 0xAA`. The program clears the watchdog in a tight loop. It does not rely on SNK proprietary cc900/asm900 tools, retail cartridges, BIOS dumps, additional downloaded game content or unrelated third-party assemblies. The standard cartridge identification string follows the documented format; it does **not** represent SNK endorsement or rights to distribute commercial games. This experiment should not be shipped as a game.

Reference hardware facts: [NgpCraft audio memory map and T6W28 format](https://tixul.github.io/NgpCraft_dev_ref/04_Audio/Audio/) and [original open-source TLCS900 instruction assembler](https://github.com/Tixul/NgpCraft_MCP/blob/main/vendor/toolchain/tools/t900as.py).

## Exact NeoPop native sound-control correction (next experiment)

The first four source-built variants all emitted **zero qualifying PCM** in
[real native CI run 42449197364](https://github.com/MasynNay/anything-plays/actions/runs/42449197364).
A new source inspection identified an actual **test cartridge initialization
bug**, independent of whether the emulator is capable of sound.

The [Beetle/Mednafen NeoPop memory write implementation](https://github.com/libretro/beetle-ngp-libretro/blob/master/mednafen/ngp/mem.c)
states the reverse of what the previous experimental comments assumed:

- **B8 = 0x55** enables the PSG; B8 = 0xAA disables the PSG.
- **B9 = 0xAA** stops the Z80; B9 = 0x55 enables the Z80.
- Direct CPU writes to **A0/A1 are accepted only when the Z80 is stopped**, and the sound chip must also be enabled.

The original experimental code set B9=0x55 (Z80 on), or wrote 0xAAAA
(PSG off). Both force the direct PSG path to stay silent. The corrected
research variants use byte stores B9=AA then B8=55, or one little-endian
word B8=0xAA55, with a restart-and-stop control variant. All initial
source-built results from the misconfigured code remain negative historical
evidence, not hardware diagnostics. The corrected real native PCM results
are **not yet assumed** and must be independently measured in CI.

## Proof standard and CI isolation

The dedicated research workflow `.github/workflows/v30-ngp-original-mono-psg.yml` generates each 0x00-header .ngp solely in a temporary build directory, then passes it into the **real NeoPop Libretro CoreSession** through the existing strict `tools/probe_ngp_mit_homebrew.py --child` path. [Original-ROM real-native CI 42449197364](https://github.com/MasynNay/anything-plays/actions/runs/42449197364) tested all four PSG initialization variants: **0/4 produced nonzero PCM, and 0/4 produced nonblank video**, despite native input callbacks and save-state API responses. The original generated headers were authentically 0x00 but execution/sound remains unproven. Only measured **nonzero native PCM** is allowed to set the audio diagnostic true. Real native changing video and camera/manual input are separate requirements and can still fail even if this ROM successfully tests PSG hardware; this minimal tone ROM intentionally does not implement a polished video demo.

The workflow retains only `NGP_ORIGINAL_MONO_PSG_UNAPPROVED.json` and `SHA256SUMS.txt`, not cartridge output, screenshots, native cores or game assets. A green research job means the experiments ran and their results were audited; it **does not imply actual sound was produced**. If it produces real PCM but not video, extend the original cartridge with a genuine changing monochrome display and native input logic in a later, independently verified experiment. If no sound is produced, investigate boot/PSG initialization and CPU execution before asserting an emulator audio defect.

No 3.0 release-acceptance audio, physical QA, corresponding source, third-party licensing, or public binary distribution approval flags are changed. The application remains at 18 console profiles and 11 cores with v2.0 public unchanged.

## Verified original monochrome PSG and source-built changing K1GE video

[PR #64](https://github.com/MasynNay/anything-plays/pull/64) merged after
the [real native run 42450342688](https://github.com/MasynNay/anything-plays/actions/runs/42450342688)
confirmed **all four corrected genuine 0x00 monochrome PSG programs emitted
qualifying nonzero native PCM**. The original sound path is therefore
validated on the Linux test core for sound callbacks, but the four tone-only
cartridges did **not** draw changing nonblank K1GE video; no full monochrome
video/audio/input acceptance or public-redistribution approval followed.

The next exact original-source-only experiment uses
`tools/build_v30_ngp_mono_native_av.py`. It retains the byte-exact proven
B8=55/B9=AA chip+Z80 sound initialization and direct T6W28 tone. It writes
the **native K1GE** (not K2GE color) window origin/size registers at
`0x8002..0x8005` and `BG_COL` at `0x8118` via documented TLCS-900/H
`LD A,#imm` / `LD (abs16),A`. The background alternates two visible
monochrome shades (`0x83` and `0x87`) inside the defined window while
preserving the outside margin, using bounded byte-register DEC/JR loops and
watchdog refreshes. The actual native NeoPop graphics implementation
in `mednafen/ngp/gfx.c` independently confirms these K1GE memory-mapped
addresses and background grayscale behavior.

The new `tools/probe_v30_ngp_mono_native_av.py` runs only an original
temporarily generated 0x00 mono cartridge in the real NeoPop CoreSession
with native PCM, frame and manual/camera callback measurements.
`.github/workflows/v30-ngp-mono-native-av.yml` retains **only reviewer
JSON + SHA256SUMS**. The source-only proof is not promoted until its
**real changing video and full A/V/input results** are inspected. The
per-platform physical gameplay, genuine battery/flash persistence,
license/source and binary redistribution gates stay **false** regardless
of a green research job.
