# Anything Plays — What changed in 3.1 distribution and why it matters

**Exact comparison of published 3.0 and source-verified 3.1.0, November 11/12, 2026.** This is a component-specific technical release review, not a blanket assertion of legal permission.

## Change table

| Component | Stable 3.0 | Clean 3.1.0 | Distribution effect |
| --- | --- | --- | --- |
| Original app source | MIT | MIT | No change to Anything Plays' own source license |
| Eleven Libretro core families, 18 console profiles | Original-source archives/notices in [v3.0.0-sources](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources) | Original core families and source provenance revalidated in [full clean final QA](https://github.com/MasynNay/anything-plays/actions/runs/43140637755) | Existing core-specific obligations continue; Snes9x must remain noncommercial and the required notices/source available |
| OpenCV camera backend | Published stock headless wheel still included FFmpeg and some platform codec libraries | Recompiled OpenCV 4.14.0.94 on all four hosts with FFmpeg OFF; [actual final source record](V3_1_CLEAN_OPENCV_SOURCE_REPRODUCTION.md) | **Reduces** packaged codec obligations; exact pristine source and Windows packager patch are recorded |
| SDL controller stack | No pygame-ce requirement in [v3.0.0 requirements.txt](https://github.com/MasynNay/anything-plays/blob/v3.0.0/requirements.txt) | Adds `pygame-ce>=2.5.8,<3` for optional gamepads | **New LGPL-2.1-or-later pygame-ce distribution and replacement obligations** |
| SDL 2.x | Other packaged components could use SDL, but pygame-ce was not installed | pygame-ce 2.5.8 wheel includes SDL2, SDL2_image, SDL2_mixer, SDL2_ttf | SDL2 itself uses the zlib license; preserve each component's actual notices, without incorrectly claiming SDL2 is LGPL |
| Bundled mpg123 | Not introduced through pygame-ce in 3.0 | The exact new 3.1 Linux/Mac native package audits show `libmpg123` in pygame's native dependency directory | **Additional LGPL 2.1 notice/source/replacement review**, not covered by SDL2's zlib notice. The original [pygame-ce mpg123 license text](../licenses/mpg123-LGPL-2.1-ORIGINAL.txt) is retained verbatim |
| Other bundled audio/font/image libraries | Some families pre-existed through Pillow and audio runtimes | pygame-ce brings further native audio/font libraries, including FreeType, FLAC, Ogg/Vorbis, Opus, HarfBuzz and Brotli on some platforms | Preserve proper per-library license notices and accurately identify conditions. FreeType can be used under its FreeType License with the applicable acknowledgement; it is not automatically GPL-only |

## Verifiable evidence already complete

- Four original, same-source clean 3.1.0 full native installers passed [13/13 native jobs](https://github.com/MasynNay/anything-plays/actions/runs/43140637755), including real frozen Tk/Stream Mode startup and checksum-proven wheel identity.
- The [four exact-native dependency and notice inventories](https://github.com/MasynNay/anything-plays/actions/runs/43147036559) passed and enumerate byte hashes, actual library paths and available license files.
- A **genuinely modified** pygame-ce C extension compiled, loaded and executed in a separate frozen final 3.1.0 installation on [Linux](https://github.com/MasynNay/anything-plays/actions/runs/43148388829), [Windows](https://github.com/MasynNay/anything-plays/actions/runs/43149732092), [Apple Silicon and Intel Macs](https://github.com/MasynNay/anything-plays/actions/runs/43149191077). The original installers were preserved. This proves a practical path for one component, not every covered library.
- Six original pygame/SDL tagged source candidates and their licensing texts are preserved with SHA256 in the [upstream source QA artifact](https://github.com/MasynNay/anything-plays/actions/runs/42909893531); the exact final app, SDL/pygame source manifests, notices and replacement tests are linked from [the source companion](V3_1_SOURCE_COMPANION.md).

## Distribution scope and remaining source requirements

As with [published v2.0](RELEASE_DISTRIBUTION_REVIEW.md), limit the complete emulator-bundling download to **free, noncommercial, nonpromotional distribution**. Do not place ads, subscriptions, sponsorship, paid promotion or donations around the binary download, because Snes9x grants only noncommercial use. The original MIT app source has broader rights than some complete installer components. Do not imply ROMs or BIOS files are provided. Maintain verified source and notices for all eleven cores.

For the new pygame-ce/SDL native runtime, ensure recipient-accessible pygame-ce source and applicable library dependencies, actual license/credit text, appropriate source/build inputs and a workable way to install compatible modified LGPL native libraries. Do not assume a successful test of one `pygame.base` extension establishes full source correspondence for `libmpg123` or every third-party native object. In particular, the new 3.1 package currently has `libmpg123` on Linux and both Macs, while the older six-archive pygame/SDL source bundle did not separately include pinned mpg123 source. The exact compiled mpg123 source/build identity and corresponding-source access need completion, or a tested clean rebuild without that dependency.

Physical controller/camera/retail-game/endurance coverage is separately documented in [the disclosed QA scope](V3_1_HARDWARE_QA_SCOPE.md). A known untested hardware condition may be disclosed; it is not a distinct license prohibition and must never be marked physically passed.

**Decision at this checkpoint:** Technical binary QA is ready. The public GitHub release remains gated on rights/source/notice and final artifact review, **not** on a newly invented requirement that every user own an Intel Mac or controller. This is a narrower remediation path than restarting all of 3.1.
