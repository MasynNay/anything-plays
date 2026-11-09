# Anything Plays 3.0 — repository and release organization

## Public-facing downloads

**The main 3.0 application release must stay readable.** It may expose
exactly four platform installers, plus `SHA256SUMS.txt`:

1. Windows x64 installer
2. macOS Apple Silicon DMG
3. macOS Intel DMG
4. Debian/Ubuntu x64 package
5. Plain-text SHA-256 checksums

Source attribution, required redistribution notices, license texts and
build provenance belong **inside each application package and in clearly
linked project documentation**. If a full source ZIP is legally required,
publish that in a separately labeled source archive release and link it
prominently from the main release. Never hide or omit a source obligation.

**Separate emulator-pack catalog:** one clearly named GitHub prerelease
per approved 3.0 emulator generation; tag pattern
`v3.0.0-cores` (or `v3.0.0-alpha.2-cores` during testing).
Core assets have stable names `AnythingPlays3-Core-<name>-<target>.zip`.
The app discovers only valid, checksum-bearing GitHub assets from this
catalog; it does not download from external emulator sites or depend on
RetroArch, Dolphin or their standalone installers.

Do not present a candidate ZIP as downloadable merely because GitHub Actions
produced it. Every binary needs a licensed/source-reviewed, runtime-tested
and approved manifest. GameCube remains blocked until a paired Dolphin + Sys
package format and real 3D video/audio QA are completed.

## What stays in the GitHub root

Keep only standard repository information, the application entry point,
shared public build/check APIs, dependency manifests and obvious directories.
Platform-specific build implementation and installer definitions live in
`packaging/`. CI, developer diagnostics, game fixtures and license reviews
remain in their own folders.

GitHub Actions requires workflow files within `.github/workflows/`.
Organize them with distinct names for app builders, optional emulator QA and
experimental GameCube research; avoid spawning unrelated draft releases for
every commit. The legacy v2 workflows remain preserved on the original
branches for release traceability.

## Publish checklist

A release is blocked unless **all** console and platform evidence is
complete: embedded rendering, real-game behavior, native PCM, user-device
audio QA, keyboard/camera controls, saves, unload/restart stability,
source and license audit, clean installation, macOS signing/notarization
as applicable, and verified download hashes.

The 3.0 preview is **not** a release authorization.

## Enforced clean-assets staging

When 3.0 is actually approved, collect the four signed/validated production
installers in a separate input directory and run:

```bash
python tools/stage_v30_release_assets.py \
  --version 3.0.0 --input release/candidates \
  --output release/public-3.0.0
```

This produces **exactly four installers and SHA256SUMS.txt**. It refuses
missing, empty, symlinked, stale 2.0 or unexpected extra installer files;
it deliberately excludes all emulator-pack ZIPs, diagnostics and unrelated
technical assets. The script **does not publish or authorize** a release.
The required source/license information is documented and linked separately.
