# Anything Plays 3.1 — Exact clean-source frozen native and notice inventory

**Technical evidence, November 11/12, 2026. Not legal or physical-hardware approval.**

The four native jobs in [Actions run 43147036559](https://github.com/MasynNay/anything-plays/actions/runs/43147036559) independently audited the actual `v3.1.0` complete installers from [the 13/13 passing unified clean build 43140637755](https://github.com/MasynNay/anything-plays/actions/runs/43140637755), **not** the outdated stock OpenCV draft. All four jobs completed successfully.

The exact immutable application source is `104b96621ec4cb8dc39fde8c3fe96fc854c406ed`. Each job rechecked the original GitHub run identity, installed package SHA and original 11-core/18-console receipt, then inspected a freshly extracted DEB, Windows Inno EXE, or signed mounted DMG. The evidence reports include SHA256 for each frozen native object and observed license/notice candidate, alongside duplicate-native-basenames with different hashes. No game ROMs or cameras were uploaded.

| Target | Audited native files | Audited license/notice candidates | Named codec candidates | Evidence artifact |
| --- | ---: | ---: | ---: | --- |
| Linux x64 | 216 | 164 | 0 | [Native inventory artifact](https://github.com/MasynNay/anything-plays/actions/runs/43147036559/artifacts/13911503107) |
| Windows x64 | 198 | 166 | 0 | [Native inventory artifact](https://github.com/MasynNay/anything-plays/actions/runs/43147036559/artifacts/13912845513) |
| macOS Apple Silicon | 204 | 167 | 0 | [Native inventory artifact](https://github.com/MasynNay/anything-plays/actions/runs/43147036559/artifacts/13912086959) |
| macOS Intel | 203 | 167 | 0 | [Native inventory artifact](https://github.com/MasynNay/anything-plays/actions/runs/43147036559/artifacts/13912506591) |

The scanner was also corrected to reject `.so.yml` notice metadata previously counted as compiled macOS modules. The revised audit passed all four platforms and reduced Apple Silicon native counts from 206 to 204 and Intel Mac counts from 205 to 203; notice counts were unchanged. A regression test now preserves versioned Linux ELF sonames while excluding misleading metadata extensions.

These are the actual counts printed by the native jobs, **not** estimates or claims that all those files are subject to the same license. `named codec candidates = 0` means the inventory's filename classifier did not find one of its configured codec name patterns among inventoried native objects. It is **not** a comprehensive transitive-codec/legal analysis.

## What this newly resolves

- Actual installed native and notice inventory coverage for the **new clean-source candidate on all four platforms**.
- Original binary SHA and exact source revision provenance for each inspected full installer.
- A reproducible private per-platform evidence report for native dependency, duplicate-library and notice review.

## Still required for redistribution and public stable approval

- Trace each relevant LGPL-covered pygame-ce native object (and applicable transitive dependencies) to the **actual corresponding source, local modifications, compilation options, build tools and linker arrangement**. The upstream [pygame-ce license identifies LGPL-2.1-or-later](https://github.com/pygame-community/pygame-ce/blob/main/README.rst). The existing genuine source-modified `pygame.base` test covered an *older RC1* artifact and **one** extension, not the entire exact clean 3.1 installation.
- Independently verify the actual license of **each** native dependency and retain the required notice texts. SDL 2.x itself uses the [zlib license](https://www.libsdl.org/license.php); do not incorrectly treat every SDL2 library as LGPL or assume all SDL-related transitive components have the same terms.
- Establish recipient-usable library modification/rebuild/replacement materials when required by the [actual LGPL-2.1 linking/distribution terms](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html) on all four targets.
- Preserve durable source availability and notices alongside any final public release; the CI artifacts are temporary.
- Obtain physical controller/camera/gameplay/save/audio acceptance for the **exact** clean final installer where possible, clearly identifying untested hardware rather than converting synthetic CI into a physical pass.
- Review final release notes and post-upload seven-asset SHA-256 correspondence before publication.

**These audit jobs passing do not automatically flip `pygame_sdl_redistribution_review`, `corresponding_source_material`, `real_controller_hardware_acceptance` or `public_release_approved`.** They reduce the missing technical evidence while the release stays safely private.
