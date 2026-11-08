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

### Corrected NGP cartridge-header acceptance (November 8, 2026)

**Important source-fixture correction:** the previously pinned MIT file
`hw_calibration/a_align_calib_v12.ngp` has actual header byte
`0x23 = 0x10` (**color-compatible**), despite its `.ngp` extension.
An independent review of **all fourteen** sibling `.ngp` calibration
blobs at the pinned `Tixul/Ngpcraft_emulator` Git commit showed
**14/14 color-mode headers, 0/14 genuine mono-mode `0x00`**.
The [real native 14-ROM test](https://github.com/MasynNay/anything-plays/actions/runs/42448817220)
recorded **0/14 nonzero PCM**. The separate original-generated true
mono 0x00 PSG test also recorded **0/4 nonzero PCM and 0/4 changing
video** in [run 42449197364](https://github.com/MasynNay/anything-plays/actions/runs/42449197364).
This is not sufficient to conclude a genuine native audio defect.

`tools/ngp_mit_fixtures.py` now checks immutable Git blob + the real
cartridge header, and the main `tools/probe_ngp_mit_homebrew.py` parent
**rejects even a native-positive report for a color-header `.ngp`**
when testing the real mono target. The fourteen-ROM research workflow
remains diagnostic only and **explicitly reports zero genuine mono
candidates**. The genuine mono blocker in issue #41 remains OPEN;
NGPC color acceptance continues separately and is not demoted.
