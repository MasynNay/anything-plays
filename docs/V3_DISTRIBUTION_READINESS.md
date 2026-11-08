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

## Independently verified four-platform PCE source-built candidate fingerprints

After the [successful four-platform original homebrew video/audio run
42444367068](https://github.com/MasynNay/anything-plays/actions/runs/42444367068),
the four original GitHub Actions archives were downloaded and their **native
binary SHA-256, byte sizes, exact pinned source tarball SHA-256, and native
audio/video test reports** rechecked. The resulting compact manifest is
[config/v3.0-pce-source-built-candidates.json](../config/v3.0-pce-source-built-candidates.json).
It gives each target an immutable native SHA and archived source SHA without
committing any third-party emulator libraries, game ROMs, or large source
tarballs to Git. The newly compiled pinned-source PCE cores passed original
HuCard playback on each target (more than a million nonzero PCM values and
hundreds of video frames each).

The Windows source tarball has a different exact byte digest than Linux and
the two Macs because its source checkout uses Windows line endings. Those
differences are recorded **per platform**, not hidden by assigning a
nonmatching universal hash. All four builds check out the exact same Git
commit; platform-specific archive hashes are evidence of the actual captured
bytes, not proof of a cross-platform reproducible binary build.

**This is a candidate for replacing the UNVERSIONED OLD PCE buildbot binary,**
not an automatic swap or approval for the old core. The working 3.0 preview,
reviewed stable production lock, and user ROM library are unchanged. All
third-party distribution permissions and mixed GPL/noncommercial compliance
flags remain false.

## Source-built Beetle PCE Fast — separate experimental candidate

The original 3.0 developer-preview Beetle PCE Fast buildbot binary identifies
itself as `v1.31.0.0` but does **not** expose an upstream Git source revision.
The source snapshots therefore correctly mark its binary/source correspondence
as **unresolved**.

To eliminate the unknown-build-source problem *without guessing* about the
existing binary, a separate four-platform lab now checks out the official
[Beetle PCE Fast Libretro upstream repository](https://github.com/libretro/beetle-pce-fast-libretro)
at immutable commit
`2de1ce1c3f237b161c126c54ba407990bb86d1e9`, compiles a **new**
native Libretro candidate from that exact source, archives the source and
GPL-2.0 text alongside the compiled core, hashes both files and runs an
**original, generated PC Engine HuCard** through the real native application
frontend. The homebrew test checks actual changing native video and
nonzero HuC6280 PSG audio. No copyrighted game ROM or CD BIOS is needed.

Workflow: `.github/workflows/v30-pce-pinned-source.yml`
(`Anything Plays 3.0 | PCE pinned-source replacement research`).
The evidence script is `tools/capture_v30_pce_source_build.py`;
it rejects an unexpected Git commit, modified tracked source, mismatched
repository URL, missing GPL notice or incorrectly named native binary.
Each workflow artifact contains the new `mednafen_pce_fast_libretro` binary,
matching full pinned-source tarball, GPL notice and real playback evidence.

**Important scope limitation:** This workflow tests a *replacement candidate*,
not the native PCE binary inside the current successful 3.0 installers. It
does not establish that the current buildbot binary corresponds to this commit;
does not change or approve `config/v3.0-core-lock.json`; does not establish
that a combined distribution of GPL/noncommercial cores is compatible; and
does not certify real-device retail-game compatibility. A failed platform
build or native audio/video gate must remain failed. Only a separately reviewed
replacement could be integrated after all four platform jobs pass.

## Four-platform immutable candidate lock, not a license clearance

The successful [full offline CI run 42437133733](https://github.com/MasynNay/anything-plays/actions/runs/42437133733)
retained **48 original native inputs**: 11 platform-specific core ZIPs and the
upstream Dolphin system ZIP on each of Windows x64, Linux x64, Mac Intel and
Mac Apple Silicon. Those archives were independently hashed against each
`PRESERVED_NATIVE_INPUTS.json` record; all matched.

`tools/create_v30_candidate_lock.py` checks the original outer CI archive,
each nested ZIP and each extracted native library, and requires exactly the
18-profile / 11-core lineup. It emits a four-platform **unapproved**
fingerprint manifest containing native and original-ZIP SHA-256, byte sizes,
reported versions, upstream source repositories and Dolphin Sys hashes.

To repeat the process without manually reconstructing the manifest, dispatch
the GitHub workflow `Anything Plays 3.0 | Freeze original native candidate
inputs`, provide the successful offline lab run ID, and retrieve the
`NATIVE-LOCK-UNAPPROVED` artifact. This workflow does **not** publish
installers, grant redistribution rights, resolve noncommercial/GPL linking
compatibility, or claim independently reproducible native binaries. Missing
source attribution (notably Beetle PCE Fast) still requires investigation.

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

## Dolphin submodules pinned to their exact parent commit

The first ten [upstream source snapshots](https://github.com/MasynNay/anything-plays/actions/runs/42441448884)
correctly preserved the parent source trees but did **not** include Git
submodule content. In particular, the Dolphin Libretro source at commit
`32c61f9d0e933331bb7087ba57e96883241b4960` contains **34 Gitlinks** to
pinned third-party commits, not 33 and not a complete vendored source tree.

A new [unapproved Gitlink index](../config/v3.0-dolphin-submodule-candidates.json)
records all 34 exact Git commit hashes and source URLs as extracted from that
commit's own Git tree and `.gitmodules`. One external dependency is hosted
on GitLab; the rest use GitHub. The companion
[offline and optional live verifier](../tools/check_v30_dolphin_submodules.py)
ensures the index cannot silently omit or change a dependency:

```bash
python -m tools.check_v30_dolphin_submodules
python -m tools.check_v30_dolphin_submodules --verify-upstream
```

**Source archive candidate capture now executed:** [PR #57](https://github.com/MasynNay/anything-plays/pull/57)
added the isolated `.github/workflows/v30-dolphin-submodule-sources.yml`
workflow. Its [six-shard run 42446758270](https://github.com/MasynNay/anything-plays/actions/runs/42446758270)
passed all six jobs and retained six `DOLPHIN-SOURCE-UNAPPROVED` Actions
artifacts covering the **34 original pinned Gitlinks**. Each GitHub or GitLab
immutable-revision archive is bounded, validated as an unextracted tarball,
rehash-checked against the saved SHA-256 and recorded in a shard manifest.
[Seven accompanying source/package CI jobs](https://github.com/MasynNay/anything-plays/actions/runs/42446758291)
passed on PR #57 before merge at `eec9170eb0106ee7c5d5d99d1cc372be3986c769`.
These are time-limited research artifacts, not source offers attached to a
public production release.

**What this establishes:** pinned and archived upstream Dolphin dependency
source **candidates** with checksums, not a binary/source equivalence proof.
**What remains unresolved:** nested submodules and external build
dependencies, which components were actually compiled into the original
Dolphin Libretro binary and on which build flags, licenses/notices and
redistribution of the combined program and Dolphin Sys. Every source-to-
shipped-binary and public distribution approval flag remains **false**.

**Independent 34-archive reconciliation complete:** [PR #58](https://github.com/MasynNay/anything-plays/pull/58)
merged after its [seven-job source/packaging CI](https://github.com/MasynNay/anything-plays/actions/runs/42447184884)
and the [real original-artifact reconciliation run 42447184893](https://github.com/MasynNay/anything-plays/actions/runs/42447184893)
both passed. `tools/reconcile_v30_dolphin_source_archives.py` downloaded
all six original unapproved source artifacts, independently rehashed and checked
the 34 original source TARs against original shard manifests, checksum lists,
original pinned Gitlink commits and repository URLs. It retained a single
`AnythingPlays-3.0.0-DOLPHIN-34-SOURCE-REVIEW-UNAPPROVED` review artifact
containing **only a 34-source JSON and SHA256SUMS.txt**, not binaries or ROMs.
This audit makes the precise upstream dependencies easy to inspect without
placing any native payloads into the Git repository or GitHub Releases.
The remaining source-to-shipped-binary, transitive source, license compatibility,
Dolphin Sys and final hardware acceptance requirements remain unchanged.

## Reported upstream source capture (new evidence path)

The 3.0 [preview integrity manifest](../config/v3.0-preview-candidate-integrity.json)
contains eleven core identities. Ten report short Git revisions that have been
resolved to complete upstream commits; **Beetle PCE Fast does not report a
revision**. The new source-only CI workflow
`Anything Plays 3.0 | Preserve reported upstream sources` archives the ten
reported commit tarballs from GitHub and records SHA-256, size and submodule
presence. Its output is an Actions artifact marked `UNAPPROVED`, not a
public GitHub release. Run `python tools/capture_v30_source_snapshots.py
--output source-snapshots` to repeat it in a trusted checkout. The exact
published native binaries, build flags, transitive source and rights remain
unverified. Never interpret archived upstream source alone as compliance.

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
