# Monochrome Neo Geo Pocket: original MIT audio evidence search

**Status: RESEARCH ONLY.** No claim of audible monochrome NGP homebrew yet, and no alteration of the stable 3.0 release approval. The existing pinned monochrome alignment cartridge in `tools/ngp_mit_fixtures.py` renders video and polls real inputs but emitted zero native nonzero PCM values on four target platforms. That is insufficient sound evidence, not proof the NeoPop emulator cannot play audio.

## Exact source corpus

The pinned upstream [Tixul/Ngpcraft_emulator](https://github.com/Tixul/Ngpcraft_emulator) **MIT-licensed** commit `93b1fd666ff375afcbb48079fbcf61dbb99b86b4` contains exactly **14 original `.ngp` monochrome calibration cartridges** under `hw_calibration/`. Their exact Git blob SHA-1, byte lengths and paths have been recorded in `config/v3.0-ngp-mono-mit-candidates.json`, directly from that commit's Git tree.

The standalone research pipeline `.github/workflows/v30-ngp-mono-mit-matrix.yml` fetches the 14 blobs to temporary runner directories, checks Git blob SHA-1 and exact byte lengths, loads each into a real Mednafen NeoPop **native Libretro core** with the existing `tools/probe_ngp_mit_homebrew.py --child`, records the actual native video/PCM/input results, then deletes each ROM when the temporary directory closes. It records the native core's SHA-256 (the downloaded research core itself is not a frozen public-production native binary). A candidate is tagged **audible only** if the actual core reports >100 native nonzero PCM values, >1,000 native PCM frames, positive peak and a passing native audio gate; a candidate is tagged full native AV/input only if the existing strict video, audio and two-input acceptance all pass. It never synthesizes any audio or changes thresholds.

The research workflow publishes **only a JSON research report and a SHA256SUMS.txt** to GitHub Actions for 60 days. No ROM, game, BIOS, video capture, native library or public application release is included. Full upstream MIT copyright/license terms remain with the upstream repository. The framework's own licensing and combined-GPL/noncommercial app questions remain unresolved.

## If all 14 prove silent

This establishes that the fourteen **tested calibration fixtures** are unsuitable for audible acceptance on the tested NeoPop build. It does **not** establish that all monochrome games or the NeoPop core are silent. Continue by obtaining or building an authentically monochrome, **source-licensed audible homebrew**, with proper compiler/toolchain provenance and native checks on all four operating systems. The publicly documented NgpCraft base template has an MIT sound driver but builds a **color** `.ngc` cartridge by default and documents a historical proprietary Toshiba compiler; renaming it `.ngp` would be invalid. Do not bundle proprietary toolchain binaries.

## Remaining release rule

Native audio on a valid .ngp, genuine changing K1GE-compatible video, native manual/camera input and expected save/endurance tests must be demonstrated independently. Neither a candidate research report nor a green diagnostics-only workflow sets `config/v3.0-release-acceptance.json` audio, physical or license flags true. Public 3.0 remains blocked until all external licensing/source and real hardware gates are satisfied.
