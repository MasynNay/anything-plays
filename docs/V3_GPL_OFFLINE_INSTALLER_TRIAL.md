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

## Verified complete four-platform actual packaged-app tests — November 8, 2026

[Original complete 18-profile/11-core GPL-alternative offline lab run 42503215322](https://github.com/MasynNay/anything-plays/actions/runs/42503215322) **PASSED ALL FOUR JOBS** on the true Windows x64, Linux x64, macOS Apple Silicon and Intel Mac runners. The same commit's [normal original offline installer regression run 42503215187](https://github.com/MasynNay/anything-plays/actions/runs/42503215187) and [source CI 42503215279](https://github.com/MasynNay/anything-plays/actions/runs/42503215279) also passed. The genuine executable Windows installer, Linux DEB and both macOS DMGs were built **locally in their isolated workflow runners**, with all eleven newly staged native cores and original Dolphin Sys. Only the seven research JSON reports per host were archived; no unapproved binary installer was published or uploaded as an artifact.

The original four source-independent evidence ZIPs were downloaded and individually inspected: each archive has *exactly seven* JSON reports, an original source/native staging manifest, the complete installed-core SHA-256 provenance and exactly five original nonretail SNES/Sega A/V reports. No ZIP contains a game ROM, native core library, or installer. Every installed candidate report has `installed_core_count=11`, `console_profiles=18`, original Dolphin Sys verified, genuine `mednafen_supafaust` + `blastem` core identities, zero `snes9x`/`genesis_plus_gx` binaries, and FALSE source/legal/physical release approval.

| Actual host | Original research-only artifact ID | Original evidence ZIP SHA-256 | Authentic installed native SNES/SMS/GG/SG1000/Genesis frame counts | Native tests |
| --- | ---: | --- | --- | --- |
| Windows x64 | 13626032695 | `c2abca16ff73910b303ef682f116444985d63401bdf663416c1871e51fb3b062` | 358 / 359 / 360 / 359 / 360 | 5/5 passed |
| Linux x64 | 13626745972 | `bb27a71a96e8b8a46ba4d782600b601cbd6c96d06c7914bacd3a9b41076f10c1` | 359 / 360 / 360 / 360 / 360 | 5/5 passed |
| macOS ARM64 | 13626357814 | `0480c47dfc64fe8922d6ba63446b329ab753a96a423720421deb46d94019920a` | 360 / 360 / 360 / 361 / 364 | 5/5 passed |
| macOS Intel | 13626890568 | `addbffe49d68478f82e4561616d0e4184f726f074f92d9ba3226fd77cba9e557` | 363 / 365 / 368 / 367 / 363 | 5/5 passed |

**All 20/20 individual original SNES/four Sega installed-library video and native PCM checks passed**, each with real exit code zero, changing video and nonzero PCM. These tests measure native emulator callback results, **not** physical speaker playback or installed-game full compatibility. Existing base full-offline QA checks the remaining nine cores and Dolphin Sys, but the new alternative lab's explicit A/V loop covers only the five replaced console profiles. Signed Windows and Apple-notarized Mac releases are not claimed.

### Windows no-extra-download runtime

The newly compiled Windows Supafaust and BlastEm libraries require the MinGW `libwinpthread-1.dll` runtime in addition to ordinary Windows system DLLs. The trial now copies the actual original MSYS2 MINGW64 runtime byte-for-byte with SHA-256 in the test manifest and Windows installer, validates its integrity before loading a core, and permanently registers **only that verified installed core directory** using `os.add_dll_directory`. The original installer no longer needs a separately installed MSYS2 runtime to inspect or launch the alternative cores. An early test exposed the missing dependency, which was fixed rather than suppressed. The upstream [Winpthreads COPYING](https://github.com/mingw-w64/mingw-w64/blob/master/mingw-w64-libraries/winpthreads/COPYING) grants permissive rights subject to copyright/notice reproduction; the exact verbatim original notice is tracked at `licenses/Winpthreads-COPYING.txt` and is required by `verify_bundle.py` on Windows trial builds. The exact corresponding MSYS2 runtime package revision and all transitive compiler dependencies still need formal complete-corresponding-source review before any stable binary distribution.

### QA and rights still strictly withheld

The test-only marker includes explicit `public_binary_distribution_approved=false`, `combined_gpl_license_reviewed=false`, `production_core_substitution_approved=false`, `physical_qa_approved=false`. Neither the source GPLv2+/GPLv3 test successes nor a permissively licensed MinGW runtime resolve the separate GPLv2-only vs GPLv3-only library compatibility review for other emulators. The exact source correspondence for the other nine binaries plus full Dolphin Sys still needs final review. The app cannot be called a production release until genuine physical camera/controller/speaker/save/endurance review and complete source/license decisions. **No outside repository contacts or permission requests are made.**

### Final post-notice original evidence — merged implementation

[PR #87](https://github.com/MasynNay/anything-plays/pull/87) was **squash merged** at `01e1ac7f52bfac13f5c4ebe5ab92bd45b9ca83bd` after the final notice-verified workflow [42503875717](https://github.com/MasynNay/anything-plays/actions/runs/42503875717) **passed Windows/Linux/Mac ARM/Mac Intel 4/4**, normal complete offline lab [42503875902](https://github.com/MasynNay/anything-plays/actions/runs/42503875902) **passed**, and [source CI 42503875701](https://github.com/MasynNay/anything-plays/actions/runs/42503875701) **passed**.

Independently downloaded and parsed the ORIGINAL final four artifacts again (distinct from earlier green run 42503215322). Each original ZIP contains exactly seven original research JSON files: five genuine installed-native SNES/Genesis/SMS/GG/SG1000 video+PCM results (each `passed=true`, `native_exit_code=0`), one exact native staging/source record and one complete packaged-core manifest. Each proves **11 original/alternative core slots, 18 profiles, Dolphin Sys present, original Snes9x/Genesis Plus GX native binaries absent, and ALL public distribution/legal/physical flags FALSE**.

| Target | Original FINAL Actions artifact ID | Original FINAL downloaded ZIP SHA-256 | Native installed test evidence |
| --- | ---: | --- | --- |
| Windows x64 | 13626379191 | `7477192c1f636f315806b95dbe2a3ebf1b4221a30be9437f926a6454920f713d` | 5/5 original source homebrew A/V pass; original `libwinpthread-1.dll` runtime SHA-256 `98a4fea591385952cad1c532f4a92606358630976e9ede5fcf115ab945305a09` |
| Linux x64 | 13626523554 | `575ee1b775f13a99421c91f155a1e0f604da2219a3c249197f37b96d47e806e7` | 5/5 original source homebrew A/V pass |
| Mac ARM64 | 13626239586 | `e88aa8f3a1e606dbf49d788f53dfbdaa51d266f817d2ad81eaa963abb798c5ca` | 5/5 original source homebrew A/V pass |
| Mac Intel | 13626896888 | `a516df606c422bc4bc23c41d0a6fa5a8f2ce5a3810c1a8c840d7776f7cc9ecd6` | 5/5 original source homebrew A/V pass |

These four archives are **small JSON reviewer evidence only**. The four actual working, unapproved prototype installers were compiled on their native CI runners but were *not uploaded as public binaries*, because a full GPL combined-work/component-specific license review, corresponding source/dependency audit and physical user acceptance have NOT been completed. Do not retrospectively reclassify their evidence as permission to release a full 3.0 installer.

## Current three-family complete offline candidate — merged PR #90 (November 8, 2026)

Earlier sections document the historical two-family SNES/Sega trial. **The latest four-platform candidate additionally replaced the old PC Engine Fast nightly with an independently source-built core**, retaining the identical 18 console profiles and 11 native core slots. Exactly **eight** other original core ZIPs and the original Dolphin Sys archive remain unchanged. The exact original source revision for that **replacement** is `libretro/beetle-pce-fast-libretro@2de1ce1c3f237b161c126c54ba407990bb86d1e9`; this does **not** invent or claim an upstream source revision for the discarded old PCE nightly.

[PR #90](https://github.com/MasynNay/anything-plays/pull/90) merged at `11a08722a6406add1267975d36fd34a9385ecd6f` after [original full four-platform offline installer build 42508423915](https://github.com/MasynNay/anything-plays/actions/runs/42508423915) and [source checks 42508423910](https://github.com/MasynNay/anything-plays/actions/runs/42508423910) **both passed**. Every real CI OS independently verified the three source-built family identities, the other eight originals, Dolphin Sys, full installed-native 18/11 provenance and the absence of the two noncommercial original native files. Each actual installed original-source PC Engine HuCard program delivered real changing video and nonzero native PSG PCM; original installed SNES/four Sega AV and seven serial SNES/Sega relaunch cycles also passed.

| Actual OS | Original research JSON ZIP artifact ID | Independently downloaded original ZIP SHA-256 | Source-built installed PCE video frames / nonzero PCM samples |
| --- | ---: | --- | --- |
| Windows x64 | 13627784169 | `bc073bcda66e399b534dcd8fa25aec334331dcaffa1bafb37827d9d4321ac664` | 599 / 879,369 |
| Linux x64 | 13628298006 | `00fcda178eecfac4724e588c56b545b525438b79cc99f3900121c0a25c693868` | 598 / 877,899 |
| Apple Silicon | 13628567397 | `6f7bc86a52732ad341dba6e925b736e68bbad465c69a37151766074301a3305a` | 599 / 879,369 |
| Intel Mac | 13628905898 | `f9d070987bf643a8f9a38e4d564e002697c98e9a75a4d075ec26a2164859533c` | 595 / 873,493 |

Each originally downloaded ZIP contains exactly **9 JSON evidence files** and no emulator library, actual installer, BIOS or game ROM. Every repeated-switch result is `passed=true` with seven sessions and child exit code 0. Explicit release, source/legal compatibility and physical acceptance flags stay **FALSE**. The test-only complete Windows/Linux/macOS installer files were built in CI but were **not published or uploaded**.

Source-reviewed 3.0 production core selection now supports the genuine GPL-alternative names thanks to [merged PR #89](https://github.com/MasynNay/anything-plays/pull/89), but the current approved-production workflow still has an **unimplemented original-native input and installed-runtime handoff** for those alternative binaries. The full combined GPL2/GPL3 rights/source audit (including the eight remaining original native libraries, Dolphin Sys and transitive dependencies) and real-device acceptance are still incomplete. **No outside rights-holder requests, external repository submissions or user GameCube/N64 repeat tests.** No public 3.0 release approval is claimed.
