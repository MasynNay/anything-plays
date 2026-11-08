# Anything Plays 3.0 — real-device QA evidence checklist

**Status: owner-reported, test-only evidence. Not 3.0 public release authorization.**

## Why this exists

GitHub Actions can validate 18 console profiles, 11 bundled native cores,
offline archive resolution and many individual homebrew playback paths.
It **cannot** physically inspect your Windows, Linux, Apple Silicon or Intel
Mac computer, confirm that an actual retail/homebrew game plays and saves
in the installed desktop app, confirm webcam-zone movement with real light
and hardware, or establish that it stays stable over an extended play session.

The source-only `tools/v30_physical_qa.py` records the missing practical
evidence. It uses **only the Python standard library** and the existing
18-console system registry. It does not need Internet access or ROM data,
open the webcam, automatically run any emulator or modify release approvals.

## Start a private local QA session

Use the **exact test installer you physically installed**, and the **full
40-character GitHub source commit used to build that installer**. Run in a
local checkout of the same 3.0 development code, with Python 3.12 or 3.13.

```bash
# On Windows, macOS or Linux (use python instead of python3 if appropriate):
python3 -m tools.v30_physical_qa init \
  --installer "/path/to/the-actual-3.0-preview-installer" \
  --commit "40-character-GitHub-source-commit" \
  --out "$HOME/AnythingPlays-v30-qa.json"

# Walk through the host install checks and each console interactively.
python3 -m tools.v30_physical_qa wizard \
  --report "$HOME/AnythingPlays-v30-qa.json"

# Quit the wizard with q and return later; inspect remaining checks.
python3 -m tools.v30_physical_qa status \
  --report "$HOME/AnythingPlays-v30-qa.json"

# Export only a reviewer JSON and a checksum, never your game files.
python3 -m tools.v30_physical_qa export \
  --report "$HOME/AnythingPlays-v30-qa.json" \
  --output "$HOME/AnythingPlays-v30-qa-evidence"
```

The tool autodetects the native host architecture. Windows x64 expects
a local `.exe`, Linux x64 a `.deb`, and macOS ARM/Intel a `.dmg`.
It SHA-256 hashes the **actual local installer** and records its base
filename, byte count and full source revision. It refuses mismatched
architectures and an invalid source commit. One report is required **per
platform and per final installer revision**. The four reports cannot be
interchanged or assumed equivalent.

Run the wizard **with the actual installed application open**. For each
check, enter `p` only after verifying it on your actual machine;
enter `f` for a reproducible failure, `s` for not tested, or `q`
to save progress. A unit test, an emulator backend that merely loaded,
or a GitHub CI artifact is **not** a passing real-machine observation.

You can also record a single result without the wizard, for example:

```bash
python3 -m tools.v30_physical_qa record \
  --report "$HOME/AnythingPlays-v30-qa.json" \
  --system gamecube --check audible_audio --result pass
```

## Required physical checks

There are **six** host/installer checks and **eight** system checks for
each of the **18** console profiles: **150 observations per platform**,
600 observations across four supported hardware targets.

| Scope | Exact check | What you must observe on a real machine |
| --- | --- | --- |
| Installer | `fresh_installer_clean_install` | The exact hashed preview installer completes a fresh user installation, app opens without error |
| Installer | `no_extra_emulators` | You do not install RetroArch, Dolphin, separate cores or firmware for the selected supported cartridge path |
| Installer | `native_integrity_match` | The installed 11 native libraries and Dolphin Sys match the installer provenance and hashes |
| Installer | `camera_device_live` | Real webcam image works, selection and visible button zones respond |
| Installer | `long_run_session_stable` | Extended actual installed app use remains stable with no crash/leak or unexpected error |
| Installer | `no_unexpected_network` | Initial play from the bundled installer works without network downloads |
| Each console | `offline_start` | Supported, legally possessed test game/homebrew starts in the embedded app with Internet off |
| Each console | `embedded_video` | Real game image animates in the application window, not in another emulator window |
| Each console | `audible_audio` | Sound comes from actual computer speakers and is appropriate to that game |
| Each console | `keyboard_gameplay` | Actual game responds to configured in-app keyboard controls |
| Each console | `camera_controls` | Physical webcam zone movements move/control the actual in-app game |
| Each console | `rom_change_restart` | Game exits/unloads, another compatible ROM loads, and input/video/audio recover without restarting the app |
| Each console | `save_then_reload` | A *real game-state change* persists after an app restart; confirm in the game, not only that a save file exists |
| Each console | `extended_play_stable` | Play remains responsive over a genuine sustained session; note failures in an issue |

For **Nintendo 64**, explicitly repeat unload/load on at least two
different legally possessed compatible ROMs; avoid the historical bug
where the first launch works and the second silently fails. For **GameCube**,
confirm real hardware-accelerated embedded Dolphin video, controller
response, sound and saving using a lawful test game or homebrew, without
launching standalone Dolphin. For **Neo Geo Pocket** and **Color**, confirm
real gameplay in addition to the previously proven CI homebrew audio/video
paths. For **PC Engine**, only the advertised HuCard path is in 3.0 scope;
CD titles requiring a BIOS are not.

A `pass` in these local records is a **human self-report**, not automated
proof and never a copyright, redistributability or core-build approval.
If something is unknown or untested, leave `not-tested`: do not invent
a green result to finish a checklist. If the result is `fail`, preserve
the issue before retesting; the next release build requires a fresh,
checksum-identified QA record.

## Evidence safety and next review

The local report stores only status selections, installer base filename,
SHA256, build revision, timestamps and 18 registry names. It does **not**
store personal names, machine serials, game names, ROM paths, ROM bytes,
webcam photos, camera recordings, saved games or screenshots. Any optional
screenshots or logs must be separately reviewed for personal/private data
and appropriate game copyright before sharing.

The `export` command writes exactly two reviewer files, with the
second file independently hashing the first. It never uploads data or
marks `config/v3.0-release-acceptance.json` fields true. Even if **all
150 observations pass** on each platform, independent review and the
full 44-core source/license rights approval are still required.
A reviewed human/real-device evidence packet may **later** support a
carefully scoped change to the release acceptance manifest, but it
must not be substituted for legal review, matched sources or actual
production installer/signing validation.

GitHub's 3.0 publication workflow remains fail closed until all
source rights, physical validation, true corresponding sources,
production installer hashes and deliberate owner publication approval
are satisfied. See
[V3_PUBLICATION_RUNBOOK.md](V3_PUBLICATION_RUNBOOK.md),
[V3_CORRESPONDING_SOURCE_REVIEW_SCHEMA.md](V3_CORRESPONDING_SOURCE_REVIEW_SCHEMA.md)
and [release blocker #28](https://github.com/MasynNay/anything-plays/issues/28).
