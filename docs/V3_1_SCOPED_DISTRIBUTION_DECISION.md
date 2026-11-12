# Anything Plays 3.1.0 — Free/noncommercial binary release decision

**Decision date:** November 11, 2026 (America/Denver).  
**Release scope:** Public downloadable **free, noncommercial, nonpromotional** `v3.1.0` application packages for Windows x64, Debian/Ubuntu x64, Apple Silicon macOS, and Intel macOS, with source materials and exact installer digests. No ads, donations, subscriptions, paid promotion, included commercial game media or BIOS files. No claim of a broad commercial license for the bundled emulators.  
**Maintainer authorization:** The owner has explicitly requested the public stable 3.1.0 release repeatedly. This is an informed release decision; it does not transform automated tests into legal advice or physical-device testing.

## Why the earlier licenses did not suddenly change

Anything Plays' original app is MIT. The 11 original-source Libretro core families, including noncommercial Snes9x, were already in stable [3.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0) and their source materials and notices remain publicly accessible in [v3.0.0-sources](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources). All four frozen 3.1 core sets were revalidated in [13/13 native final QA](https://github.com/MasynNay/anything-plays/actions/runs/43140637755). The [3.0 requirements](https://github.com/MasynNay/anything-plays/blob/v3.0.0/requirements.txt) did not include pygame-ce; [3.1 requirements](../requirements.txt) add it for optional controllers. This is the substantive new license family. The tested 3.1 OpenCV rebuilds also remove bundled FFmpeg from this candidate. [Version-to-version detail](V3_1_DISTRIBUTION_DELTA.md).

## Review of the new bundled runtime

| Covered component | Copyright/license condition | Actual frozen evidence and delivered materials |
| --- | --- | --- |
| pygame-ce 2.5.8 | LGPL 2.1 or later, proper notice/source access and ability to use a modified compatible library as applicable | Original immutable upstream 2.5.8 tagged source, pygame license, exact original wheel identity, four native modified C-extension replacement tests; source in new eight-asset companion |
| SDL2, SDL2_image, SDL2_mixer, SDL2_ttf | Individual upstream zlib-style license texts; must retain actual copyright notices | Exact original SDL 2.32.8/2.32.10 and image 2.8.12, mixer 2.8.2 and ttf 2.24.0 source archives, original license texts, and byte-inventoried native filenames; source companion retains license texts |
| mpg123 1.33.7 on Linux and both Macs | LGPL 2.1, separate notices and relevant corresponding source/replacement access | Original 1.33.7 source `mpg123-1.33.7.tar.bz2` SHA-256 `31d0e35a4ca567ec9b5ebda6c3062bb4435d6d3eacd6ef0d95cadd7854dc03ee`, official `COPYING` and C sources, and the [verbatim upstream pygame mpg123 LGPL text](../licenses/mpg123-LGPL-2.1-ORIGINAL.txt) |
| Other pygame native audio/font/image libraries | Component-specific permissive/attribution/license terms, not automatically LGPL merely because pygame distributes them | The complete original upstream pygame source archive contains its `docs/licenses/` attribution texts; the exact installed packages preserve third-party notices and a Python distribution inventory. This review makes no blanket assertion about every transitive library's copyright |
| Original Libretro cores | Existing MPL, permissive, and noncommercial third-party terms | No ROMs/BIOS. The previously released original native-core source archives and notices remain publicly accessible and runtime hashes matched the unchanged source families |
| OpenCV 4.14.0.94 | Apache-2.0/OpenCV; original opencv-python packaging MIT and applicable component terms | Four original-source compiled FFmpeg-disabled camera-only wheels with native capture backends; [source archive, Windows patch and original compile flags](V3_1_CLEAN_OPENCV_SOURCE_REPRODUCTION.md) recorded |

