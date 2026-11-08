# Anything Plays 3.0 — distribution and release evidence

**Status: NOT APPROVED FOR PUBLIC BINARY DISTRIBUTION.**
**Reviewed:** November 7, 2026.
**Code baseline:** `feature/v3.0-unified-test`, including merged control-label sizing and Linux Dolphin fixes.

This is the 3.0-specific audit trail. The earlier [v2.0 distribution decision](RELEASE_DISTRIBUTION_REVIEW.md) applies **only** to the exact approved 2.0 binaries and does not approve any changed 3.0 native libraries.

## What has been demonstrated

- Four-platform complete offline developer installer CI passed: [run 42426209611](https://github.com/MasynNay/anything-plays/actions/runs/42426209611), commit `43cc14b572b039b0d0074fa4726ed4d65ffd764b`.
- Full test packaging includes **18 console profiles, 11 native cores and bundled Dolphin Sys files**. It does not require downloading RetroArch or Dolphin to try the full test build.
- That run included Linux unprivileged installed-app startup, read-only GameCube homebrew playback and source/UI regression checks. These are automated tests, not blanket real-game compatibility or independent GPL compliance certifications.
- The maintainer separately reports Dolphin/GameCube now works on a physical Linux system. The precise tested installer SHA, 30-minute endurance and full control/save matrix remain unrecorded.
- The camera-side label-size slider, persistent size preference and zone-constrained rendering are merged. Their source checks and the complete offline installer lab passed.

## Native core redistribution review matrix

| Core packaged in the complete preview | Upstream source | Public binary approval |
| --- | --- | --- |
| mGBA | [libretro/mgba](https://github.com/libretro/mgba) | 3.0 binary/source/notice matching pending; old 2.0 approval does not transfer |
| Snes9x | [libretro/snes9x](https://github.com/libretro/snes9x) | Custom noncommercial license and separately LGPL-licensed filter require **3.0-specific** review |
| FCEUmm | [libretro/libretro-fceumm](https://github.com/libretro/libretro-fceumm) | Source, full terms, notices, binary hash and compatibility review pending |
| Genesis Plus GX | [libretro/Genesis-Plus-GX](https://github.com/libretro/Genesis-Plus-GX) | Source, full terms, notices, binary hash and compatibility review pending |
| ParaLLEl-N64 | [libretro/parallel-n64](https://github.com/libretro/parallel-n64) | Source, full terms, notices, binary hash and compatibility review pending |
| Dolphin Libretro | [libretro/dolphin](https://github.com/libretro/dolphin) | GPL obligations, linked dependencies, Sys assets, source, notices, binary hash and GPU QA pending |
| Stella 2014 | [libretro/stella2014-libretro](https://github.com/libretro/stella2014-libretro) | Source, full terms, notices, binary hash and compatibility review pending |
| ProSystem | [libretro/prosystem-libretro](https://github.com/libretro/prosystem-libretro) | Source, full terms, notices, binary hash and compatibility review pending |
| Beetle PCE Fast | [libretro/beetle-pce-fast-libretro](https://github.com/libretro/beetle-pce-fast-libretro) | Source, full terms, notices, binary hash and compatibility review pending |
| Beetle NeoPop | [libretro/beetle-ngp-libretro](https://github.com/libretro/beetle-ngp-libretro) | Source, full terms, notices, binary hash and mono audio coverage pending |
| Beetle WonderSwan | [libretro/beetle-wswan-libretro](https://github.com/libretro/beetle-wswan-libretro) | Source, full terms, notices, binary hash and compatibility review pending |

The list is derived from `fetch_mgba_core.py` and the full-bundle packaging workflow, not a fresh independent inspection of each binary's full dependency tree. **Listing an upstream repository does not satisfy license terms or establish its binary's source correspondence.**

At the time of review, repository `licenses/` included the full 2.0 core texts, a Dolphin GPL file, FCEUmm GPL text, Genesis Plus GX license text and glcontext MIT text. Standalone, verified bundled license/source inventories are **not yet demonstrated for all eleven 3.0 cores and transitive components**. Some licenses can impose additional source-availability, linking, relinking or use restrictions, and compatibility of combined distribution must be reviewed rather than assumed.

## License compatibility question

The exact 3.0 package includes both GPL-family native cores and
noncommercial Snes9x / Genesis Plus GX cores. Their use via an in-process
Libretro plugin interface may raise a *combined-work versus aggregation*
question that checksum and notice checks cannot answer. See the dedicated
[GPL / noncommercial compatibility assessment](V3_LICENSE_COMPATIBILITY_GATE.md).
A legally reviewed permissible distribution architecture or relevant
rights-holder authorization is a prerequisite; CI cannot infer it.

## Publication blockers and required evidence

1. **Freeze exact bytes.** Current full-preview build runs with `AP_RELEASE_BUILD=0` and `AP_V30_TEST_CORES=1`. The acquisition path can fetch Libretro `latest` cores. Preserve each archive, its SHA-256, target architecture, reported revision and exact final packaged native binary hash. The old approved v2.0 lock does not cover the additional 3.0 cores.
2. **Prove source/permissions.** Obtain corresponding source and required notices for **every** redistributed core, bundled Dolphin Sys asset and relevant Python/native dependency. Resolve Snes9x noncommercial scope, GPL/LGPL/MPL obligations and any compatibility questions for distributing the combined application. Do not treat a license filename as complete permission evidence.
3. **Check real packaged inputs.** Use immutable build inputs and verify each installed archive/hash before publication, including after macOS app packaging.
4. **Complete native acceptance.** Record per-platform installer and per-console video, audible output, keyboard/camera input, saves, repeated loading and long-session shutdown. Document unavailable physical Intel macOS testing rather than claiming it.
5. **Verify installer notices and provenance.** Scan extracted DEB, DMG and EXE installer contents for source/license notices, no commercial ROMs/BIOS, appropriate source access links and no unintended codecs. Publish platform signing/notarization limitations clearly.
6. **Re-run final packaging on the approved commit.** Check exactly four full installers and one checksum document using `tools/stage_v30_release_assets.py`; retain third-party source archives as linked, clearly identified source artifacts.
7. **Approve manually.** Update `config/v3.0-release-acceptance.json` only where evidence is recorded. Only publish if `python tools/check_v30_release.py` passes *without* `--report-only`. Neither a successful preview build nor owner consent to ship overrides missing legal or technical evidence.

### Exact work remaining

- [x] Merge camera label-size controls and test zone fitting.
- [x] Pass the full four-platform developer installer lab on updated 3.0 code.
- [x] Confirm physical Linux Dolphin/GameCube starts in the maintainer's test installation.
- [ ] Complete eleven-core native binary/source/redistribution notices and rights matrix.
- [ ] Capture immutable 3.0 multi-platform native core archives and hashes.
- [ ] Complete actual installer acceptance across platforms and all supported consoles.
- [ ] Approve the 3.0 acceptance record with supporting evidence.
- [ ] Produce immutable, verified public artifacts, update stable README/site, then publish 3.0.

**No roadmap announcement before public 3.0 release.** This document concerns launch readiness only.

**This document is an engineering evidence inventory, not legal advice or a rights-holder authorization.**
