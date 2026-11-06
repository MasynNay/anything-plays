# Contributing to Anything Plays

Thank you for helping make camera-powered play accessible and reliable.

## Before writing code

Open an issue describing the bug or feature, the affected console and
operating system, and what you expect to happen. For camera or emulator bugs,
include relevant logs and steps to reproduce, but **never upload commercial
ROMs, BIOS images, personal camera footage, or private settings files**.

## Development setup

Use Python 3.12 with Tkinter, install `requirements.txt`, and run the program
from source. `README.md` contains platform-specific instructions. Use a
virtual environment; do not commit `.venv`, `cores/`, `dist/`, or `release/`.

## Code expectations

- Keep responsibilities in the modules listed in `ARCHITECTURE.md`.
- Write straightforward functions with descriptive names and comments that
  explain constraints or unusual decisions, not every line of syntax.
- Do not perform Tk widget operations in background threads.
- Keep libretro callback objects and borrowed native memory alive for their
  required lifetime. Avoid changing C structure layouts without a focused test.
- Never add global keyboard injection or silently download native code at app
  runtime.
- Preserve the legacy settings location and per-console profile migration.
- Keep all four consoles and all 16 themes working. Changes to button IDs,
  cartridge art, grid geometry, and saved layouts require regression tests.
- Preserve bundled core checks in all three platform packaging scripts.

## Test before opening a pull request

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```

On Linux with a virtual display:

```bash
PYTHONPATH=. xvfb-run -a python tests/smoke_gui.py
```

If you touched camera capture, core startup, audio, or packaging, use the
`QA_CHECKLIST.md` to verify the affected platforms with a real device and a
homebrew or otherwise legally obtained ROM. Automated tests do not prove the
installer is correct.

## Pull requests

Keep each change focused, describe why it is needed, and include the test
results and affected OS/console combinations. Do not include unrelated
formatting, generated native cores, builds, ROMs, or secrets. Contributors
retain responsibility for confirming rights to any new assets they provide.
