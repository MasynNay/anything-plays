# Anything Plays 3.1.1 — Reliability maintenance update

Anything Plays 3.1.1 improves reliability while keeping the same 18 offline console profiles, 11 original-source emulator core families, local ROM libraries, controller support, Stream Mode and appearance themes.

## What changed

- **Camera recovery:** Isolate failing camera devices, release camera-held controls when a capture source disappears and clean up preview timers after errors.
- **Controller resilience:** Handle a failing gamepad without blocking other devices; release held inputs and safely recover SDL resources on reconnect and partial initialization failures.
- **Safer save files:** Use unique temporary save files, flush data before atomic replacement and retry bounded Windows file-sharing conflicts.
- **ROM and cover-art stability:** Inaccessible or broken entries no longer prevent healthy games from showing in the library.
- **Long-session tests:** Expanded synthetic input/save endurance, four-platform driver error tests and real Linux Tk/OpenCV/SDL soak checks.

## Downloads

| Platform | Installer |
| --- | --- |
| Windows 64-bit | `AnythingPlaysSetup-3.1.1.exe` |
| Ubuntu/Debian Linux 64-bit | `anything-plays-31_3.1.1_amd64.deb` |
| Apple Silicon Mac | `AnythingPlays-3.1.1-macos-arm64.dmg` |
| Intel Mac | `AnythingPlays-3.1.1-macos-x64.dmg` |

The release includes `SHA256SUMS.txt`, a four-platform QA manifest, source access disclosures, and the original pygame/SDL/mpg123 upstream source companion (byte-identical to the original 3.1.0 source archive).

## Updating from 3.1.0

Version 3.1.1 uses the existing stable 3.1 installed application identity and preserves its settings namespace. Install the correct update for your operating system. Back up any important game save files before an operating-system upgrade or installer change. The stable [3.1.0 release](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0) remains available for rollback.

The Windows installer retains the existing stable Inno AppId, the Debian installer upgrades `anything-plays-31`, and the macOS update uses `AnythingPlays31.app` with the established `com.anythingplays.release31` bundle identifier.

## Verified QA and known limitations

All four complete 3.1.1 installers were assembled on native Windows, Ubuntu Linux, Apple Silicon Mac and Intel Mac runners from the **same pinned application source**. Their eleven original-source core families and inherited SHA-pinned runtime materials were checked, and the actual frozen Tk desktop/Stream Mode startup passed on all four hosts. Automatic camera, controller, library and save regressions also passed.

**Physical-device coverage is limited.** Real USB/Bluetooth controller pairing, actual webcam object capture, retail ROM audio/save compatibility and multi-hour physical gameplay were not independently certified for every published installer. These synthetic and native startup tests do not guarantee compatibility with every camera, GPU, controller or game. The macOS DMGs are ad-hoc signed, not Apple notarized; Windows may warn about an unsigned installer.

## Free use and third-party source

The original app source uses MIT licensing; third-party emulators, artwork, SDL, pygame-ce, mpg123, OpenCV and other libraries retain their separate licenses. This full bundle is released for **free, noncommercial, nonpromotional** use and does not grant separate commercial redistribution rights. The release includes original third-party upstream source and license materials, rebuilding/replacement documentation and an accurate technical review manifest. This does not warrant byte-for-byte reproducible builds of every transitive native library or separately establish legal compliance for every potential redistribution scenario.

Source and bug reports: https://github.com/MasynNay/anything-plays

Download information: https://anythingplays.masynnay.com/
