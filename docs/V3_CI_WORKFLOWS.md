# Anything Plays 3.0 — CI workflow map

The Actions page groups production builds, system verification, focused
console acceptance and experimental rendering separately. All changes are on
the 3.0 branch; public 2.0 and main remain unchanged.

* **Application builds** (`v30-app.yml`): source/GUI regressions and
  Windows, macOS Intel, Apple Silicon and Linux *starter* preview packages.
  A successful preview is **not** a verified full offline 3.0 installer.
* **Emulator verification** (`v30-cores.yml`): other consoles' native
  audio/video, in-app updates/install/rollback, N64 experiments and optional
  emulator candidate archives. The eight Neo Geo Pocket jobs were removed
  to avoid repeatedly cancelling their results amid the 80+ job matrix.
* **Neo Geo Pocket native acceptance** (`v30-ngp.yml`): dedicated eight
  blocking NGP/NGPC video/audio/manual/camera tests; focused unit contracts;
  a **required** native saved-state recovery across two cold emulator
  processes, plus a separately labelled exploratory original cartridge
  `.flash` save/restore experiment. Examine **job-level** results: the
  cold `.flash` experiment is allowed to fail to preserve diagnostic
  evidence, not to claim the feature works.
* **Experimental emulator lab** (`v30-lab.yml`): GameCube renderer,
  hardware negotiation and Genesis investigations. Some individual diagnostic
  jobs deliberately tolerate failures, so a green aggregate isn't playback
  certification.
* **Sustained endurance lab** (`v30-endurance.yml`): native and GUI soaks.
* **Full offline bundle lab** (`v30-full-bundle.yml`): four-platform complete
  11-core installer layout, paired with verified Dolphin Sys; these builds
  remain unpublished pending the full release gates.

### Pinned Neo Geo Pocket evidence

`42388394525`: **4/4 NGPC** actual MIT homebrew original screen frames,
PCM, manual A and camera B accepted. **0/4 monochrome NGP audio**: its
pinned MIT alignment calibration ROM produces a silent PCM stream, despite
native changing LCD frames and both working input paths. Obtain a legal
NGP *sound-producing* original test; never relax the nonzero PCM gate.

The original NGPC cartridge-flash experiment wrote a 272-byte `.flash`
file and preserved it across cold processes, but **did not reload the
modified in-game number**. The release gate is still blocked on native flash
restore. It must not be masked by the separate recovery-state system.

`42389452506`: the **two-process native saved-state fallback** passed with
pinned StarGunner, identical recovered actual in-game screen pixels,
and no `.flash` file in either session. New save-state files validate ROM
and native core SHA256, length and contents, and commit atomically in the
user-writable data directory. Physical hardware and retail-game behavior
still require independent testing.

The full public release remains blocked by
`config/v3.0-release-acceptance.json` and
`tools/check_v30_release.py`. Neither preview builds nor experimental
diagnostics may override those gates.
