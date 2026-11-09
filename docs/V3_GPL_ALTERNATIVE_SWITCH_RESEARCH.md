# Anything Plays 3.0 — SNES + four Sega profiles using non-NC GPL candidate cores

**TECHNICAL RESEARCH PASSED, NOT A GPL DISTRIBUTION DECISION OR PUBLIC RELEASE.**

The existing public v2.0.0 is unchanged. The current full offline 3.0 developer preview still bundles the original noncommercial Snes9x and Genesis Plus GX natives. This research proves that **source-built Beetle Supafaust (original GPL-2.0-or-later grant)** and **source-built BlastEm (GPLv3)** can operate through Anything Plays' real `CoreSession` for SNES + Genesis + Master System + Game Gear + SG-1000, without downloading retail ROMs or distributing any replacement binaries.

## Exact original source and native inputs

The experiment downloads only the original immutable artifacts from:

- [4-OS pinned source-built Supafaust run 42494297281](https://github.com/MasynNay/anything-plays/actions/runs/42494297281), source `libretro/supafaust@642d1d1b6684aa7e306a02a89885f3f5456a5157`.
- [8-job pinned source-built GPL candidate run 42496671418](https://github.com/MasynNay/anything-plays/actions/runs/42496671418), using ONLY the four BlastEm native artifacts from original `libretro/blastem@2230addc4dd74dd094fd264987fd808abba32d0e`.

Per target, `tools/probe_v30_gpl_core_switch.py` independently checks every **original source/native/license checksum entry**, exact native file SHA and pinned original upstream source commit. Original native research artifact folders also contain a narrow allowlist of original post-checksum diagnostic reports and homebrew screenshots, neither loaded nor executed as source/native inputs. Extra unexpected files and tampered original sources/libraries fail.

## Genuine combined switch results — November 8, 2026

[Four-platform native CI run 42500154650](https://github.com/MasynNay/anything-plays/actions/runs/42500154650) **passed all four real OS jobs** after the initial test validator was corrected to allow only known post-build diagnostic reports. Final [source checks 42500154701](https://github.com/MasynNay/anything-plays/actions/runs/42500154701) also passed.

One disposable process per OS contains the SAME frontend, sequentially starting and terminating seven actual `CoreSession` instances. Each cycle loads a source-authored, noncommercial-ROM-free original homebrew game, produces changing nonblank RGB frames and more than 100 genuinely nonzero native PCM values. The sequence is **SNES → Master System → Game Gear → SG-1000 → Genesis → SNES again → Master System again**. Original Genesis homebrew uses the previously tested 10-byte TMSS-safe startup variant, not a modified retail game.

| Target | Passed / actual cycles | Native video frames in the seven ~5 s sessions | Exact original small research evidence ZIP SHA-256 |
| --- | --- | --- | --- |
| Windows x64 | 7 / 7 | 296, 300, 300, 249, 300, 296, 300 | `4945832fb583317c885caf8f8623627c79b5fac2074918f9c8eed7bdee292fbe` |
| Linux x64 | 7 / 7 | 300, 300, 300, 249, 300, 300, 300 | `6a17fb5e85a8b3a6a136309d65d6e5f9e44461f044e5607a22ffd455947aaec9` |
| macOS ARM64 | 7 / 7 | 297, 303, 300, 252, 302, 304, 300 | `52a2a00265e8b6f70a0601ee1dd76ca4f60b743593344465967daf52fdccab51` |
| macOS Intel | 7 / 7 | 299, 302, 305, 252, 306, 304, 306 | `db24bc41ed707890cb3e4e10d9889e61118927fd3c07678e1923f5c1ece72aca` |

Each original 4-OS Actions evidence ZIP was independently downloaded from run 42500154650, verified to contain exactly `GPL_ONLY_NATIVE_SWITCH_UNAPPROVED.json`, parsed, and checked to show **7 successful results, zero native child errors and all four distribution/license/physical approval flags FALSE**. These observed frames are genuine native video callbacks, not proof of actual monitor rendering, frame pacing or real-game compatibility.

## What this accomplishes and what it does NOT

**Proven:** two source-built GPL license families work in the same real frontend on all four architectures; replacing the SNES and shared four-Sega-console **core families** is a technically viable research avenue that can preserve all **18 profiles** and **11 native core slots**. These alternatives are actually different native binaries, and their identity must never be disguised under a Snes9x or Genesis Plus GX manifest/source identity.

**Not proven:** that GPLv2-or-later Supafaust + GPLv3 BlastEm can be redistributed together with the remaining application's **GPLv2-only** cores or other dependencies under the same combined-work rules. The whole exact binary/component collection needs an independent GPL compatibility and exact corresponding-source audit, including all remaining 9 core families, complete Dolphin Sys and frozen native dependencies. No author permission to relicense GPLv2-only binaries can be inferred from this test.

**Not tested:** a real full 18-profile/11-core installer with both substitutions, actual retail/authorized cartridge compatibility, saved game SRAM, webcam controls, physical audio, sustained use, signed/notarized packages, or gameplay acceptance on a person's physical devices.

**No core names or runtime selections were changed in the app.** The original 2.0 stable release, 3.0 preview binaries, actual user libraries and 3.0 production lock remain untouched. All original NC and full-release flags stay explicitly unapproved.

**Next engineering gate:** stage a separate source-verified **18-profile/11-core GPL-alternative four-platform offline preview** with exact new native names/manifest identities, not masked original NC names, and run full native A/V, switching, save/camera and installed package tests. Hold any public binary release until GPL/core/source rights and actual owner four-platform QA are independently complete.

## External licensing route

The user additionally requested clarification of Snes9x and Genesis Plus GX's actual free educational career-portfolio noncommercial permissions. Attempted public issue creation on **`snes9xgit/snes9x`** and **`ekeeke/Genesis-Plus-GX`** on November 8, 2026 through the linked GitHub integration returned HTTP 403 `Resource not accessible by integration` for **both**. **No message was posted, no permission received.** The ready-to-send drafts remain at [portfolio permission requests](V3_PORTFOLIO_PERMISSION_REQUESTS.md); those public upstream repositories require direct submission through an account with rights, or an official alternate contact channel. The GPL-alternative research is a parallel path, not evidence that third-party copyright holders waived existing rights.
