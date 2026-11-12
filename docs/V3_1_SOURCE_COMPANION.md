# Anything Plays 3.1 — Source companion QA

**Technical source candidates, not complete corresponding-source or redistribution approval.**

[Successful new source-companion run](https://github.com/MasynNay/anything-plays/actions/runs/42909893531) packages the
original upstream Git-tag candidate archives for pygame-ce 2.5.8, SDL2
2.32.8 and 2.32.10, SDL2_image 2.8.12, SDL2_mixer 2.8.2, and SDL2_ttf
2.24.0. All six original-source archives, source metadata, the five verbatim tagged SDL top-level LICENSE.txt notices,
an original pygame LGPL 2.1 notice, SHA-256 digests and frozen SDL runtime evidence
are retained in one time-limited GitHub Actions artifact.

### Provenance

- Exact installed full 18-console RC1 QA: [42905694504](https://github.com/MasynNay/anything-plays/actions/runs/42905694504).
- Pinned official pygame-ce tag and current wheel comparisons: [42906334464](https://github.com/MasynNay/anything-plays/actions/runs/42906334464).
- Pinned five official SDL upstream tags: [42879614179](https://github.com/MasynNay/anything-plays/actions/runs/42879614179).
- New combined six-source companion and independent hash check: [42909893531](https://github.com/MasynNay/anything-plays/actions/runs/42909893531).
- Public source built emulator-core origins remain in the separate
  [Anything Plays 3.0.0 original sources release](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources).

### Not yet proven

The candidate versions were selected from observed native version strings;
the precise source trees, native build flags, wheel-to-signed-macOS binary
transforms, LGPL replacement/relinking process, required transitive sources
and notices have not all been independently verified. The technical
companion is insufficient to certify legal compliance or a stable 3.1
release. Physical gamepads, camera, retail games, saves, audio, long sessions
and final 3.1.0 stable identities are separate, open release requirements.

Do not label these files approved source correspondence, rename RC1
installers as stable, or modify the existing public 3.0.0 release.

## Exact clean-final 3.1.0 native source replacement evidence (all four OSes)

The following source-modification tests target the **new, original, immutable, complete 18-console/11-core 3.1.0 installers** from the single source revision `104b96621ec4cb8dc39fde8c3fe96fc854c406ed` in [final original build 43140637755](https://github.com/MasynNay/anything-plays/actions/runs/43140637755). They are more recent and more relevant than the older RC1 replacement evidence below.

| Final native OS | Exact technical result |
| --- | --- |
| Linux x64 | [Passed actual final Linux modified C method and frozen Tk](https://github.com/MasynNay/anything-plays/actions/runs/43148388829) |
| Windows x64 | [Passed actual final Windows modified MSVC C method and frozen Tk](https://github.com/MasynNay/anything-plays/actions/runs/43149732092) |
| macOS Apple Silicon | [Passed actual final signed Mac modified C method and frozen Tk](https://github.com/MasynNay/anything-plays/actions/runs/43149191077) |
| macOS Intel | [Passed separate actual final signed Intel Mac modified C method and frozen Tk](https://github.com/MasynNay/anything-plays/actions/runs/43149191077) |

The independently compiled modified native `pygame.base` library was installed **only into a disposable copied original app**. The source was the exact tagged pygame-ce 2.5.8 original, with observable C changes. The copied native function executed and the real frozen 18-console Tk desktop opened successfully. Original installers remained unchanged. Mac app copies were re-signed after native modification. The corrected [exact four-platform final native library and notice inventory](https://github.com/MasynNay/anything-plays/actions/runs/43147036559) passed separately.

**This is one covered C extension per platform, not independent proof of all pygame/SDL/transitive binary-to-source correspondence, build options, modified-library replacement for every relevant object, complete user-supplied build/relink materials, notice duties or redistribution permission.** pygame-ce 2.5.8 is LGPL; bundled SDL 2.x is zlib-licensed, but every transitive dependency must be reviewed according to its own license. Source archives and CI evidence can expire, so a public binary release needs durable source and notice access satisfying actual applicable terms. None of the physical gamepad, camera, game save, audio, sustained gameplay and independent legal/rollout checks is silently approved by the native code tests.

See [the native distribution review](V3_1_NATIVE_DISTRIBUTION_REVIEW.md), [exact final release acceptance record](V3_1_RELEASE_ACCEPTANCE.md) and [publication runbook](V3_1_PUBLICATION_RUNBOOK.md). The owner has requested public 3.1.0, but the exact distribution rights/source/relinking and hardware release gates are still explicitly false.

## Subsequent verified native-replacement evidence

The technical source-companion candidate archives above have since been
supplemented by **actual modified-source `pygame.base` compilation, native
method invocation from disposable original RC1 installations, and frozen
Tk startup** on all four shipping targets:

| Target | Verified CI |
| --- | --- |
| Linux x64 | [Source-modified Linux RC1 QA](https://github.com/MasynNay/anything-plays/actions/runs/42949949019) |
| macOS Apple Silicon | [Source-modified dual-Mac RC1 QA](https://github.com/MasynNay/anything-plays/actions/runs/42951159759) |
| macOS Intel | [Source-modified dual-Mac RC1 QA](https://github.com/MasynNay/anything-plays/actions/runs/42951159759) |
| Windows x64 | [Source-modified Windows RC1 QA](https://github.com/MasynNay/anything-plays/actions/runs/42953456034) |

This establishes a practical replacement path for **one** pygame native
extension only. It is not a demonstration of end-user replacement for
all LGPL-covered components, source-to-binary correspondence for every
SDL dependency, or complete Section 6 compliance. The source companion
must still gain exact build options, linked-library dependency inventory,
reproducible user rebuild/replacement steps for the complete covered
runtime, required notices and source availability review. Physical
controller, camera, gameplay, save and stable installer acceptance are
independent open gates.

See [Windows and four-platform modified-source evidence](V3_1_LGPL_ACTUAL_MODIFIED_PYGAME_WINDOWS_SOURCE_QA.md),
[release acceptance](V3_1_RELEASE_ACCEPTANCE.md) and the machine-readable
`config/v3.1-release-readiness.json`. **Do not set the six stable release
gates true on the basis of these limited technical proofs.**
