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
