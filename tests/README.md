# Test organization

The project's test suite is intentionally in one directory for standard Python unittest discovery. Tests with the **test_v21_** prefix remain because they preserve compatibility behavior carried forward into 3.0; renaming them adds churn without new coverage.

| Area | Files |
| --- | --- |
| Shared emulator, camera, settings, storage | tests beginning with **test_** |
| New 3.0 console and installer contracts | tests beginning with **test_v30_** |
| UI startup and longer running sessions | **smoke_gui.py**, **soak_gui.py** |
| Native console audio, video, save and input evidence | Matching GitHub Actions workflows and tools in **tools/** |

Commands from the repository root:

- **python -m unittest discover -s tests -v**
- **python tools/check_repository_hygiene.py**
- **PYTHONPATH=. xvfb-run -a python tests/smoke_gui.py** (Linux)

Never suppress or weaken a failing native compatibility assertion solely to make CI green. Avoid committing commercial ROMs, BIOS, emulator binaries or installer outputs.
