# Release candidate QA checklist · v2.0.0

This checklist is for **hands-on verification after installing a new build**.
Tests in `tests/` cannot validate a physical camera, real game audio, native
installer permissions, or every Libretro platform combination.

## 1. Every operating system

- [ ] Windows 11 x64 installer launches on a clean machine.
- [ ] macOS Apple Silicon DMG opens from Finder and launches on first attempt.
- [ ] macOS Intel DMG opens from Finder and launches on first attempt.
- [ ] Ubuntu 24.04 x64 DEB installs, launches from the app menu and runs offline.
- [ ] A freshly installed app finds all three bundled cores without manual setup.
- [ ] The installed `CORE_PROVENANCE.json` matches the bundled binaries.
- [ ] Window resizing, both independently scrolling panes, and all 16 themes
  work without clipping controls.
- [ ] Unsigned Windows and macOS security prompts are documented accurately.

## 2. Every console

For GB, GBC, GBA and SNES, use a legal test ROM or a homebrew game:

- [ ] Correct ROM extension filtering and console-specific cartridge art.
- [ ] ROM launches and renders without a blank/black game screen.
- [ ] Audio is audible and does not crackle, stutter or lag during normal play.
- [ ] Keyboard input works even when camera object controls are paused.
- [ ] Supported buttons function, including SNES X/Y/L/R.
- [ ] SRAM `.sav` persists when unloading and reopening a game.
- [ ] ROM folder and profile are retained when switching away and back.
- [ ] No system-wide keyboard events leak into other applications.

## 3. Camera input

- [ ] Webcam discovery does not hang the interface and reports useful device
  names where the operating system provides them.
- [ ] Camera permission denial and camera disconnection do not crash the app.
- [ ] Picking a target color works from both live video and a reference image.
- [ ] Mirror, tolerance, minimum area, cooldown, and hold length behave as
  expected for a stationary and a moving target.
- [ ] Disabled buttons do not activate; re-enabling retains their old zones.
- [ ] Fit buttons to grid produces equal-size zones for each console.
- [ ] Shuffle triggers once on entry rather than on every frame inside a zone.
- [ ] Manual drawing, overlay styles, transparency and PNG art render correctly.
- [ ] Escape and Stop disable object controls immediately without closing the game.

## 4. Persistence and upgrade

- [ ] Back up v1.5 preferences before upgrading.
- [ ] Existing `~/.config/fish-plays-pokemon-studio/preferences.json` loads.
- [ ] Existing valid custom rectangles, mappings, selected theme and ROM folders
  survive migration without silently resetting.
- [ ] Invalid or missing profile fields recover without a startup crash.
- [ ] App closes without lingering camera access, audio processes or core workers.

## 5. Publication gate

- [ ] Automated tests and Linux headless UI smoke test pass in CI.
- [ ] Generated installers are independently checked with SHA-256 checksums.
- [ ] Third-party core/license/source requirements in
  `THIRD_PARTY_COMPONENTS.md` are satisfied for each packaged artifact.
- [ ] README and release notes describe actual artifact names and limitations.
- [ ] Merge and release tag approved by the repository owner.

**Do not treat a green CI run alone as approval to publish.**
