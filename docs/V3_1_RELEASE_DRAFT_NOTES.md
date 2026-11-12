# Anything Plays 3.1.0

**PREPUBLICATION DRAFT — NOT APPROVED FOR PUBLIC RELEASE**

Anything Plays lets a camera, tracked objects and manual inputs control classic console games. Version 3.1 extends the 18-console desktop application with real gamepad support, clearer display frames and a dedicated streamer-friendly presentation. Built for Windows x64, Linux x64, Intel Mac and Apple Silicon.

## What's new

**Stream Mode for creators.** Open it beside **View mode** or with **Ctrl+Shift+S**. A separate **Stream Output** window and **Stream Settings** window offer a Nintendo DS-inspired top/bottom default, or a side-by-side layout. Swap game and camera placement, change proportions, select any of 16 themes, adjust bezel widths/colors, choose 15, 24 or 30 FPS, and resize without distorting either image. In OBS, capture **Stream Output**, not **Stream Settings**. External emulators without an embedded frame source display a clear placeholder rather than simulated game video. OBS manages audio and recording; Anything Plays itself does not stream or record.

**Polished camera and emulator presentation.** Matching, theme-aware display bezels distinguish camera tracking from game output, using status indicators driven by real camera/emulator state instead of decorative fake activity.

**Optional controller input.** Standard SDL gamepads can be mapped per console. The controller configuration UI includes visual mapping, rescan, button/stick preview, and local redacted diagnostic copying. Controller input does not inject keyboard events system-wide.

**Safer long-term operation.** Controller disconnect, rescan and focus-loss recovery releases held inputs correctly. Stream Mode reuses existing game/camera frames without starting new capture devices, bounds image caches and rendering work, and cleans up when closed. Camera disconnects clear stale private output frames while intentionally selected reference images remain labeled.

**Independent settings.** The real 3.1.0 installer uses a separate app identity and settings directory. It copies existing RC2 preferences once on initial launch without overwriting stable 3.0, RC1 or RC2 user data.

## Downloads prepared for review

| Platform | Filename |
| --- | --- |
| Windows 64-bit | `AnythingPlaysSetup-3.1.0.exe` |
| Ubuntu/Debian 64-bit | `anything-plays-31_3.1.0_amd64.deb` |
| macOS Apple Silicon | `AnythingPlays-3.1.0-macos-arm64.dmg` |
| macOS Intel | `AnythingPlays-3.1.0-macos-x64.dmg` |

The release draft must also contain `FINAL_QA_MANIFEST.json`, `SHA256SUMS.txt` and `FINAL_SOURCE_ACCESS_REVIEW.md`. Each installer contains all 18 console profiles and 11 original source-built emulator core families. **Game ROMs, game BIOS files and licensed game media are not included.**

## Verification

- [Newest same-source four-platform native build and installed desktop QA](https://github.com/MasynNay/anything-plays/actions/runs/43140637755) passed all 13 jobs, with four complete 11-core, 18-console installers and installed Tk, Stream Mode and settings-isolation verification. All four were built from the same application revision `104b96621ec4cb8dc39fde8c3fe96fc854c406ed`.
- Each platform uses its own original-source-built OpenCV 4.14.0.94 camera-only wheel, with FFmpeg disabled and the applicable native camera backend retained; see the [exact source, build recipes, checksums and limitations](V3_1_CLEAN_OPENCV_SOURCE_REPRODUCTION.md).
- The [new private staged four-installer package](https://github.com/MasynNay/anything-plays/actions/runs/43142249044) rechecked SHA256, original source SHA, all four compiled wheel hashes and native installed GUI receipts. This candidate is **not** yet uploaded to the existing v3.1.0 GitHub Release draft. That older draft still contains stock-OpenCV binaries and must not be published as the new candidate.
- Project owner confirmed that RC2 installed and launched on Linux and Stream Mode's two-screen presentation worked visually. **That was RC2, not a claim of real-world final-installer acceptance on every platform.**

## Known limitations and review before public publication

- **Native dependency redistribution review remains open.** The new four-platform full installer candidate is built with SHA-pinned, FFmpeg-disabled native camera-only OpenCV wheels, unlike the older stock-OpenCV draft and the public stable 3.0 packages. Source reproduction is documented, but this does **not** resolve pygame-ce/SDL, transitive native library, source availability, required notices, user replacement/relinking or other redistribution conditions. Consult the [native distribution review](V3_1_NATIVE_DISTRIBUTION_REVIEW.md) and the [clean OpenCV source record](V3_1_CLEAN_OPENCV_SOURCE_REPRODUCTION.md).
- Automated installed-GUI tests cannot certify actual controller hardware, live camera tracking, retail-game compatibility, audio, saving or extended real-world sessions. These requirements remain outstanding.
- The macOS applications are ad-hoc signed and are **not Apple-notarized**. Windows packages are not necessarily publisher-signed.
- The project's own source is MIT-licensed; included emulator cores, pygame-ce, SDL and transitive native dependencies retain their respective licenses. The exact proposed application source is available at the source revision in Verification above, with all eleven original emulator sources and notices in [v3.0.0-sources](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources). The pygame/SDL upstream source candidates and technical replacement tests are documented in [the source companion](https://github.com/MasynNay/anything-plays/blob/main/docs/V3_1_SOURCE_COMPANION.md). **Complete native corresponding-source, replacement/relinking and redistribution review has not been finished.** This draft does not constitute legal approval.
- Before pressing Publish, complete the outstanding release acceptance checks and independently inspect the compiled-binary and source-notice evidence. Until then, the existing public [RC2](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc2) remains the available 3.1 prerelease and [3.0.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0) remains stable.

Before publication, follow the [exact release runbook](V3_1_PUBLICATION_RUNBOOK.md), replace the **older** private draft with the newly verified four clean-source installers and matching receipts only after the remaining [native distribution review](V3_1_NATIVE_DISTRIBUTION_REVIEW.md) and physical acceptance are actually cleared. Verify all seven corresponding assets after any replacement.

**Status: Four source-verified new installers exist in private staging; the existing owner-only draft still contains older binaries. Stable 3.1.0 is not publicly published or approved for redistribution. Do not substitute checksum verification for licensing and real-device acceptance.**
