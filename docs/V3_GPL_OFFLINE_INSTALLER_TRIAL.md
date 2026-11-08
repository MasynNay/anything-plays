# Anything Plays 3.0 — complete offline GPL-alternative installer trial

**STATUS: UNAPPROVED NATIVE RESEARCH. NOT A PUBLIC 3.0 DISTRIBUTION.**

This is a complete actual offline **18-console-profile / 11-native-core** preview build using the same Python application, webcam/control UI, local ROM shelf, existing GameCube/Dolphin Sys and the same per-platform installer scripts, with only two core-family substitutions:

| Five impacted console profiles | Original 3.0 test core NOT packaged in this trial | Actual source-built replacement | Original reviewed checkout |
| --- | --- | --- | --- |
| Super Nintendo | Snes9x (custom NC) | `mednafen_supafaust_libretro` (GPL2-or-later file grant) | `libretro/supafaust@642d1d1b6684aa7e306a02a89885f3f5456a5157` |
| Genesis, Master System, Game Gear, SG-1000 | Genesis Plus GX (custom NC) | `blastem_libretro` (GPLv3) | `libretro/blastem@2230addc4dd74dd094fd264987fd808abba32d0e` |

All **nine other original Libretro core ZIPs** and the original exact offline **Dolphin Sys ZIP** are copied **byte for byte** from the separately verified four-platform native-input archive set, with original SHA-256 validation before replacement. The assembled test-only native set contains **11 real Libretro cores plus Dolphin Sys**. The original reviewed complete source/native artifacts for Supafaust and BlastEm are verified again per target: exact original source commit, original license notice, native image SHA-256 and source ZIP. The alternate installed core filenames reveal the *actual* emulators: the original `snes9x_libretro.*` and `genesis_plus_gx_libretro.*` are **not in this trial installer**. The old noncommercial notices may remain among the repository's original third-party history notices, but the research payload contains neither old NC core library.

## Real application and offline workflow

`AP_V30_GPL_TRIAL=1 AP_V30_TEST_CORES=1 AP_RELEASE_BUILD=0 AP_V30_APPROVED_RELEASE=0` selects this lane **at build time only**, with a required `AP_CORE_ARCHIVE_DIR` holding exact stage input ZIPs. It is impossible to use this lane with an approved production build. The real Windows Inno Setup, Linux DEB and Mac DMG preview scripts now copy the exact 11 new core names, original GPL license texts and a `V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json` manifest. The manifest is preserved **in the installed core directory**.

The installed application's normal `SYSTEMS` registry still has all original profiles, extensions and user preferences. Its `core_locator.find_core()` reads the *trial marker only for SNES and the four Sega systems* and returns the genuine matching Supafaust or BlastEm library path. The marker includes the exact native file SHA-256 and immutable upstream source revisions, checked locally at launch without network. It refuses missing, symlinked or tampered native libraries; if the marker is corrupted, affected profiles fail closed and **do not silently load a noncommercial binary or another user-owned core**. Every non-trial installation still uses its original core discovery and stable 2.0 behavior; no user needs to edit an environment variable to play an installed lab preview.

`.github/workflows/v30-gpl-offline-installer-trial.yml` obtains the **original** unapproved native input artifacts from the already-green four-platform full preview run 42437133733, **original source-built** Supafaust artifacts from 42494297281 and **original source-built** BlastEm artifacts from 42496671418, and invokes the existing real install builder on Windows x64, Linux x64, macOS ARM64 and Intel. It validates the *actual packaged* core file hashes, all profiles, both absent old NC native images, and the source manifest. It then runs original project-authored homebrew native A/V for **SNES + all four Sega** against the binaries extracted from the staged application (not merely the original research source folder). The standard packaging scripts also verify all other nine cores, Dolphin Sys, third-party notices, GB/GBC/GBA coverage, icon and packaged artifact integrity.

**Only JSON research evidence is uploaded to GitHub Actions. The actual test-only installers, native research libraries, BIOS and ROMs are NEVER uploaded or publicly released through this workflow.** This is deliberate because the full combined GPL2/GPL3 license/version review and corresponding source/dependency obligations have not been approved.

## Source and rights still to solve — independent of user income

This is a **source-built alternative to the two custom noncommercial core families**. It avoids requesting permissions from their copyright owners if the final production binary genuinely excludes them. It does NOT by itself establish that a current single-package frontend with mixed GPLv2-only and GPLv3-only emulator components satisfies compatible combined-work licensing obligations. The actual source-level and binary build flags must be audited for the remaining cores, dependencies, Dolphin and ParaLLEl-N64; investigate GPLv2-or-later or otherwise compatible licensing grants and legally appropriate architecture before choosing a final public binary. Only then can strict `config/v3.0-core-lock.json` and `config/v3.0-release-acceptance.json` be populated with reviewed, source-corresponding binary identities.

The full real-device playtesting also remains mandatory: camera movement, sound through speakers, physical controllers, saves and repeated ROM switching, GameCube longrun stability, every named system and all four OSes. CI native homebrew tests alone do not equal that proof. No silent publisher or false approval flags are introduced.

## Scope of noncontact

Per the owner's explicit instruction, **no upstream rights-holder contacts, GitHub issues in outside repositories, licensing emails or requests to anyone else will be sent**. The engineering work proceeds independently within the owner's repository. Stable public v2.0.0 remains available; a lawful full offline v3.0.0 binary awaits genuine technical, licensing, source and physical acceptance.
