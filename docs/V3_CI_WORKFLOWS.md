# Anything Plays 3.0 — CI workflow map

The Actions page has three purposeful workflows instead of an 800-line
mixed build-and-experiment workflow.

* **Application builds** (`v30-app.yml`) runs source/GUI tests and builds
  Windows, macOS Intel, macOS Apple Silicon and Linux starter installers.
* **Emulator verification** (`v30-cores.yml`) runs managed-core install,
  playback and rollback tests, NES/Atari native audio/video, N64 homebrew
  and platform-matched optional core candidate packaging.
* **Experimental emulator lab** (`v30-lab.yml`) runs only when selected
  native/diagnostic code changes or when manually dispatched. It records
  GameCube renderer crashes and the Genesis 68000 experiment without
  turning a successful mGBA-only application build into an overall failure.

A green application build is **not** a public 3.0 release and cannot override
`tools/check_v30_release.py`. GameCube and Genesis still require real
continuous video, sound, input, saves and platform-specific runtime QA.
All core-pack candidates remain unpublished until license/runtime approval.

The published 2.0 release and its legacy history are preserved.