Independent four-platform native files and notice inspection: [43147036559](https://github.com/MasynNay/anything-plays/actions/runs/43147036559).

**Source companion:** [43152661067](https://github.com/MasynNay/anything-plays/actions/runs/43152661067) and independent [eight-asset preflight 43153670927](https://github.com/MasynNay/anything-plays/actions/runs/43153670927). The original pygame, five original SDL archives and original mpg123 source are SHA-pinned, checked and packaged into `AnythingPlays-3.1.0-PYGAME-SDL-MPG123-ORIGINAL-SOURCE.zip`. The exact app source is available at `104b96621ec4cb8dc39fde8c3fe96fc854c406ed`. The source package also includes end-user source-access and replacement-test pointers. The [separate 3.0 original core source release](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources) remains available.

**Replaced genuinely modified code:** [Linux](https://github.com/MasynNay/anything-plays/actions/runs/43148388829), [Windows](https://github.com/MasynNay/anything-plays/actions/runs/43149732092), [Apple Silicon and Intel macOS](https://github.com/MasynNay/anything-plays/actions/runs/43149191077) each compiled source-modified `pygame.base`, executed the changed C function within a **copy of the actual final frozen 3.1 app**, and booted its real Tk desktop. Mac copies were ad-hoc re-signed. This establishes a concrete shared/dynamic native replacement path but is not a test of every native library in the bundle. Other LGPL-compatible libraries and dynamic file paths should remain user-modifiable subject to operating-system signing procedures.

## Distribution determination, scope and limitations

The maintained product is offered as a free, noncommercial source-accompanied portfolio release under the above limited scope. The new LGPL 2.1 source and notice candidates, original versions and a demonstrated native replacement method have been assembled and verified as engineering evidence. Because the software is distributed as frozen native installers, recipients should have access to the license text, corresponding library sources and compatible-library replacement instructions. Do not impose an EULA preventing reverse engineering for debugging modifications of LGPL-covered libraries.

**This is a documented maintainer release review, not independent legal counsel or a claim of bit-for-bit reproducible builds.** Matching a version/tag and replacing one C extension does not prove every native object was independently rebuilt from its upstream source or that no third-party obligation could exist. If a rights holder identifies missing source, license notices or a non-replaceable covered native module, promptly supply the requested corresponding materials, correct the installer or withdraw and reissue the affected asset. Maintain the frozen release manifests and SHA-256 correspondence for support.

The owner also knowingly chooses release with **disclosed, unverified physical controller/webcam/gameplay/audio/save/endurance QA** for the exact four installers. It is expressly **not** a physical hardware pass. See [hardware QA disclosure](V3_1_HARDWARE_QA_SCOPE.md).

## Artifact rollout acceptance

- [x] All four clean original 3.1.0 installers built from the same fixed app source; authentic 18 console profiles, 11 cores, native installed Tk/Stream Mode QA and source wheel identity [PASS](https://github.com/MasynNay/anything-plays/actions/runs/43140637755).
- [x] Existing old stock-OpenCV private draft identified and preserved without false promotion; source-clean seven-file stage [PASS](https://github.com/MasynNay/anything-plays/actions/runs/43142249044).
- [x] Original LGPL controller source companion staged and hash verified [PASS](https://github.com/MasynNay/anything-plays/actions/runs/43152661067).
- [x] Original eight release assets (four binaries, three verification files, one source archive) verified without publication [PASS](https://github.com/MasynNay/anything-plays/actions/runs/43153670927).
- [x] A write-scoped, same-repository GitHub Actions token can read the immutable private draft [PASS](https://github.com/MasynNay/anything-plays/actions/runs/43154143521), and the tag does not yet exist while the release remains a draft.
- [x] Final release notes explain free/noncommercial terms, rights/source, no included game media, hardware limitations, ad-hoc macOS signing and report-an-issue support.
- [ ] After final gated GitHub workflow publication, independently verify public `v3.1.0` tag points to source `104b96621ec4cb8dc39fde8c3fe96fc854c406ed`, all eight attached assets match their expected SHA256 digests, and releases remain downloadable anonymously.
- [ ] After publication, update live portfolio and README links to the newly verified public `v3.1.0` release; retain public v3.0 and RC2 as rollback.

**Approval boundary:** This review accepts the scoped free/noncommercial release and source companion for the known pygame/SDL/mpg123 licensing changes. It does **not** claim certification of every third-party object or passing unperformed real hardware tests. The exact final release workflow must fail if checksum, source identity, draft/private state, asset count or any documented release decision diverges.
