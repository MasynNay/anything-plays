# Dolphin 3.0: exact nested Gitlink source capture

**Status: source-candidate preservation only. No license, source-to-binary, complete build or public installer approval.**

The original Dolphin Libretro source revision used for the 3.0 development
preview is `32c61f9d0e933331bb7087ba57e96883241b4960`. Its Git tree
contains **34 direct Gitlinks**. The [six-shard source capture
run 42446758270](https://github.com/MasynNay/anything-plays/actions/runs/42446758270)
saved and hashed original immutable archives for every one of those 34
submodules. [Run 42447184893](https://github.com/MasynNay/anything-plays/actions/runs/42447184893)
independently rehashed all 34 and produced the `UNAPPROVED` reviewer index.

The source-capture metadata explicitly identified `.gitmodules` in only
**two** of the 34 original source archives: `Externals/cubeb/cubeb` and
`Externals/libadrenotools`. Direct inspection of those repositories' exact
pinned upstream Git trees and `.gitmodules` revealed precisely **three more
Gitlink dependencies**, not merely potential directory references:

| Dolphin parent source | Its nested Gitlink | Exact source revision |
| --- | --- | --- |
| `Externals/cubeb/cubeb` | `cmake/sanitizers-cmake` | `aab6948fa863bc1cbe5d0850bc46b9ef02ed4c1a` |
| `Externals/cubeb/cubeb` | `googletest` | `40412d85124f7c6f3d88454583c4633e5e10fc8c` |
| `Externals/libadrenotools` | `lib/linkernsbypass` | `aa3975893d83ef1bc84c321ec60c65fbf1287887` |

The parent source revisions were independently tied to the previous
34-source archive audit: Cubeb `54217bca3f3e0cd53c073690a23dd25d83557909`
(original source archive SHA-256
`a795511bf56183ff7bad8fb2d2836ca5bb158e12ddd519caced62946ffa69c83`),
and libadrenotools `8fae8ce254dfc1344527e05301e43f37dea2df80`
(original archive SHA-256
`ceffce971676d4cfdf348a082df06fc92a1dca6d95bea892a480d63f200961cb`).

All three child Git trees were independently queried at their **full pinned
Git revisions**. None contained another `type=commit, mode=160000` Gitlink
at that revision. This establishes the Git-submodule graph closure **under
those two selected parent submodules**, not the completeness of every
nested library, dependency installed by a build script or source input for
Dolphin itself.

## Reproducible verification and archival

- Immutable configuration: `config/v3.0-dolphin-nested-submodule-candidates.json`.
  It fixes both parent identities, original source archive hashes, all three
  child source repositories and exact child commits, with all redistribution
  and binary/source approval flags **false**.
- Source tool: `tools/capture_v30_dolphin_nested_sources.py`.
  It first validates the original independent 34-source audit JSON, verifies
  actual parent source trees and `.gitmodules` URL/path/revision contents
  against the pinned index, and requires all three child trees to have
  no further Gitlinks.
- For each verified child, capture only the immutable GitHub codeload
  source TAR at its full 40-digit commit, with bounded size, SHA-256/byte
  length, and a manifest of candidate *top-level* license/notice filenames
  and their content digests. Listing a notice does **not** mean that it
  describes every transitive component or licenses the shipped program.
- Dedicated workflow `.github/workflows/v30-dolphin-nested-sources.yml`:
  downloads only the original **34-source reviewer JSON** from successful
  run `42447184893`, independently validates its checksum, runs strict
  upstream nested verification and three source snapshots, then uploads
  exactly **three original source TARs, one UNAPPROVED JSON and
  SHA256SUMS.txt**. No emulator binaries, games, BIOS or installers.
- Source regression suite: `tests/test_v30_dolphin_nested_sources.py`,
  including forged links, changed original parent archives, unexpected
  deeper Gitlinks, source ZIP checksums, and false release claims.

After the new run, record its exact workflow URL/artifact digests in
`CONTINUE_HERE.md`. Only mark a source *candidate* archived once the
actual files passed GitHub Actions and their SHA-256 was reviewed. The
checked-in source graph is reviewable offline; live upstream checks may
fail if public source repos change availability, without waiving any gate.

## Distribution and license decisions this does not settle

Preserving **34 direct plus 3 nested** candidate sources is a material step
toward complete source inventory. However it is **not** proof those exact
revisions were used to build the distributed Dolphin binary, nor that the
34 direct Gitlink source trees include every conditional, external or
generated build input. Some nested sources may only be used for tests or
platforms absent from the packaged core. The original Dolphin parent
source, its Sys archive, buildbot provenance, compiler flags, patches,
transitive runtime assets, complete notices and actual combined GPL/
noncommercial in-process redistribution must still be independently
reviewed. Unapproved archives should never be attached to a public
binary release as though they were complete corresponding sources.

The production gates in `tools/check_v30_source_gate.py`,
`tools/check_v30_release.py`, and `config/v3.0-core-lock.json`
remain fail-closed. Stable public 3.0 must not be published on the
strength of this research alone.

## Actual independent three-source capture result — verified

[PR #69](https://github.com/MasynNay/anything-plays/pull/69)
**merged** after [source regression run 42452594655](https://github.com/MasynNay/anything-plays/actions/runs/42452594655)
and [real nested source capture run 42452594761](https://github.com/MasynNay/anything-plays/actions/runs/42452594761)
both completed **SUCCESS** on the exact reviewed PR head
`09e4a4dc4297967824c67b034c0cc7904aef8531`.
The source CI ran Python 3.12/3.13 and native mGBA compatibility
successfully; source-only build changes correctly skipped three
unaffected package jobs.

The actual test-only GitHub Actions archive
`AnythingPlays-3.0.0-DOLPHIN-THREE-NESTED-SOURCES-UNAPPROVED`
(artifact ID `13606560568`) was **downloaded and independently
rehash-verified**. It contains exactly **five** files: the three original
immutable source TAR.GZ files, one reviewer JSON and SHA256SUMS.txt.
All four checksum entries (three TARs and reviewer JSON) match actual
downloaded bytes.

| Exact additional source snapshot | Actual TAR bytes | Actual TAR SHA-256 |
| --- | ---: | --- |
| `cmake/sanitizers-cmake` at `aab6948...` | 7,234 | `9f5b073625375322236a94ce8d2d803cdedad321c91e63845f487b9ebfb2c433` |
| `googletest` at `40412d8...` | 868,503 | `ff9fb47ea9e2cb4dc0f30956a2f3b5e42dde67b06f33241d22ac255e5981eda0` |
| `lib/linkernsbypass` at `aa39758...` | 5,656 | `da1128c8aa771c4d24766b53a47822d0717baa5c536ca8491220402942b80638` |

All three source archives contained a candidate root `LICENSE`
file; the archived JSON records their exact contents' SHA-256,
but this is **not** a license compatibility determination or proof those
dependencies are compiled into the distributed Dolphin Libretro core.

**Result:** pinned Git-submodule source candidates captured and
verified: **34 direct + 3 nested = 37**. No deeper Gitlinks at
these immutable child revisions. The original binary/source
correspondence, runtime-specific build graph, additional external
build tool dependencies, Dolphin Sys rights and mixed GPL/noncommercial
permission remain independently unapproved. Do not promote this source
audit to `corresponding_source_inventory_verified=true` or publish stable
v3.0 on its strength.
