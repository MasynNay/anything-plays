# Anything Plays 3.3.0

Version 3.3 improves **GameCube preview responsiveness, camera and controller fault recovery, input latency observability, and Stream Mode reliability** while preserving the original graphics, interface layouts, custom controller mapping, and existing console support.

## Improvements
- GameCube optional GPU preview readback is capped separately from native emulation. A broken optional monotonic clock no longer leaves the video preview indefinitely frozen.
- Stream Mode provides local bounded-memory cadence and latency diagnostics, faster unchanged-frame reuse, and strict stop/ROM-switch camera/game source cleanup for OBS window capture.
- Webcam discovery protects against out-of-order results, driver hangs and endless retry threads. A timeout never force-terminates a blocked OS camera driver.
- SDL controller reconnects, input release and clipboard/status diagnostics now handle failing native adapters without leaking OS paths.
- Native GameCube audio reports distinguish PCM generation, queued delivery, device underflows, and an actual available output stream; they do **not** claim that an audible speaker was verified.

## Install and upgrade
Choose the **Windows x64 EXE**, **Linux x64 DEB**, **Intel Mac DMG**, or **Apple Silicon Mac DMG** below. These are full-native, 11-core packages supporting 18 console profiles. This release uses the **existing 3.1.x/3.2 app installation and local-settings identity**, not the separate 3.3 private QA identity. Back up custom profiles, ROM directory information and game saves before upgrading. Public v3.2.0 downloads remain available for rollback.

## Verified / limitations
Source Python 3.12/3.13, native mGBA regression tests, three-minute synthetic Tk Stream Mode endurance, and four native platform frozen/installed QA builds are automated. Exact final 3.3 stable-identity installer hashes and source manifest are attached.

**Not verified on actual owner hardware:** a full 30-minute physical GameCube session with real GPU, controller, speakers, saves/restart; webcam, two-player tracking and OBS capture across the operating systems; retail-game compatibility; in-place upgrade from a real user's saves; and notarized installer trust. No ROMs, BIOS or commercial game images are included. Windows installer is not Authenticode-signed, and Macs are ad-hoc signed and not notarized. GameCube performance varies by machine.

## Source and license
Anything Plays application code is MIT licensed. **Emulator cores, SDL, pygame, OpenCV and other dependencies retain their own licenses** and may restrict redistribution/reuse; in particular, Snes9x is not under the application's MIT license. This scoped free, noncommercial, nonpromotional release reuses byte-identical eleven-core native libraries and corresponding original notices from the published 3.2.0 installers, plus the existing source companion and upstream original emulator archives linked from the source access report. No blanket commercial rights or independent audit of every transitive dependency is claimed.

See `FINAL_SOURCE_ACCESS_REVIEW.md`, `FINAL_QA_MANIFEST.json` and `SHA256SUMS.txt`. Previous stable version and rollback: https://github.com/MasynNay/anything-plays/releases/tag/v3.2.0
