# Anything Plays 2.1 — Maintainer guide

This guide describes the **test branch**, not the verified v2.0 release.
Never merge it into `main` or publish it as v2.1 until the release checklist
and real-hardware criteria below pass.

## Repository map

| Path | Responsibility |
| --- | --- |
| `app.py` | The Tk root, shared state, and mixin composition |
| `anything_plays/ui_layout.py` | Game area, ROM controls and scrolling |
| `anything_plays/ui_panels.py` | Camera, tracking, and safety panels |
| `anything_plays/ui_library.py` | ROM library scan, cancel and thumbnail shelf |
| `anything_plays/ui_gameplay.py` | Manual keys, camera arming and frame display |
| `anything_plays/ui_profiles.py` | Per-console profiles and preferences |
| `anything_plays/ui_external.py` | External fallback process and input bridge |
| `anything_plays/ui_view.py` | Windowed, fullscreen, borderless and game-only view |
| `anything_plays/ui_updates.py` | Background update check scheduling and UI feedback |
| `anything_plays/emulator_updates.py` | Read-only upstream checks and core hashes |
| `anything_plays/gba_emulator.py` | Libretro lifecycle on the emulator thread |
| `anything_plays/libretro_*.py` | Isolated audio, video, input and save adapters |
| `anything_plays/n64_software.py` | Experimental ParaLLEl-N64 Angrylion options |
| `anything_plays/remote_retropad.py` | N64 controller fallback via loopback UDP |
| `anything_plays/dolphin_pipe.py` | Dolphin controller fallback (POSIX) |
| `tools/` | Dependency auditing, staged file checks and native build tools |
| `tests/` | Unit, contract and synthetic graphics/input tests |
| `docs/` | Architecture, licensing, provenance, QA and decisions |
| `.github/workflows/v21-test-build.yml` | **Alpha-only** test builds, separate from 2.0 |

Root-level build scripts, `requirements*.txt`, `installer.iss`,
`AnythingPlays.spec`, `verify_bundle.py` and `fetch_mgba_core.py`
remain as supported entry points. Moving them merely to reduce GitHub's
visible file count breaks packaging callers and reproducibility.

## Run development tests

```bash
python -m pip install -r requirements.txt
python -m compileall -q app.py anything_plays tests fetch_mgba_core.py verify_bundle.py
python -m unittest discover -s tests -v
# Linux CI runs the GUI smoke test with:
xvfb-run -a python tests/smoke_gui.py
```

Tests use fake ROM bytes and synthetic camera/controller inputs. A passing
test suite does **not** validate gameplay on real console titles, physical
webcams, GPU drivers, audio devices, or macOS Gatekeeper.

## Console readiness

| Console | Built-in video | Installer bundles core | Camera control | Readiness |
| --- | --- | --- | --- | --- |
| GB / GBC / GBA | Yes | mGBA | Yes | Supported |
| SNES | Yes | Snes9x | Yes | Supported |
| NES | Yes | FCEUmm in alpha | Yes | Needs expanded real-game QA |
| Genesis | Yes | Genesis Plus GX in alpha | Yes | Needs expanded real-game QA |
| N64 | **Experimental** Angrylion software video | ParaLLEl-N64 in alpha | Analog/digital in app | Physical-hardware validation outstanding |
| GameCube | **Experimental** Dolphin CPU renderer in app | Dolphin core and Sys staged in alpha | In-app RetroPad mapping | **Native gameplay/performance unverified; release blocked** |

### Native embedded N64

The test app defaults to the software-rendered ParaLLEl-N64 core. It requests
Angrylion, rejects hardware render requests, and passes returned CPU pixel
frames through the Libretro video adapter to the built-in canvas. If that
path is too slow or incompatible, switch off **Play N64 in the app** to select
the external RetroArch fallback. This fallback is not the intended final UX.

Do not claim native N64 parity until a real-ROM compatibility matrix confirms
camera buttons, analog range, audio, SRAM persistence, resizing, game-only
mode, stop/restart and expected performance on Apple Silicon, Intel,
Windows and Linux.

### GameCube native renderer and GPU-host blocker

The alpha now stages Dolphin Libretro and its Sys assets, and attempts an
in-panel CPU renderer. The pinned native patch removes a software-renderer
dependency on a separate OpenGL window. It still must compile successfully
and demonstrate nonblank homebrew frames at minimally usable speed.
The native CI job retains build logs on compilation failure and records
separate frame-validity and frame-rate evidence. No success is assumed
from the presence of a binary alone.

Dolphin's accelerated renderer requires an owned OpenGL/Vulkan/Metal graphics
context and video presentation into the app. A Libretro core that requests a
hardware framebuffer cannot be driven by the current Tk/PIL software-frame
decoder. The existing separate-window Dolphin bridge and binary are **not**
a one-installer/no-dependency solution.

GameCube readiness requires a supported and licensed embeddable graphics
backend, platform-specific GPU lifecycle, controller+analog mapping, sound,
saves, native packaging, and actual cross-platform gameplay validation.
Do not hide missing prerequisites behind an installer or claim it is complete
based on launch tests.

## Emulator update policy

The startup job checks upstream source repositories no more than once every
24 hours. It checks bundled core digests against `CORE_PROVENANCE.json`.
A different upstream source revision is a **review signal**, not proof that a
compatible binary update exists. Never hot-swap a running or signed native
library, or install unreviewed nightlies automatically.

For release updates, maintainers validate source/license changes, build a
complete package, re-run native library checks, sign the bundle, and issue a
new app release with rollback instructions. ROMs and BIOS files are never
included.

## Release checklist — all required

- [ ] No regressions in GB/GBC/GBA, SNES, NES and Genesis
- [ ] Real N64 title compatibility and latency recorded on all target platforms
- [ ] N64 in-app graphics/audio/input/save/suspend confirmed
- [ ] **GameCube game video rendered within Anything Plays**
- [ ] **No external RetroArch/Dolphin installation required for any advertised system**
- [ ] User-friendly ROM library scanning and clear/reset actions validated
- [ ] 2.1 app icon approved and included consistently across every installer
- [ ] Full 2.1 core license/source review with deterministic hashes
- [ ] Safe signed application update and recovery/rollback process validated
- [ ] Windows, macOS Intel, macOS Apple Silicon and Linux physical-install QA
- [ ] Main branch, stable installer and existing 2.0 settings preserved

The requirement is **select ROM → enable camera → play**, not a collection of
manual emulator configuration dialogs. If a checkbox remains unchecked, keep
this branch as a test build and retain the known-good 2.0 release.
